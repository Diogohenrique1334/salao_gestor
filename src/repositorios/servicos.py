# ---------------------------------------------------------------------------
# repositorios/servicos.py — acesso a dados de Servico e do vinculo
# CabeleireiroServico (que carrega o desconto especifico por cabeleireiro).
# ---------------------------------------------------------------------------
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import CabeleireiroServico, Servico


# ----- Servico -------------------------------------------------------------
def listar(db: Session, incluir_inativos: bool = False) -> List[Servico]:
    stmt = select(Servico).order_by(Servico.nome)
    if not incluir_inativos:
        stmt = stmt.where(Servico.ativo.is_(True))
    return list(db.execute(stmt).scalars().all())


def buscar_por_id(db: Session, servico_id: int) -> Optional[Servico]:
    return db.get(Servico, servico_id)


def criar(db: Session, *, nome: str, duracao_min: int, preco_base: Decimal) -> Servico:
    s = Servico(nome=nome.strip(), duracao_min=int(duracao_min), preco_base=preco_base, ativo=True)
    db.add(s)
    db.flush()
    return s


def atualizar(
    db: Session,
    servico_id: int,
    *,
    nome: Optional[str] = None,
    duracao_min: Optional[int] = None,
    preco_base: Optional[Decimal] = None,
    ativo: Optional[bool] = None,
) -> Optional[Servico]:
    s = db.get(Servico, servico_id)
    if not s:
        return None
    if nome is not None:
        s.nome = nome.strip()
    if duracao_min is not None:
        s.duracao_min = int(duracao_min)
    if preco_base is not None:
        s.preco_base = preco_base
    if ativo is not None:
        s.ativo = ativo
    db.flush()
    return s


def remover(db: Session, servico_id: int) -> None:
    """Soft-delete do servico (preserva historico)."""
    s = db.get(Servico, servico_id)
    if s:
        s.ativo = False
        db.flush()


# ----- Vinculo cabeleireiro<->servico (DESCONTO) ---------------------------
def buscar_vinculo(db: Session, cabeleireiro_id: int, servico_id: int) -> Optional[CabeleireiroServico]:
    return db.execute(
        select(CabeleireiroServico).where(
            CabeleireiroServico.cabeleireiro_id == cabeleireiro_id,
            CabeleireiroServico.servico_id == servico_id,
        )
    ).scalar_one_or_none()


def listar_vinculos_do_cabeleireiro(
    db: Session, cabeleireiro_id: int, apenas_ativos: bool = True
) -> List[CabeleireiroServico]:
    stmt = select(CabeleireiroServico).where(
        CabeleireiroServico.cabeleireiro_id == cabeleireiro_id
    )
    if apenas_ativos:
        stmt = stmt.where(CabeleireiroServico.ativo.is_(True))
    return list(db.execute(stmt).scalars().all())


def definir_vinculo(
    db: Session,
    *,
    cabeleireiro_id: int,
    servico_id: int,
    desconto_tipo: Optional[str],
    desconto_valor: Decimal,
    ativo: bool = True,
) -> CabeleireiroServico:
    """Cria ou atualiza (upsert) o vinculo cabeleireiro<->servico com desconto."""
    vinc = buscar_vinculo(db, cabeleireiro_id, servico_id)
    if vinc is None:
        vinc = CabeleireiroServico(cabeleireiro_id=cabeleireiro_id, servico_id=servico_id)
        db.add(vinc)
    vinc.desconto_tipo = desconto_tipo
    vinc.desconto_valor = desconto_valor
    vinc.ativo = ativo
    db.flush()
    return vinc


def remover_vinculo(db: Session, cabeleireiro_id: int, servico_id: int) -> None:
    vinc = buscar_vinculo(db, cabeleireiro_id, servico_id)
    if vinc:
        db.delete(vinc)
        db.flush()
