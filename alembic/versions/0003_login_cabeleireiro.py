"""login do cabeleireiro (conta ligada ao perfil)

Revision ID: 0003_login_cabeleireiro
Revises: 0002_walkin_e_reset
Create Date: 2026-06-21

Adiciona cliente.cabeleireiro_id (FK -> cabeleireiro.id) para que uma conta
com papel='cabeleireiro' aponte para o seu perfil profissional.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_login_cabeleireiro"
down_revision = "0002_walkin_e_reset"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cliente", sa.Column("cabeleireiro_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_cliente_cabeleireiro", "cliente", "cabeleireiro",
        ["cabeleireiro_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_cliente_cabeleireiro", "cliente", type_="foreignkey")
    op.drop_column("cliente", "cabeleireiro_id")
