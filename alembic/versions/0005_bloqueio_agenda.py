"""bloqueio de agenda (ferias/folga)

Revision ID: 0005_bloqueio_agenda
Revises: 0004_data_nascimento
Create Date: 2026-06-22

Cria bloqueio_agenda: periodos em que o cabeleireiro nao atende. inicio/fim sao
hora local naive (fim exclusivo). Entram como "ocupado" no calculo de slots e
barram novas reservas; nao cancelam agendamentos pre-existentes.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005_bloqueio_agenda"
down_revision = "0004_data_nascimento"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bloqueio_agenda",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cabeleireiro_id", sa.Integer(), nullable=False),
        sa.Column("inicio", sa.DateTime(), nullable=False),
        sa.Column("fim", sa.DateTime(), nullable=False),
        sa.Column("motivo", sa.String(length=120), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["cabeleireiro_id"], ["cabeleireiro.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_bloqueio_cabeleireiro_inicio", "bloqueio_agenda", ["cabeleireiro_id", "inicio"]
    )


def downgrade() -> None:
    op.drop_index("ix_bloqueio_cabeleireiro_inicio", table_name="bloqueio_agenda")
    op.drop_table("bloqueio_agenda")
