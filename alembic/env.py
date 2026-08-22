# ---------------------------------------------------------------------------
# alembic/env.py — bootstrap das migrations.
#
# Conecta o Alembic ao metadata dos modelos (src.db) e pega a URL do banco da
# camada de configuracao (env var DATABASE_URL ou .streamlit/secrets.toml),
# sem hardcode de credencial no repositorio.
# ---------------------------------------------------------------------------
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from src.config.settings import get_settings
from src.db import models  # noqa: F401 (registra os modelos no metadata)
from src.db.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    url = get_settings().database_url
    if not url:
        raise RuntimeError(
            "DATABASE_URL nao configurada. Defina a env var DATABASE_URL ou "
            "preencha database_url em .streamlit/secrets.toml antes de migrar."
        )
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_url(), poolclass=pool.NullPool, future=True)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
