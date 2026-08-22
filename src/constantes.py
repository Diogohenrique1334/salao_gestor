# ---------------------------------------------------------------------------
# constantes.py — vocabulario de dominio compartilhado entre as camadas.
#
# Centraliza os valores "magicos" (papeis, status de agendamento, tipos de
# desconto) para evitar strings soltas espalhadas pelo codigo.
# ---------------------------------------------------------------------------
from __future__ import annotations

# Papeis de usuario (coluna cliente.papel)
PAPEL_CLIENTE = "cliente"
PAPEL_GESTOR = "gestor"
PAPEL_CABELEIREIRO = "cabeleireiro"  # conta ligada a um perfil de Cabeleireiro
PAPEIS = (PAPEL_CLIENTE, PAPEL_GESTOR, PAPEL_CABELEIREIRO)

# Status do agendamento
STATUS_CONFIRMADO = "confirmado"
STATUS_CANCELADO = "cancelado"
STATUS_REAGENDADO = "reagendado"
STATUS_CONCLUIDO = "concluido"
STATUS_NO_SHOW = "no_show"
STATUS_AGENDAMENTO = (
    STATUS_CONFIRMADO,
    STATUS_CANCELADO,
    STATUS_REAGENDADO,
    STATUS_CONCLUIDO,
    STATUS_NO_SHOW,
)
# Status que ocupam o slot na agenda (impedem novo agendamento no mesmo horario)
STATUS_ATIVOS = (STATUS_CONFIRMADO, STATUS_REAGENDADO)

# Tipo de desconto do vinculo cabeleireiro<->servico
DESCONTO_PERCENTUAL = "percentual"  # desconto_valor em % (0-100)
DESCONTO_VALOR = "valor"            # desconto_valor em R$ absoluto
DESCONTO_TIPOS = (DESCONTO_PERCENTUAL, DESCONTO_VALOR)

# Canais de notificacao
CANAL_EMAIL = "email"
CANAL_WHATSAPP = "whatsapp"
CANAL_SMS = "sms"          # ainda sem implementacao (ver notificacoes/politica.py)
CANAL_CONSOLE = "console"

# Eventos de notificacao — chave da POLITICA de canais (notificacoes/politica.py).
# Existem para que "quem recebe o que, por qual canal" seja uma decisao unica e
# declarativa, em vez de "manda por todo canal configurado" (o que faria um
# canal pago como SMS disparar em todo evento).
EVENTO_CONFIRMACAO = "confirmacao"
EVENTO_LEMBRETE = "lembrete"
EVENTO_REAGENDAMENTO = "reagendamento"
EVENTO_CANCELAMENTO = "cancelamento"
EVENTO_RESET_SENHA = "reset_senha"
# eventos do lado do PROFISSIONAL (cabeleireiro)
EVENTO_PROF_NOVO_AGENDAMENTO = "prof_novo_agendamento"
EVENTO_PROF_REAGENDAMENTO = "prof_reagendamento"
EVENTO_PROF_CANCELAMENTO = "prof_cancelamento"
EVENTO_PROF_AGENDA_DIA = "prof_agenda_dia"

# NPS (Net Promoter Score) — faixas da nota 0-10
NPS_PROMOTOR_MIN = 9   # nota >= 9 => promotor
NPS_DETRATOR_MAX = 6   # nota <= 6 => detrator (7-8 = neutro)
