"""foto do cabeleireiro (nome do arquivo, nao a imagem)

Revision ID: 0011_foto_cabeleireiro
Revises: 0010_servico_ordem_e_dias
Create Date: 2026-11-09

Guarda apenas o NOME DO ARQUIVO (ex.: "marcos.jpg"), que vive em
`assets/profissionais/` e entra na imagem Docker junto com o resto do projeto.

Por que nao os bytes: as fotos da equipe praticamente nao mudam, e colocar
imagem em tabela transacional faz todo backup carregar as imagens e um
`SELECT *` distraido puxar centenas de KB sem precisar. Com o nome do arquivo o
custo no banco e' de ~20 bytes por profissional.

A contrapartida, aceita de propria vontade: trocar uma foto exige commit e
deploy. Para uma equipe de tres pessoas isso acontece quando alguem entra ou
sai. Se um dia a equipe crescer ou o gestor quiser trocar a foto sozinho pela
tela, ai sim vale upload de verdade para storage externo.

NULL = sem foto; a UI cai no circulo com as iniciais.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0011_foto_cabeleireiro"
down_revision = "0010_servico_ordem_e_dias"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cabeleireiro", sa.Column("foto", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("cabeleireiro", "foto")
