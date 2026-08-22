"""nps (pesquisa de satisfacao pos-atendimento)

Revision ID: 0006_nps
Revises: 0005_bloqueio_agenda
Create Date: 2026-06-22

Cria nps_resposta: nota 0-10 (com comentario opcional) do cliente sobre um
atendimento concluido. Uma nota por agendamento (UNIQUE).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0006_nps"
down_revision = "0005_bloqueio_agenda"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nps_resposta",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agendamento_id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("nota", sa.Integer(), nullable=False),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agendamento_id"], ["agendamento.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"]),
        sa.UniqueConstraint("agendamento_id", name="uq_nps_agendamento"),
    )
    op.create_index("ix_nps_criado_em", "nps_resposta", ["criado_em"])


def downgrade() -> None:
    op.drop_index("ix_nps_criado_em", table_name="nps_resposta")
    op.drop_table("nps_resposta")
