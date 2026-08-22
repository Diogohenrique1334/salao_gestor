# ---------------------------------------------------------------------------
# repositorios/cabeleireiros.py — acesso a dados de Cabeleireiro e HorarioTrabalho.
#
# CRUD do profissional + suas janelas de trabalho. "Remover" e' soft-delete
# (ativo=False) para preservar o historico de agendamentos. Tambem expoe
# remover_definitivo para casos sem historico.
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import time
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Cabeleireiro, HorarioTrabalho


# ----- Cabeleireiro --------------------------------------------------------
def listar(db: Session, incluir_inativos: bool = False) -> List[Cabeleireiro]:
    stmt = select(Cabeleireiro).order_by(Cabeleireiro.nome)
    if not incluir_inativos:
        stmt = stmt.where(Cabeleireiro.ativo.is_(True))
    return list(db.execute(stmt).scalars().all())


def buscar_por_id(db: Session, cabeleireiro_id: int) -> Optional[Cabeleireiro]:
    return db.get(Cabeleireiro, cabeleireiro_id)


def criar(db: Session, *, nome: str, telefone: Optional[str] = None, bio: Optional[str] = None) -> Cabeleireiro:
    prof = Cabeleireiro(nome=nome.strip(), telefone=(telefone or None), bio=(bio or None), ativo=True)
    db.add(prof)
    db.flush()
    return prof


def atualizar(
    db: Session,
    cabeleireiro_id: int,
    *,
    nome: Optional[str] = None,
    telefone: Optional[str] = None,
    bio: Optional[str] = None,
    ativo: Optional[bool] = None,
) -> Optional[Cabeleireiro]:
    prof = db.get(Cabeleireiro, cabeleireiro_id)
    if not prof:
        return None
    if nome is not None:
        prof.nome = nome.strip()
    if telefone is not None:
        prof.telefone = telefone.strip() or None
    if bio is not None:
        prof.bio = bio.strip() or None
    if ativo is not None:
        prof.ativo = ativo
    db.flush()
    return prof


def remover(db: Session, cabeleireiro_id: int) -> None:
    """Soft-delete: desativa o cabeleireiro (preserva agendamentos antigos)."""
    prof = db.get(Cabeleireiro, cabeleireiro_id)
    if prof:
        prof.ativo = False
        db.flush()


def remover_definitivo(db: Session, cabeleireiro_id: int) -> None:
    """Apaga de vez (cascata em vinculos/horarios). Use so sem agendamentos."""
    prof = db.get(Cabeleireiro, cabeleireiro_id)
    if prof:
        db.delete(prof)
        db.flush()


# ----- HorarioTrabalho -----------------------------------------------------
def listar_horarios(db: Session, cabeleireiro_id: int) -> List[HorarioTrabalho]:
    return list(
        db.execute(
            select(HorarioTrabalho)
            .where(HorarioTrabalho.cabeleireiro_id == cabeleireiro_id)
            .order_by(HorarioTrabalho.dia_semana, HorarioTrabalho.hora_inicio)
        ).scalars().all()
    )


def adicionar_horario(
    db: Session, cabeleireiro_id: int, *, dia_semana: int, hora_inicio: time, hora_fim: time
) -> HorarioTrabalho:
    h = HorarioTrabalho(
        cabeleireiro_id=cabeleireiro_id,
        dia_semana=dia_semana,
        hora_inicio=hora_inicio,
        hora_fim=hora_fim,
    )
    db.add(h)
    db.flush()
    return h


def remover_horario(db: Session, horario_id: int) -> None:
    h = db.get(HorarioTrabalho, horario_id)
    if h:
        db.delete(h)
        db.flush()
