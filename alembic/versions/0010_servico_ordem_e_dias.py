"""ordem de exibicao e dias da semana permitidos por servico

Revision ID: 0010_servico_ordem_e_dias
Revises: 0009_almoco_por_dia
Create Date: 2026-11-09

DUAS COLUNAS EM `servico`:

`ordem` — posicao na lista que o cliente ve. Antes era alfabetica, o que punha
"Alisante" na frente de "Corte" (260 agendamentos em 90 dias). Fica editavel
pelo gestor para nao precisar de deploy a cada mudanca de ideia.
O valor inicial vem da POPULARIDADE REAL (agendamentos nos ultimos 90 dias),
que e' um palpite inicial melhor do que alfabetico ou do que uma lista chutada.

`dias_semana` — em quais dias o servico pode ser marcado, como lista de
indices separados por virgula no padrao datetime.weekday(): 0=segunda ...
6=domingo. Default: todos. Caso real que motivou: o "Mensal" nao deve ser
marcavel no fim de semana (ja tinha 8 marcacoes em sabados).

Formato texto em vez de tabela ou bitmask de proposito: a UI e' um grupo de 7
checkboxes, o conteudo cabe numa olhada no banco e nao exige join.

A REGRA VALE SO PARA MARCACAO NOVA: os agendamentos que ja existem em dias
agora proibidos continuam validos e visiveis. Regra nova nao apaga compromisso
ja firmado com o cliente.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0010_servico_ordem_e_dias"
down_revision = "0009_almoco_por_dia"
branch_labels = None
depends_on = None

TODOS_OS_DIAS = "0,1,2,3,4,5,6"


def upgrade() -> None:
    op.add_column(
        "servico",
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="100"),
    )
    op.add_column(
        "servico",
        sa.Column(
            "dias_semana",
            sa.String(length=20),
            nullable=False,
            server_default=TODOS_OS_DIAS,
        ),
    )

    # Semeia a ordem pela popularidade dos ultimos 90 dias (mais marcado = 1).
    # Empate e servico sem nenhum agendamento caem para o fim, por nome.
    op.execute(
        """
        UPDATE servico s
           SET ordem = p.posicao
          FROM (
                SELECT x.id,
                       row_number() OVER (ORDER BY x.marcacoes DESC, x.nome) AS posicao
                  FROM (
                        SELECT sv.id,
                               sv.nome,
                               count(a.id) AS marcacoes
                          FROM servico sv
                          LEFT JOIN agendamento a
                                 ON a.servico_id = sv.id
                                AND a.criado_em > now() - interval '90 days'
                         GROUP BY sv.id, sv.nome
                       ) x
               ) p
         WHERE p.id = s.id
        """
    )


def downgrade() -> None:
    op.drop_column("servico", "dias_semana")
    op.drop_column("servico", "ordem")
