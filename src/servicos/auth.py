# ---------------------------------------------------------------------------
# servicos/auth.py — CAMADA DE NEGOCIO: autenticacao.
#
# Responsabilidade: hash/verificacao de senha (bcrypt) e autenticacao de
# usuario contra o banco. A gestao de sessao/cookie na UI fica em
# ui/componentes/guards.py (Etapa 2) — aqui mora apenas a regra pura + acesso
# via repositorio de clientes.
# ---------------------------------------------------------------------------
from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta
from typing import Optional, Tuple

import bcrypt
from sqlalchemy.orm import Session

from src.constantes import PAPEL_CABELEIREIRO, PAPEL_CLIENTE
from src.db.models import Cliente
from src.repositorios import clientes as repo_clientes

_BCRYPT_MAX_BYTES = 72  # limite do algoritmo bcrypt
_RESET_VALIDADE_MIN = 30


def hash_senha(senha: str) -> str:
    """Gera o hash bcrypt da senha (string pronta p/ persistir)."""
    senha_bytes = senha.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(senha_bytes, bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Confere a senha em texto contra o hash armazenado."""
    try:
        senha_bytes = senha.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(senha_bytes, senha_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


class EmailJaCadastrado(Exception):
    """Erro de negocio: e-mail ja existe no cadastro."""


def registrar_cliente(
    db: Session,
    *,
    nome: str,
    email: str,
    senha: str,
    telefone: Optional[str] = None,
    data_nascimento: Optional[date] = None,
    papel: str = PAPEL_CLIENTE,
) -> Cliente:
    """Cadastra um novo usuario com senha hasheada. Levanta se e-mail existir."""
    if repo_clientes.buscar_por_email(db, email):
        raise EmailJaCadastrado(email)
    return repo_clientes.criar(
        db,
        nome=nome,
        email=email,
        senha_hash=hash_senha(senha),
        telefone=telefone,
        data_nascimento=data_nascimento,
        papel=papel,
    )


def autenticar(db: Session, email: str, senha: str) -> Optional[Cliente]:
    """Retorna o Cliente se e-mail+senha conferem; senao None."""
    cliente = repo_clientes.buscar_por_email(db, email)
    if cliente and verificar_senha(senha, cliente.senha_hash):
        return cliente
    return None


# ----- reset de senha ------------------------------------------------------
def redefinir_senha(db: Session, cliente_id: int, nova_senha: str) -> None:
    """Define uma nova senha (uso direto: gestor ou etapa final do self-service)."""
    repo_clientes.definir_senha(db, cliente_id, hash_senha(nova_senha))


def gerar_codigo_reset(db: Session, email: str) -> Optional[Tuple[Cliente, str]]:
    """Gera e armazena (hasheado) um codigo de 6 digitos com validade.

    Retorna (cliente, codigo_em_texto) p/ envio; None se o e-mail nao existir.
    O codigo em texto so existe aqui (no banco fica apenas o hash).
    """
    cliente = repo_clientes.buscar_por_email(db, email)
    if cliente is None:
        return None
    codigo = f"{secrets.randbelow(10**6):06d}"
    expira = datetime.utcnow() + timedelta(minutes=_RESET_VALIDADE_MIN)
    repo_clientes.set_reset(db, cliente.id, hash_senha(codigo), expira)
    return cliente, codigo


def definir_login_cabeleireiro(
    db: Session, *, cabeleireiro_id: int, nome: str, email: str, senha: Optional[str] = None
) -> Cliente:
    """Cria ou atualiza a conta de login (papel=cabeleireiro) de um perfil.

    - Se ja existe conta para o cabeleireiro: atualiza nome/e-mail e, se `senha`
      vier preenchida, troca a senha.
    - Senao: cria a conta (senha obrigatoria). O e-mail nao pode pertencer a
      outra conta.
    """
    email = email.strip().lower()
    existente = repo_clientes.buscar_por_cabeleireiro(db, cabeleireiro_id)

    # e-mail nao pode colidir com outra conta
    por_email = repo_clientes.buscar_por_email(db, email)
    if por_email is not None and (existente is None or por_email.id != existente.id):
        raise EmailJaCadastrado(email)

    if existente is not None:
        existente.nome = nome.strip()
        existente.email = email
        if senha:
            existente.senha_hash = hash_senha(senha)
        db.flush()
        return existente

    if not senha:
        raise ValueError("Senha obrigatoria ao criar o login do cabeleireiro.")
    return repo_clientes.criar(
        db, nome=nome, email=email, senha_hash=hash_senha(senha),
        papel=PAPEL_CABELEIREIRO, cabeleireiro_id=cabeleireiro_id,
    )


def redefinir_com_codigo(db: Session, email: str, codigo: str, nova_senha: str) -> bool:
    """Valida o codigo (correto e nao expirado) e troca a senha. True em sucesso."""
    cliente = repo_clientes.buscar_por_email(db, email)
    if cliente is None or not cliente.reset_codigo_hash or not cliente.reset_expira_em:
        return False
    if datetime.utcnow() > cliente.reset_expira_em:
        repo_clientes.limpar_reset(db, cliente.id)
        return False
    if not verificar_senha(codigo.strip(), cliente.reset_codigo_hash):
        return False
    repo_clientes.definir_senha(db, cliente.id, hash_senha(nova_senha))  # tambem limpa o reset
    return True
