# ---------------------------------------------------------------------------
# servicos/precificacao.py — MOTOR DE PRECO (regra de negocio pura)
#
# Calcula o preco final de um servico para um cabeleireiro, aplicando o
# desconto especifico do vinculo (percentual ou valor absoluto), amarrado ao
# preco_base do servico. Funcao pura (sem banco) => facil de testar.
#
# Saida: PrecoCalculado(preco_base, desconto, preco_final).
# ---------------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from src.constantes import DESCONTO_PERCENTUAL, DESCONTO_VALOR

_CENTAVOS = Decimal("0.01")


def _q(valor: Decimal) -> Decimal:
    """Arredonda para 2 casas (centavos)."""
    return valor.quantize(_CENTAVOS, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PrecoCalculado:
    preco_base: Decimal
    desconto: Decimal
    preco_final: Decimal


def calcular_preco(
    preco_base: Decimal,
    desconto_tipo: Optional[str],
    desconto_valor: Optional[Decimal],
) -> PrecoCalculado:
    """Aplica o desconto do cabeleireiro sobre o preco-base do servico.

    - desconto_tipo == 'percentual': desconta `desconto_valor`% (limitado a 0-100)
    - desconto_tipo == 'valor':      desconta `desconto_valor` reais
    - None/0:                        sem desconto
    O preco final nunca fica negativo.
    """
    base = Decimal(preco_base or 0)
    valor = Decimal(desconto_valor or 0)

    if desconto_tipo == DESCONTO_PERCENTUAL and valor > 0:
        pct = min(max(valor, Decimal(0)), Decimal(100))
        desconto = _q(base * pct / Decimal(100))
    elif desconto_tipo == DESCONTO_VALOR and valor > 0:
        desconto = _q(min(valor, base))
    else:
        desconto = Decimal("0.00")

    final = _q(base - desconto)
    if final < 0:
        final = Decimal("0.00")
    return PrecoCalculado(preco_base=_q(base), desconto=desconto, preco_final=final)
