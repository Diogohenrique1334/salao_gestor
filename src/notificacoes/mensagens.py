# ---------------------------------------------------------------------------
# notificacoes/mensagens.py — construtores de texto (PUROS, sem banco).
#
# Recebem dados primitivos e devolvem Mensagem (assunto/corpo + params do
# template WhatsApp). A ponte com o banco (buscar nomes) fica em eventos.py.
#
# Duas familias:
#   - CLIENTE      : confirmacao / lembrete / reagendamento / cancelamento
#   - PROFISSIONAL : novo_agendamento / reagendamento / cancelamento / agenda_do_dia
#
# O texto do CORPO vai para o cliente final do salao: escrever com acentuacao
# correta (o resto do codigo segue sem acento por convencao, o texto exibido
# nao).
# ---------------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from src.config.settings import get_settings
from src.notificacoes.base import Mensagem


def _salao() -> str:
    """Nome do salao (configuravel por SALAO_NOME / [salao].nome)."""
    return get_settings().salao.nome


def _data_hora(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y às %H:%M")


def _hora(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def _dia(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _moeda(valor: Decimal) -> str:
    """R$ 1234.5 -> 'R$ 1.234,50' (formato brasileiro)."""
    texto = f"{Decimal(valor):,.2f}"                      # 1,234.50 (padrao en)
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"


# ===========================================================================
# CLIENTE
# ===========================================================================
def confirmacao(
    *, nome_cliente: str, servico: str, cabeleireiro: str, inicio: datetime, preco: Decimal
) -> Mensagem:
    wpp = get_settings().whatsapp
    salao, quando, valor = _salao(), _data_hora(inicio), _moeda(preco)
    corpo = (
        f"Olá, {nome_cliente}! Seu agendamento no {salao} está confirmado.\n\n"
        f"Serviço: {servico}\nProfissional: {cabeleireiro}\n"
        f"Quando: {quando}\nValor: {valor}\n\n"
        f"Até lá! Para cancelar ou reagendar, acesse o app."
    )
    return Mensagem(
        assunto=f"Agendamento confirmado - {quando}",
        corpo=corpo,
        template_whatsapp=wpp.template_confirmacao,
        template_params=[nome_cliente, servico, cabeleireiro, quando, valor],
    )


def lembrete(*, nome_cliente: str, servico: str, cabeleireiro: str, inicio: datetime) -> Mensagem:
    wpp = get_settings().whatsapp
    salao, quando = _salao(), _data_hora(inicio)
    corpo = (
        f"Olá, {nome_cliente}! Lembrete do seu horário no {salao}.\n\n"
        f"Serviço: {servico}\nProfissional: {cabeleireiro}\nQuando: {quando}\n\n"
        f"Se precisar, você pode reagendar ou cancelar pelo app."
    )
    return Mensagem(
        assunto=f"Lembrete: seu horário amanhã - {quando}",
        corpo=corpo,
        template_whatsapp=wpp.template_lembrete,
        template_params=[nome_cliente, servico, cabeleireiro, quando],
    )


def reagendamento(
    *, nome_cliente: str, servico: str, cabeleireiro: str, inicio_antigo: datetime, inicio_novo: datetime
) -> Mensagem:
    """Aviso de REMARCACAO — deixa explicito o de->para.

    Existe separado de `confirmacao` porque reaproveitar aquele texto faz o
    cliente receber "agendamento confirmado" sem perceber que o horario mudou.
    """
    salao, antes, agora = _salao(), _data_hora(inicio_antigo), _data_hora(inicio_novo)
    corpo = (
        f"Olá, {nome_cliente}! Seu agendamento no {salao} foi remarcado.\n\n"
        f"Serviço: {servico}\nProfissional: {cabeleireiro}\n\n"
        f"Horário anterior: {antes}\nNOVO horário: {agora}\n\n"
        f"Atenção: anote o novo horário. Até lá!"
    )
    return Mensagem(assunto=f"Agendamento REMARCADO - agora {agora}", corpo=corpo)


def cancelamento(*, nome_cliente: str, servico: str, inicio: datetime) -> Mensagem:
    salao, quando = _salao(), _data_hora(inicio)
    corpo = (
        f"Olá, {nome_cliente}. Seu agendamento de {servico} em {quando} foi cancelado.\n"
        f"Esperamos te ver em breve no {salao}!"
    )
    # cancelamento e' informativo: sem template (texto livre basta no console/email)
    return Mensagem(assunto=f"Agendamento cancelado - {quando}", corpo=corpo)


def reset_senha(*, nome_cliente: str, codigo: str) -> Mensagem:
    corpo = (
        f"Olá, {nome_cliente}. Recebemos um pedido para redefinir sua senha no {_salao()}.\n\n"
        f"Seu código de verificação é: {codigo}\n\n"
        f"Ele expira em 30 minutos. Se você não pediu, ignore este e-mail."
    )
    return Mensagem(assunto="Código para redefinir sua senha", corpo=corpo)


# ===========================================================================
# PROFISSIONAL (cabeleireiro)
# ===========================================================================
def novo_agendamento_profissional(
    *, nome_profissional: str, nome_cliente: str, servico: str, inicio: datetime
) -> Mensagem:
    quando = _data_hora(inicio)
    corpo = (
        f"Olá, {nome_profissional}. Você tem um novo agendamento.\n\n"
        f"Cliente: {nome_cliente}\nServiço: {servico}\nQuando: {quando}\n\n"
        f"Sua agenda completa está no painel do app."
    )
    return Mensagem(assunto=f"Novo agendamento - {quando}", corpo=corpo)


def cancelamento_profissional(
    *, nome_profissional: str, nome_cliente: str, servico: str, inicio: datetime
) -> Mensagem:
    """Alerta IMEDIATO: e' o evento que abre um buraco na agenda do profissional."""
    quando = _data_hora(inicio)
    corpo = (
        f"Olá, {nome_profissional}. Um agendamento da sua agenda foi cancelado.\n\n"
        f"Cliente: {nome_cliente}\nServiço: {servico}\nHorário vago: {quando}\n\n"
        f"O horário voltou a ficar disponível para novas reservas."
    )
    return Mensagem(assunto=f"Cancelamento na sua agenda - {quando}", corpo=corpo)


def reagendamento_profissional(
    *, nome_profissional: str, nome_cliente: str, servico: str,
    inicio_antigo: datetime, inicio_novo: datetime,
) -> Mensagem:
    antes, agora = _data_hora(inicio_antigo), _data_hora(inicio_novo)
    corpo = (
        f"Olá, {nome_profissional}. Um cliente remarcou o horário.\n\n"
        f"Cliente: {nome_cliente}\nServiço: {servico}\n\n"
        f"Saiu de: {antes}\nEntrou em: {agora}"
    )
    return Mensagem(assunto=f"Remarcação na sua agenda - {agora}", corpo=corpo)


@dataclass(frozen=True)
class ItemAgenda:
    """Uma linha do resumo diario (mantem `agenda_do_dia` puro/sem banco)."""

    inicio: datetime
    fim: datetime
    cliente: str
    servico: str


def agenda_do_dia(
    *, nome_profissional: str, dia: date, itens: List[ItemAgenda], primeiro_horario: Optional[str] = None
) -> Mensagem:
    """Resumo matinal da agenda. Substitui o e-mail a cada agendamento (ruido)."""
    salao, quando = _salao(), _dia(dia)
    if not itens:
        corpo = (
            f"Olá, {nome_profissional}. Bom dia!\n\n"
            f"Você não tem agendamentos para {quando}."
        )
        return Mensagem(assunto=f"Sua agenda de {quando} - sem atendimentos", corpo=corpo)

    linhas = "\n".join(
        f"  {_hora(i.inicio)} - {_hora(i.fim)}  |  {i.cliente}  |  {i.servico}" for i in itens
    )
    total = len(itens)
    plural = "atendimento" if total == 1 else "atendimentos"
    abertura = f" Começa às {primeiro_horario}." if primeiro_horario else ""
    corpo = (
        f"Olá, {nome_profissional}. Bom dia!\n\n"
        f"Você tem {total} {plural} hoje ({quando}).{abertura}\n\n"
        f"{linhas}\n\n"
        f"Bom trabalho! — {salao}"
    )
    return Mensagem(assunto=f"Sua agenda de {quando} - {total} {plural}", corpo=corpo)
