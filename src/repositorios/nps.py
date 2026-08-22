# ---------------------------------------------------------------------------
# repositorios/nps.py — acesso a dados das respostas de NPS.
#
# So fala com o banco. A regra (validar nota/estado, calcular score) fica em
# servicos/nps.py. Consultas de apoio:
#   - agendamentos_pendentes: concluidos do cliente ainda SEM nota (coleta).
#   - notas_no_periodo: notas de um intervalo (opcional por cabeleireiro) -> score.
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constantes import STATUS_CONCLUIDO
from src.db.models import Agendamento, NpsResposta


def criar(
    db: Session, *, agendamento_id: int, cliente_id: int, nota: int, comentario: Optional[str] = None
) -> NpsResposta:
    resposta = NpsResposta(
        agendamento_id=agendamento_id,
        cliente_id=cliente_id,
        nota=nota,
        comentario=(comentario or None),
    )
    db.add(resposta)
    db.flush()
    return resposta


def buscar_por_agendamento(db: Session, agendamento_id: int) -> Optional[NpsResposta]:
    return db.execute(
        select(NpsResposta).where(NpsResposta.agendamento_id == agendamento_id)
    ).scalar_one_or_none()


def agendamentos_pendentes(db: Session, cliente_id: int) -> List[Agendamento]:
    """Agendamentos concluidos do cliente que ainda nao tem resposta NPS."""
    return list(
        db.execute(
            select(Agendamento)
            .outerjoin(NpsResposta, NpsResposta.agendamento_id == Agendamento.id)
            .where(
                Agendamento.cliente_id == cliente_id,
                Agendamento.status == STATUS_CONCLUIDO,
                NpsResposta.id.is_(None),
            )
            .order_by(Agendamento.inicio.desc())
        ).scalars().all()
    )


def listar_por_cliente(db: Session, cliente_id: int) -> List[NpsResposta]:
    """Todas as respostas NPS do cliente (p/ a UI saber quais ja foram avaliados)."""
    return list(
        db.execute(
            select(NpsResposta).where(NpsResposta.cliente_id == cliente_id)
        ).scalars().all()
    )


def notas_no_periodo(
    db: Session, desde: datetime, cabeleireiro_id: Optional[int] = None
) -> List[int]:
    """Notas (0-10) respondidas desde `desde`. Filtra por cabeleireiro se informado."""
    stmt = select(NpsResposta.nota).where(NpsResposta.criado_em >= desde)
    if cabeleireiro_id is not None:
        stmt = stmt.join(Agendamento, Agendamento.id == NpsResposta.agendamento_id).where(
            Agendamento.cabeleireiro_id == cabeleireiro_id
        )
    return [int(n) for n in db.execute(stmt).scalars().all()]
