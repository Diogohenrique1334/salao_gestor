"""impede dois agendamentos ativos sobrepostos no mesmo cabeleireiro

Revision ID: 0008_sem_sobreposicao
Revises: 0007_almoco_cabeleireiro
Create Date: 2026-10-23

POR QUE
-------
Ate aqui a unica defesa contra double-booking era o SELECT `existe_conflito`
da aplicacao. Entre esse SELECT e o INSERT existe uma janela, e enquanto o
e-mail de confirmacao era enviado DENTRO da transacao essa janela durava
~1,2 segundo. Resultado real em producao: #161 e #162, mesmo cliente, mesmo
profissional, ambos 23/10/2026 19:30, ambos confirmados.

A ordem de commit ja foi corrigida em servicos/agendamento_fluxo.py. Esta
constraint e' a barreira que nao depende de a aplicacao estar certa.

SEMANTICA
---------
- `tsrange(inicio, fim, '[)')`: meio-aberto, igual ao teste da aplicacao
  (`existente.inicio < novo.fim AND existente.fim > novo.inicio`). Logo,
  atendimentos encostados (um acaba 14:00, o proximo comeca 14:00) NAO
  conflitam.
- `WHERE status IN ('confirmado','reagendado')`: espelha STATUS_ATIVOS. Um
  horario cancelado/concluido/faltou nao bloqueia o slot — e' o mesmo criterio
  que `repo_ag.existe_conflito` e `listar_por_cabeleireiro_no_dia` usam.
- Remarcacao continua funcionando: `reagendar_reserva` MOVE a propria linha,
  e uma linha nunca conflita com ela mesma.
- `inicio`/`fim` sao timestamp SEM fuso (hora local de parede, convencao do
  projeto) — por isso `tsrange` e nao `tstzrange`.

ATENCAO AO APLICAR
------------------
`btree_gist` e' necessario para comparar o inteiro cabeleireiro_id dentro de
um indice GiST. A criacao da constraint FALHA se ja existir qualquer par ativo
sobreposto no banco — e' preciso cancelar as duplicatas antes. Para listar:

    SELECT a.id, b.id, a.cabeleireiro_id, a.inicio
    FROM agendamento a
    JOIN agendamento b ON b.cabeleireiro_id = a.cabeleireiro_id AND b.id > a.id
                      AND a.inicio < b.fim AND a.fim > b.inicio
    WHERE a.status IN ('confirmado','reagendado')
      AND b.status IN ('confirmado','reagendado');
"""
from __future__ import annotations

from alembic import op

revision = "0008_sem_sobreposicao"
down_revision = "0007_almoco_cabeleireiro"
branch_labels = None
depends_on = None

NOME = "agendamento_sem_sobreposicao"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        f"""
        ALTER TABLE agendamento
          ADD CONSTRAINT {NOME}
          EXCLUDE USING gist (
              cabeleireiro_id WITH =,
              tsrange(inicio, fim, '[)') WITH &&
          )
          WHERE (status IN ('confirmado', 'reagendado'))
        """
    )


def downgrade() -> None:
    op.execute(f"ALTER TABLE agendamento DROP CONSTRAINT IF EXISTS {NOME}")
