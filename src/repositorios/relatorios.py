# ---------------------------------------------------------------------------
# repositorios/relatorios.py — CONSULTAS ANALITICAS p/ o dashboard do gestor.
#
# Separado do CRUD por entidade: aqui ficam agregacoes (contagens, receita,
# distribuicoes). Retorna estruturas simples (dicts/listas de tuplas) que a UI
# transforma em DataFrame p/ os graficos do dashboard.
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.constantes import (
    STATUS_CANCELADO,
    STATUS_CONCLUIDO,
    STATUS_CONFIRMADO,
    STATUS_NO_SHOW,
    STATUS_REAGENDADO,
)
from src.db.models import Agendamento, Cabeleireiro

_STATUS_RECEITA = (STATUS_CONFIRMADO, STATUS_REAGENDADO, STATUS_CONCLUIDO)


def _filtro_cab(stmt, cabeleireiro_id: Optional[int]):
    """Aplica filtro opcional por cabeleireiro a um SELECT de agendamentos."""
    if cabeleireiro_id is not None:
        stmt = stmt.where(Agendamento.cabeleireiro_id == cabeleireiro_id)
    return stmt


def resumo(db: Session, desde: datetime, cabeleireiro_id: Optional[int] = None) -> Dict[str, object]:
    """KPIs no periodo: total, cancelados, receita e ticket medio.

    Se `cabeleireiro_id` vier, restringe ao profissional (painel do cabeleireiro).
    """
    total = db.execute(
        _filtro_cab(select(func.count(Agendamento.id)).where(Agendamento.criado_em >= desde), cabeleireiro_id)
    ).scalar_one()

    cancelados = db.execute(
        _filtro_cab(select(func.count(Agendamento.id)).where(
            Agendamento.criado_em >= desde, Agendamento.status == STATUS_CANCELADO
        ), cabeleireiro_id)
    ).scalar_one()

    concluidos = db.execute(
        _filtro_cab(select(func.count(Agendamento.id)).where(
            Agendamento.criado_em >= desde, Agendamento.status == STATUS_CONCLUIDO
        ), cabeleireiro_id)
    ).scalar_one()

    no_shows = db.execute(
        _filtro_cab(select(func.count(Agendamento.id)).where(
            Agendamento.criado_em >= desde, Agendamento.status == STATUS_NO_SHOW
        ), cabeleireiro_id)
    ).scalar_one()

    receita = db.execute(
        _filtro_cab(select(func.coalesce(func.sum(Agendamento.preco_aplicado), 0)).where(
            Agendamento.criado_em >= desde, Agendamento.status.in_(_STATUS_RECEITA)
        ), cabeleireiro_id)
    ).scalar_one()

    # DENOMINADOR do ticket medio: so atendimentos PAGOS (preco > 0).
    # Planos/cortesias lancados a R$ 0 (ex.: servico "Mensal") sao atendimentos
    # reais e contam em `total`, mas incluí-los aqui derrubaria a media.
    pagos = db.execute(
        _filtro_cab(select(func.count(Agendamento.id)).where(
            Agendamento.criado_em >= desde,
            Agendamento.status.in_(_STATUS_RECEITA),
            Agendamento.preco_aplicado > 0,
        ), cabeleireiro_id)
    ).scalar_one()

    gratuitos = db.execute(
        _filtro_cab(select(func.count(Agendamento.id)).where(
            Agendamento.criado_em >= desde,
            Agendamento.status.in_(_STATUS_RECEITA),
            Agendamento.preco_aplicado <= 0,
        ), cabeleireiro_id)
    ).scalar_one()

    receita = Decimal(receita or 0)
    ticket = (receita / pagos) if pagos else Decimal(0)
    taxa_cancel = (cancelados / total * 100) if total else 0.0
    # no-show entre os ja resolvidos (compareceu vs faltou); ignora os ainda em aberto
    resolvidos = concluidos + no_shows
    taxa_no_show = (no_shows / resolvidos * 100) if resolvidos else 0.0
    return {
        "total": int(total),
        "cancelados": int(cancelados),
        "concluidos": int(concluidos),
        "no_shows": int(no_shows),
        "receita": receita,
        "ticket_medio": ticket,
        "pagos": int(pagos),
        "gratuitos": int(gratuitos),
        "taxa_cancelamento": taxa_cancel,
        "taxa_no_show": taxa_no_show,
    }


def por_cabeleireiro(db: Session, desde: datetime) -> List[Tuple[str, int]]:
    rows = db.execute(
        select(Cabeleireiro.nome, func.count(Agendamento.id))
        .join(Agendamento, Agendamento.cabeleireiro_id == Cabeleireiro.id)
        .where(Agendamento.criado_em >= desde)
        .group_by(Cabeleireiro.nome)
        .order_by(func.count(Agendamento.id).desc())
    ).all()
    return [(nome, int(qtd)) for nome, qtd in rows]


def por_status(db: Session, desde: datetime, cabeleireiro_id: Optional[int] = None) -> List[Tuple[str, int]]:
    stmt = _filtro_cab(
        select(Agendamento.status, func.count(Agendamento.id)).where(Agendamento.criado_em >= desde),
        cabeleireiro_id,
    ).group_by(Agendamento.status)
    rows = db.execute(stmt).all()
    return [(status, int(qtd)) for status, qtd in rows]


def por_dia(db: Session, desde: datetime, cabeleireiro_id: Optional[int] = None) -> List[Tuple[str, int]]:
    dia = func.date(Agendamento.inicio)
    stmt = _filtro_cab(
        select(dia, func.count(Agendamento.id)).where(Agendamento.inicio >= desde),
        cabeleireiro_id,
    ).group_by(dia).order_by(dia)
    rows = db.execute(stmt).all()
    return [(str(d), int(qtd)) for d, qtd in rows]
