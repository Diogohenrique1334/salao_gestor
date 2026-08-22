"""schema inicial do salao

Revision ID: 0001_inicial
Revises:
Create Date: 2026-06-21

Cria todas as tabelas do MVP: cliente, cabeleireiro, servico,
cabeleireiro_servico (vinculo com desconto), horario_trabalho e agendamento.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_inicial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cliente",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=180), nullable=False),
        sa.Column("senha_hash", sa.String(length=200), nullable=False),
        sa.Column("telefone", sa.String(length=20), nullable=True),
        sa.Column("papel", sa.String(length=20), nullable=False, server_default="cliente"),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("email", name="uq_cliente_email"),
    )
    op.create_index("ix_cliente_email", "cliente", ["email"])

    op.create_table(
        "cabeleireiro",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("telefone", sa.String(length=20), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "servico",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("duracao_min", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("preco_base", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "cabeleireiro_servico",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cabeleireiro_id", sa.Integer(), nullable=False),
        sa.Column("servico_id", sa.Integer(), nullable=False),
        sa.Column("desconto_tipo", sa.String(length=20), nullable=True),
        sa.Column("desconto_valor", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["cabeleireiro_id"], ["cabeleireiro.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["servico_id"], ["servico.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("cabeleireiro_id", "servico_id", name="uq_cabeleireiro_servico"),
    )

    op.create_table(
        "horario_trabalho",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cabeleireiro_id", sa.Integer(), nullable=False),
        sa.Column("dia_semana", sa.Integer(), nullable=False),
        sa.Column("hora_inicio", sa.Time(), nullable=False),
        sa.Column("hora_fim", sa.Time(), nullable=False),
        sa.ForeignKeyConstraint(["cabeleireiro_id"], ["cabeleireiro.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "agendamento",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("cabeleireiro_id", sa.Integer(), nullable=False),
        sa.Column("servico_id", sa.Integer(), nullable=False),
        sa.Column("inicio", sa.DateTime(), nullable=False),
        sa.Column("fim", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="confirmado"),
        sa.Column("preco_aplicado", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("desconto_aplicado", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("canal_confirmacao", sa.String(length=40), nullable=True),
        sa.Column("lembrete_enviado_em", sa.DateTime(), nullable=True),
        sa.Column("confirmado_pelo_cliente_em", sa.DateTime(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"]),
        sa.ForeignKeyConstraint(["cabeleireiro_id"], ["cabeleireiro.id"]),
        sa.ForeignKeyConstraint(["servico_id"], ["servico.id"]),
    )
    op.create_index("ix_agendamento_inicio", "agendamento", ["inicio"])


def downgrade() -> None:
    op.drop_index("ix_agendamento_inicio", table_name="agendamento")
    op.drop_table("agendamento")
    op.drop_table("horario_trabalho")
    op.drop_table("cabeleireiro_servico")
    op.drop_table("servico")
    op.drop_table("cabeleireiro")
    op.drop_index("ix_cliente_email", table_name="cliente")
    op.drop_table("cliente")
