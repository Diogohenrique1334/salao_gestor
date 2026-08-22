"""walk-in (agendamento avulso) e reset de senha

Revision ID: 0002_walkin_e_reset
Revises: 0001_inicial
Create Date: 2026-06-21

- agendamento.cliente_id passa a aceitar NULL (atendimento avulso)
- agendamento ganha nome_avulso / telefone_avulso
- cliente ganha reset_codigo_hash / reset_expira_em (reset self-service)
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_walkin_e_reset"
down_revision = "0001_inicial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agendamento", sa.Column("nome_avulso", sa.String(length=120), nullable=True))
    op.add_column("agendamento", sa.Column("telefone_avulso", sa.String(length=20), nullable=True))
    op.alter_column("agendamento", "cliente_id", existing_type=sa.Integer(), nullable=True)

    op.add_column("cliente", sa.Column("reset_codigo_hash", sa.String(length=200), nullable=True))
    op.add_column("cliente", sa.Column("reset_expira_em", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("cliente", "reset_expira_em")
    op.drop_column("cliente", "reset_codigo_hash")

    op.alter_column("agendamento", "cliente_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("agendamento", "telefone_avulso")
    op.drop_column("agendamento", "nome_avulso")
