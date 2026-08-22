"""data de nascimento do cliente

Revision ID: 0004_data_nascimento
Revises: 0003_login_cabeleireiro
Create Date: 2026-06-22

Adiciona cliente.data_nascimento (nullable) — base para acao de aniversario.
Nullable: contas antigas, walk-in e seed seguem sem o dado.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_data_nascimento"
down_revision = "0003_login_cabeleireiro"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cliente", sa.Column("data_nascimento", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("cliente", "data_nascimento")
