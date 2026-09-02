"""horario de almoco recorrente do cabeleireiro

Revision ID: 0007_almoco_cabeleireiro
Revises: 0006_nps
Create Date: 2026-09-01

Adiciona almoco_inicio/almoco_fim (Time, nullable) ao cabeleireiro. E' um
intervalo recorrente que vale para TODO dia de trabalho — o gestor configura
uma vez, sem bloquear dia a dia. Entra como "ocupado" no calculo de slots.
None/None = sem almoco.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0007_almoco_cabeleireiro"
down_revision = "0006_nps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cabeleireiro", sa.Column("almoco_inicio", sa.Time(), nullable=True))
    op.add_column("cabeleireiro", sa.Column("almoco_fim", sa.Time(), nullable=True))


def downgrade() -> None:
    op.drop_column("cabeleireiro", "almoco_fim")
    op.drop_column("cabeleireiro", "almoco_inicio")
