"""almoco por dia da semana (sai do cabeleireiro, entra no horario de trabalho)

Revision ID: 0009_almoco_por_dia
Revises: 0008_sem_sobreposicao
Create Date: 2026-11-09

POR QUE
-------
`cabeleireiro.almoco_inicio/fim` e' UM intervalo que valia para TODO dia de
trabalho. Na pratica o salao almoca meia hora no sabado e uma hora nos demais
dias — nao havia como expressar isso.

O almoco pertence ao DIA de trabalho, nao ao profissional: `horario_trabalho`
ja e' (cabeleireiro, dia_semana, hora_inicio, hora_fim), uma linha por dia.
Conferido no banco de producao antes de escolher este desenho: nenhum
profissional tem duas faixas no mesmo dia da semana, entao cada linha comporta
seu proprio almoco sem ambiguidade.

AS COLUNAS ANTIGAS FICAM (por enquanto)
---------------------------------------
`cabeleireiro.almoco_inicio/fim` NAO sao removidas aqui, de proposito. A
migration e' aplicada da maquina do Diogo, enquanto a versao ANTIGA do app
ainda esta rodando no Render: derrubar a coluna agora quebraria o app em
producao ate o deploy terminar. O codigo novo para de le-las; uma migration
futura pode dropa-las com seguranca.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0009_almoco_por_dia"
down_revision = "0008_sem_sobreposicao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("horario_trabalho", sa.Column("almoco_inicio", sa.Time(), nullable=True))
    op.add_column("horario_trabalho", sa.Column("almoco_fim", sa.Time(), nullable=True))

    # Copia o almoco atual do profissional para TODOS os dias dele: no primeiro
    # dia o comportamento fica identico ao de antes. O gestor so precisa mexer
    # no dia que for diferente (o sabado).
    op.execute(
        """
        UPDATE horario_trabalho h
           SET almoco_inicio = c.almoco_inicio,
               almoco_fim    = c.almoco_fim
          FROM cabeleireiro c
         WHERE c.id = h.cabeleireiro_id
           AND c.almoco_inicio IS NOT NULL
           AND c.almoco_fim    IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("horario_trabalho", "almoco_fim")
    op.drop_column("horario_trabalho", "almoco_inicio")
