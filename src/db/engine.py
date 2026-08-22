# ---------------------------------------------------------------------------
# engine.py — conexao com o Neon (Postgres).
#
# Responsabilidade: criar o Engine SQLAlchemy (com pool resiliente p/ banco
# serverless do Neon, que hiberna) e a fabrica de Session. Usado por
# repositorios e jobs.
#
# Saidas principais:
#   - get_engine()        -> Engine (cacheado)
#   - SessionLocal        -> sessionmaker
#   - sessao()            -> context manager (commit/rollback automatico)
#   - testar_conexao()    -> (ok: bool, detalhe: str)
# ---------------------------------------------------------------------------
from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Cria (uma vez) o Engine apontando para o Neon."""
    settings = get_settings()
    if not settings.db_configurado:
        raise RuntimeError(
            "DATABASE_URL nao configurada. Preencha .streamlit/secrets.toml "
            "(database_url) ou a env var DATABASE_URL."
        )
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,    # reconecta apos hibernacao do Neon
        pool_recycle=300,
        future=True,
    )


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


def nova_sessao() -> Session:
    """Retorna uma Session crua (chamador controla commit/close)."""
    return _session_factory()()


@contextmanager
def sessao() -> Iterator[Session]:
    """Context manager: commit no sucesso, rollback no erro, close sempre."""
    db = nova_sessao()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def testar_conexao() -> tuple[bool, str]:
    """Valida a conexao com o Neon. Retorna (ok, detalhe)."""
    try:
        with get_engine().connect() as conn:
            versao = conn.execute(text("SELECT version()")).scalar_one()
        return True, str(versao)
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"
