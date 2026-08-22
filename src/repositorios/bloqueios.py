# ---------------------------------------------------------------------------
# repositorios/bloqueios.py — acesso a dados de BloqueioAgenda (ferias/folga).
#
# So fala com o banco (CRUD + consultas de apoio). As regras (converter datas em
# intervalo de dia cheio, validar periodo) ficam em servicos/bloqueios.py.
#
# Consultas que sustentam a disponibilidade:
#   - intervalos_no_dia: bloqueios que tocam um dia, clipados a [00:00, 24:00) ->
#     entram como "ocupado" no calculo de slots (servicos/agenda.py).
#   - existe_no_intervalo: ha bloqueio sobrepondo [inicio, fim)? -> barra reserva.
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from src.db.models import BloqueioAgenda


def criar(
    db: Session, *, cabeleireiro_id: int, inicio: datetime, fim: datetime, motivo: Optional[str] = None
) -> BloqueioAgenda:
    bloqueio = BloqueioAgenda(
        cabeleireiro_id=cabeleireiro_id,
        inicio=inicio,
        fim=fim,
        motivo=(motivo or None),
    )
    db.add(bloqueio)
    db.flush()
    return bloqueio


def buscar_por_id(db: Session, bloqueio_id: int) -> Optional[BloqueioAgenda]:
    return db.get(BloqueioAgenda, bloqueio_id)


def listar_por_cabeleireiro(
    db: Session, cabeleireiro_id: int, apenas_futuros: bool = True
) -> List[BloqueioAgenda]:
    """Bloqueios do cabeleireiro, ordenados por inicio.

    `apenas_futuros` mantem so os que ainda nao terminaram (fim >= agora).
    """
    stmt = select(BloqueioAgenda).where(BloqueioAgenda.cabeleireiro_id == cabeleireiro_id)
    if apenas_futuros:
        stmt = stmt.where(BloqueioAgenda.fim >= datetime.now())
    return list(db.execute(stmt.order_by(BloqueioAgenda.inicio)).scalars().all())


def remover(db: Session, bloqueio_id: int) -> None:
    bloqueio = db.get(BloqueioAgenda, bloqueio_id)
    if bloqueio:
        db.delete(bloqueio)
        db.flush()


def listar_no_intervalo(
    db: Session, cabeleireiro_id: int, inicio: datetime, fim: datetime
) -> List[BloqueioAgenda]:
    """Bloqueios do cabeleireiro que sobrepoem [inicio, fim). Ordenados por inicio.

    Usado para pre-carregar TODOS os bloqueios de um horizonte numa unica query
    (calculo batcheado de disponibilidade em servicos/agenda.py).
    """
    return list(
        db.execute(
            select(BloqueioAgenda)
            .where(
                BloqueioAgenda.cabeleireiro_id == cabeleireiro_id,
                and_(BloqueioAgenda.inicio < fim, BloqueioAgenda.fim > inicio),
            )
            .order_by(BloqueioAgenda.inicio)
        ).scalars().all()
    )


def intervalos_no_dia(
    db: Session, cabeleireiro_id: int, dia: date
) -> List[Tuple[datetime, datetime]]:
    """Bloqueios que tocam o dia, clipados a [00:00, 24:00) do dia.

    Formato (inicio, fim) pronto para entrar como intervalo "ocupado".
    """
    dia_ini = datetime.combine(dia, time.min)
    dia_fim = dia_ini + timedelta(days=1)
    bloqueios = listar_no_intervalo(db, cabeleireiro_id, dia_ini, dia_fim)
    return [(max(b.inicio, dia_ini), min(b.fim, dia_fim)) for b in bloqueios]


def existe_no_intervalo(
    db: Session, *, cabeleireiro_id: int, inicio: datetime, fim: datetime
) -> bool:
    """True se ha bloqueio do cabeleireiro sobrepondo [inicio, fim)."""
    stmt = select(BloqueioAgenda.id).where(
        BloqueioAgenda.cabeleireiro_id == cabeleireiro_id,
        and_(BloqueioAgenda.inicio < fim, BloqueioAgenda.fim > inicio),
    )
    return db.execute(stmt.limit(1)).first() is not None
