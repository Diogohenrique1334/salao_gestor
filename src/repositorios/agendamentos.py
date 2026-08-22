# ---------------------------------------------------------------------------
# repositorios/agendamentos.py — acesso a dados de Agendamento.
#
# Inclui as consultas que sustentam regras de negocio:
#   - existe_conflito: ha agendamento ATIVO sobrepondo o intervalo do mesmo
#     cabeleireiro? (trava double-booking)
#   - pendentes_de_lembrete: agendamentos ativos que comecam num intervalo e
#     ainda nao tiveram lembrete enviado (idempotencia do job).
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from src.constantes import STATUS_ATIVOS, STATUS_CONFIRMADO
from src.db.models import Agendamento


def buscar_por_id(db: Session, agendamento_id: int) -> Optional[Agendamento]:
    return db.get(Agendamento, agendamento_id)


def listar_por_cliente(
    db: Session, cliente_id: int, apenas_futuros: bool = False
) -> List[Agendamento]:
    stmt = select(Agendamento).where(Agendamento.cliente_id == cliente_id)
    if apenas_futuros:
        stmt = stmt.where(Agendamento.inicio >= datetime.now())
    return list(db.execute(stmt.order_by(Agendamento.inicio.desc())).scalars().all())


def listar_por_cabeleireiro_no_dia(
    db: Session,
    cabeleireiro_id: int,
    dia_inicio: datetime,
    dia_fim: datetime,
    apenas_ativos: bool = True,
) -> List[Agendamento]:
    """Agendamentos de um cabeleireiro num intervalo (ex.: um dia).

    Por padrao so os ATIVOS (ocupam slot — usado pelo calculo de agenda). Com
    `apenas_ativos=False` traz tambem os finalizados (concluido/no_show/cancelado),
    para exibicao da agenda do dia com as baixas ja registradas.
    """
    stmt = select(Agendamento).where(
        Agendamento.cabeleireiro_id == cabeleireiro_id,
        Agendamento.inicio >= dia_inicio,
        Agendamento.inicio < dia_fim,
    )
    if apenas_ativos:
        stmt = stmt.where(Agendamento.status.in_(STATUS_ATIVOS))
    return list(db.execute(stmt.order_by(Agendamento.inicio)).scalars().all())


def existe_conflito(
    db: Session,
    *,
    cabeleireiro_id: int,
    inicio: datetime,
    fim: datetime,
    ignorar_id: Optional[int] = None,
) -> bool:
    """True se ja houver agendamento ativo do cabeleireiro sobrepondo [inicio, fim)."""
    # Sobreposicao: existente.inicio < novo.fim  E  existente.fim > novo.inicio
    stmt = select(Agendamento.id).where(
        Agendamento.cabeleireiro_id == cabeleireiro_id,
        Agendamento.status.in_(STATUS_ATIVOS),
        and_(Agendamento.inicio < fim, Agendamento.fim > inicio),
    )
    if ignorar_id is not None:
        stmt = stmt.where(Agendamento.id != ignorar_id)
    return db.execute(stmt.limit(1)).first() is not None


def criar(
    db: Session,
    *,
    cabeleireiro_id: int,
    servico_id: int,
    inicio: datetime,
    fim: datetime,
    preco_aplicado: Decimal,
    desconto_aplicado: Decimal,
    cliente_id: Optional[int] = None,
    nome_avulso: Optional[str] = None,
    telefone_avulso: Optional[str] = None,
    status: str = STATUS_CONFIRMADO,
) -> Agendamento:
    ag = Agendamento(
        cliente_id=cliente_id,
        nome_avulso=(nome_avulso or None),
        telefone_avulso=(telefone_avulso or None),
        cabeleireiro_id=cabeleireiro_id,
        servico_id=servico_id,
        inicio=inicio,
        fim=fim,
        preco_aplicado=preco_aplicado,
        desconto_aplicado=desconto_aplicado,
        status=status,
    )
    db.add(ag)
    db.flush()
    return ag


def atualizar_status(db: Session, agendamento_id: int, status: str) -> Optional[Agendamento]:
    ag = db.get(Agendamento, agendamento_id)
    if ag:
        ag.status = status
        db.flush()
    return ag


def reagendar(
    db: Session, agendamento_id: int, *, inicio: datetime, fim: datetime
) -> Optional[Agendamento]:
    ag = db.get(Agendamento, agendamento_id)
    if ag:
        ag.inicio = inicio
        ag.fim = fim
        ag.lembrete_enviado_em = None  # novo horario => novo lembrete
        db.flush()
    return ag


def marcar_canal_confirmacao(db: Session, agendamento_id: int, canais: str) -> None:
    ag = db.get(Agendamento, agendamento_id)
    if ag:
        ag.canal_confirmacao = canais
        db.flush()


# ----- Suporte ao job de lembretes ----------------------------------------
def pendentes_de_lembrete(
    db: Session, intervalo_inicio: datetime, intervalo_fim: datetime
) -> List[Agendamento]:
    """Agendamentos ativos que comecam no intervalo e ainda sem lembrete."""
    return list(
        db.execute(
            select(Agendamento)
            .where(
                Agendamento.status.in_(STATUS_ATIVOS),
                Agendamento.inicio >= intervalo_inicio,
                Agendamento.inicio < intervalo_fim,
                Agendamento.lembrete_enviado_em.is_(None),
            )
            .order_by(Agendamento.inicio)
        ).scalars().all()
    )


def marcar_lembrete_enviado(db: Session, agendamento_id: int, quando: Optional[datetime] = None) -> None:
    ag = db.get(Agendamento, agendamento_id)
    if ag:
        ag.lembrete_enviado_em = quando or datetime.utcnow()
        db.flush()
