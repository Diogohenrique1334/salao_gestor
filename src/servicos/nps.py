# ---------------------------------------------------------------------------
# servicos/nps.py — CAMADA DE NEGOCIO: NPS (pesquisa de satisfacao).
#
# Duas partes:
#   1) calcular_nps(notas) / classificar(nota) -> PURAS (sem banco): aplicam a
#      convencao NPS (promotor 9-10, neutro 7-8, detrator 0-6) e devolvem o score.
#   2) registrar(db, ...) -> grava a nota de um atendimento concluido, com regras
#      (nota valida, agendamento concluido e do cliente, sem resposta previa).
# ---------------------------------------------------------------------------
from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.constantes import NPS_DETRATOR_MAX, NPS_PROMOTOR_MIN, STATUS_CONCLUIDO
from src.db.models import NpsResposta
from src.repositorios import agendamentos as repo_ag
from src.repositorios import nps as repo_nps

NOTA_MIN = 0
NOTA_MAX = 10


# ----- erros de negocio ----------------------------------------------------
class ErroNps(Exception):
    """Base p/ erros de NPS."""


class NpsInvalido(ErroNps):
    """Nota fora de 0-10 ou agendamento em estado invalido."""


class NpsDuplicado(ErroNps):
    """Ja existe resposta NPS para este agendamento."""


# ----- calculo PURO --------------------------------------------------------
def classificar(nota: int) -> str:
    """'promotor' (>=9), 'detrator' (<=6) ou 'neutro' (7-8)."""
    if nota >= NPS_PROMOTOR_MIN:
        return "promotor"
    if nota <= NPS_DETRATOR_MAX:
        return "detrator"
    return "neutro"


def calcular_nps(notas: List[int]) -> Dict[str, object]:
    """Score NPS (= round(%promotores - %detratores), -100 a +100) e auxiliares."""
    total = len(notas)
    if total == 0:
        return {"total": 0, "promotores": 0, "detratores": 0, "neutros": 0,
                "pct_promotores": 0.0, "pct_detratores": 0.0, "media": 0.0, "score": 0}
    promotores = sum(1 for n in notas if n >= NPS_PROMOTOR_MIN)
    detratores = sum(1 for n in notas if n <= NPS_DETRATOR_MAX)
    neutros = total - promotores - detratores
    pct_prom = promotores / total * 100
    pct_detr = detratores / total * 100
    return {
        "total": total,
        "promotores": promotores,
        "detratores": detratores,
        "neutros": neutros,
        "pct_promotores": pct_prom,
        "pct_detratores": pct_detr,
        "media": sum(notas) / total,
        "score": round(pct_prom - pct_detr),
    }


# ----- registro ------------------------------------------------------------
def registrar(
    db: Session, *, agendamento_id: int, cliente_id: int, nota: int, comentario: Optional[str] = None
) -> NpsResposta:
    """Grava a avaliacao NPS de um atendimento concluido do proprio cliente."""
    if not (NOTA_MIN <= nota <= NOTA_MAX):
        raise NpsInvalido(nota)
    ag = repo_ag.buscar_por_id(db, agendamento_id)
    if ag is None or ag.cliente_id != cliente_id or ag.status != STATUS_CONCLUIDO:
        raise NpsInvalido(agendamento_id)
    if repo_nps.buscar_por_agendamento(db, agendamento_id) is not None:
        raise NpsDuplicado(agendamento_id)
    return repo_nps.criar(
        db, agendamento_id=agendamento_id, cliente_id=cliente_id, nota=nota, comentario=comentario
    )
