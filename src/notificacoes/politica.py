# ---------------------------------------------------------------------------
# notificacoes/politica.py — QUAL canal atende QUAL evento.
#
# Antes, o dispatcher enviava por todo canal configurado. Isso funciona
# enquanto todos os canais sao gratuitos, mas quebra no momento em que entra um
# canal PAGO (SMS ~R$0,10/msg): cada evento novo viraria custo automatico.
#
# Aqui a decisao fica declarativa e num lugar so. Regra de bolso adotada:
#   - CONFIRMACAO: o cliente acabou de agendar na tela, ja sabe -> e-mail (registro).
#   - LEMBRETE   : e' o evento que reduz no-show -> unico candidato natural a SMS.
#   - PROFISSIONAL: sempre e-mail (volume baixo, custo zero).
#
# Para ligar o SMS no futuro: implementar SmsNotificador, registra-lo no
# dispatcher e acrescentar CANAL_SMS na linha do EVENTO_LEMBRETE. Nada mais.
# ---------------------------------------------------------------------------
from __future__ import annotations

from typing import Dict, Tuple

from src.constantes import (
    CANAL_EMAIL,
    CANAL_WHATSAPP,
    EVENTO_CANCELAMENTO,
    EVENTO_CONFIRMACAO,
    EVENTO_LEMBRETE,
    EVENTO_PROF_AGENDA_DIA,
    EVENTO_PROF_CANCELAMENTO,
    EVENTO_PROF_NOVO_AGENDAMENTO,
    EVENTO_PROF_REAGENDAMENTO,
    EVENTO_REAGENDAMENTO,
    EVENTO_RESET_SENHA,
)

# Ordem importa apenas para leitura; o dispatcher tenta todos os listados.
CANAIS_POR_EVENTO: Dict[str, Tuple[str, ...]] = {
    # ----- cliente -----
    EVENTO_CONFIRMACAO: (CANAL_EMAIL, CANAL_WHATSAPP),
    EVENTO_LEMBRETE: (CANAL_EMAIL, CANAL_WHATSAPP),   # <- acrescentar CANAL_SMS aqui
    EVENTO_REAGENDAMENTO: (CANAL_EMAIL, CANAL_WHATSAPP),
    EVENTO_CANCELAMENTO: (CANAL_EMAIL,),
    EVENTO_RESET_SENHA: (CANAL_EMAIL,),
    # ----- profissional (cabeleireiro) -----
    EVENTO_PROF_NOVO_AGENDAMENTO: (CANAL_EMAIL,),
    EVENTO_PROF_REAGENDAMENTO: (CANAL_EMAIL,),
    EVENTO_PROF_CANCELAMENTO: (CANAL_EMAIL,),
    EVENTO_PROF_AGENDA_DIA: (CANAL_EMAIL,),
}

# Evento desconhecido cai aqui (conservador: nunca um canal pago por engano).
CANAIS_PADRAO: Tuple[str, ...] = (CANAL_EMAIL,)


def canais_de(evento: str) -> Tuple[str, ...]:
    """Canais habilitados para um evento (ver CANAIS_POR_EVENTO)."""
    return CANAIS_POR_EVENTO.get(evento, CANAIS_PADRAO)
