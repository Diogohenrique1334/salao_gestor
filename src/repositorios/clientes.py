# ---------------------------------------------------------------------------
# repositorios/clientes.py — acesso a dados da entidade Cliente.
#
# So fala com o banco (CRUD). Regras (hash de senha, validacao) ficam na
# camada de negocio (servicos/auth.py). Todas as funcoes recebem a Session.
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constantes import PAPEL_CLIENTE
from src.db.models import Cliente


def buscar_por_email(db: Session, email: str) -> Optional[Cliente]:
    return db.execute(
        select(Cliente).where(Cliente.email == email.strip().lower())
    ).scalar_one_or_none()


def listar(db: Session, papel: str = PAPEL_CLIENTE) -> List[Cliente]:
    return list(
        db.execute(
            select(Cliente).where(Cliente.papel == papel).order_by(Cliente.nome)
        ).scalars().all()
    )


def buscar_por_id(db: Session, cliente_id: int) -> Optional[Cliente]:
    return db.get(Cliente, cliente_id)


def buscar_por_cabeleireiro(db: Session, cabeleireiro_id: int) -> Optional[Cliente]:
    """Conta de login (papel=cabeleireiro) vinculada a um perfil profissional."""
    return db.execute(
        select(Cliente).where(Cliente.cabeleireiro_id == cabeleireiro_id)
    ).scalar_one_or_none()


def criar(
    db: Session,
    *,
    nome: str,
    email: str,
    senha_hash: str,
    telefone: Optional[str] = None,
    data_nascimento: Optional[date] = None,
    papel: str = PAPEL_CLIENTE,
    cabeleireiro_id: Optional[int] = None,
) -> Cliente:
    cliente = Cliente(
        nome=nome.strip(),
        email=email.strip().lower(),
        senha_hash=senha_hash,
        telefone=(telefone or None),
        data_nascimento=data_nascimento,
        papel=papel,
        cabeleireiro_id=cabeleireiro_id,
    )
    db.add(cliente)
    db.flush()  # garante id sem fechar a transacao
    return cliente


def atualizar_telefone(db: Session, cliente_id: int, telefone: str) -> None:
    cliente = db.get(Cliente, cliente_id)
    if cliente:
        cliente.telefone = telefone.strip() or None
        db.flush()


def definir_senha(db: Session, cliente_id: int, senha_hash: str) -> None:
    """Troca a senha e limpa qualquer codigo de reset pendente."""
    cliente = db.get(Cliente, cliente_id)
    if cliente:
        cliente.senha_hash = senha_hash
        cliente.reset_codigo_hash = None
        cliente.reset_expira_em = None
        db.flush()


def set_reset(db: Session, cliente_id: int, codigo_hash: str, expira_em: datetime) -> None:
    cliente = db.get(Cliente, cliente_id)
    if cliente:
        cliente.reset_codigo_hash = codigo_hash
        cliente.reset_expira_em = expira_em
        db.flush()


def limpar_reset(db: Session, cliente_id: int) -> None:
    cliente = db.get(Cliente, cliente_id)
    if cliente:
        cliente.reset_codigo_hash = None
        cliente.reset_expira_em = None
        db.flush()
