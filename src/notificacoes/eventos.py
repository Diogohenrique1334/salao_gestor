# ---------------------------------------------------------------------------
# notificacoes/eventos.py — PONTE banco -> notificacao.
#
# A partir de um Agendamento, busca os nomes (cliente/profissional/servico)
# via repositorios, monta a Mensagem (mensagens.py) e despacha (dispatcher).
# E' o ponto unico chamado por reservas/UI/jobs para notificar.
#
# DOIS LADOS: cada evento decide quem precisa saber.
#   - cliente      : confirmacao, lembrete, reagendamento, cancelamento
#   - profissional : cancelamento e reagendamento (imediatos — mexem na agenda
#                    dele), resumo diario, e novo agendamento SO se for para
#                    hoje (o resumo da manha ja saiu).
#
# O e-mail do profissional vem da CONTA DE LOGIN dele (Cliente com
# papel='cabeleireiro' apontando para o perfil) — o perfil Cabeleireiro nao tem
# coluna de e-mail. Sem conta criada, o Destinatario sai sem e-mail e o
# dispatcher apenas registra no console, sem quebrar.
#
# Retorna a lista de canais que tiveram sucesso NO ENVIO AO CLIENTE (contrato
# preservado p/ agendamento.canal_confirmacao).
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from src.constantes import (
    EVENTO_CANCELAMENTO,
    EVENTO_CONFIRMACAO,
    EVENTO_LEMBRETE,
    EVENTO_PROF_AGENDA_DIA,
    EVENTO_PROF_CANCELAMENTO,
    EVENTO_PROF_NOVO_AGENDAMENTO,
    EVENTO_PROF_REAGENDAMENTO,
    EVENTO_REAGENDAMENTO,
    EVENTO_RESET_SENHA,
)
from src.db.models import Agendamento
from src.notificacoes import dispatcher, mensagens
from src.notificacoes.base import Destinatario
from src.repositorios import agendamentos as repo_ag
from src.repositorios import cabeleireiros as repo_cab
from src.repositorios import clientes as repo_cli
from src.repositorios import servicos as repo_serv


# ----- montagem de destinatarios -------------------------------------------
def _contexto(db: Session, ag: Agendamento) -> Tuple[Destinatario, str, str]:
    """Retorna (destinatario_cliente, nome_servico, nome_cabeleireiro).

    Suporta walk-in: se nao ha cliente_id, usa nome_avulso/telefone_avulso.
    """
    prof = repo_cab.buscar_por_id(db, ag.cabeleireiro_id)
    servico = repo_serv.buscar_por_id(db, ag.servico_id)

    if ag.cliente_id is not None:
        cliente = repo_cli.buscar_por_id(db, ag.cliente_id)
        dest = Destinatario(
            nome=cliente.nome if cliente else "Cliente",
            email=cliente.email if cliente else None,
            telefone=cliente.telefone if cliente else None,
        )
    else:  # atendimento avulso (walk-in)
        dest = Destinatario(
            nome=ag.nome_avulso or "Cliente",
            email=None,
            telefone=ag.telefone_avulso,
        )
    return dest, (servico.nome if servico else "Servico"), (prof.nome if prof else "Profissional")


def _destinatario_profissional(db: Session, cabeleireiro_id: int) -> Destinatario:
    """Destinatario do cabeleireiro: nome do PERFIL + e-mail da CONTA DE LOGIN.

    Se o gestor ainda nao criou o login do profissional, volta sem e-mail — o
    dispatcher entao so registra no console (nada quebra).
    """
    prof = repo_cab.buscar_por_id(db, cabeleireiro_id)
    conta = repo_cli.buscar_por_cabeleireiro(db, cabeleireiro_id)
    return Destinatario(
        nome=prof.nome if prof else "Profissional",
        email=conta.email if conta else None,
        telefone=prof.telefone if prof else None,
    )


# ----- eventos do CLIENTE ---------------------------------------------------
def enviar_confirmacao(db: Session, ag: Agendamento) -> List[str]:
    """Confirma ao cliente. Avisa o profissional so se o horario for HOJE.

    Agendamento para os proximos dias aparece no resumo matinal; para hoje, o
    resumo ja saiu de manha, entao o aviso imediato evita o profissional ser
    pego de surpresa.
    """
    dest, servico, prof = _contexto(db, ag)
    msg = mensagens.confirmacao(
        nome_cliente=dest.nome, servico=servico, cabeleireiro=prof,
        inicio=ag.inicio, preco=ag.preco_aplicado,
    )
    canais = dispatcher.enviar(dest, msg, EVENTO_CONFIRMACAO)

    if ag.inicio.date() == date.today():
        dest_prof = _destinatario_profissional(db, ag.cabeleireiro_id)
        msg_prof = mensagens.novo_agendamento_profissional(
            nome_profissional=dest_prof.nome, nome_cliente=dest.nome,
            servico=servico, inicio=ag.inicio,
        )
        dispatcher.enviar(dest_prof, msg_prof, EVENTO_PROF_NOVO_AGENDAMENTO)

    return canais


def enviar_lembrete(db: Session, ag: Agendamento) -> List[str]:
    dest, servico, prof = _contexto(db, ag)
    msg = mensagens.lembrete(
        nome_cliente=dest.nome, servico=servico, cabeleireiro=prof, inicio=ag.inicio,
    )
    return dispatcher.enviar(dest, msg, EVENTO_LEMBRETE)


def enviar_reagendamento(db: Session, ag: Agendamento, inicio_antigo: datetime) -> List[str]:
    """Avisa cliente E profissional da REMARCACAO (de->para).

    `ag` ja esta no horario novo; `inicio_antigo` e' capturado antes de mover.
    """
    dest, servico, prof = _contexto(db, ag)
    msg = mensagens.reagendamento(
        nome_cliente=dest.nome, servico=servico, cabeleireiro=prof,
        inicio_antigo=inicio_antigo, inicio_novo=ag.inicio,
    )
    canais = dispatcher.enviar(dest, msg, EVENTO_REAGENDAMENTO)

    dest_prof = _destinatario_profissional(db, ag.cabeleireiro_id)
    msg_prof = mensagens.reagendamento_profissional(
        nome_profissional=dest_prof.nome, nome_cliente=dest.nome, servico=servico,
        inicio_antigo=inicio_antigo, inicio_novo=ag.inicio,
    )
    dispatcher.enviar(dest_prof, msg_prof, EVENTO_PROF_REAGENDAMENTO)
    return canais


def enviar_cancelamento(db: Session, ag: Agendamento) -> List[str]:
    """Avisa cliente E profissional — o buraco na agenda e' problema dele."""
    dest, servico, _prof = _contexto(db, ag)
    msg = mensagens.cancelamento(nome_cliente=dest.nome, servico=servico, inicio=ag.inicio)
    canais = dispatcher.enviar(dest, msg, EVENTO_CANCELAMENTO)

    dest_prof = _destinatario_profissional(db, ag.cabeleireiro_id)
    msg_prof = mensagens.cancelamento_profissional(
        nome_profissional=dest_prof.nome, nome_cliente=dest.nome,
        servico=servico, inicio=ag.inicio,
    )
    dispatcher.enviar(dest_prof, msg_prof, EVENTO_PROF_CANCELAMENTO)
    return canais


def enviar_codigo_reset(*, nome: str, email: str, codigo: str) -> str:
    """Envia o codigo de reset de senha (politica: e-mail). Retorna o canal usado."""
    dest = Destinatario(nome=nome, email=email)
    msg = mensagens.reset_senha(nome_cliente=nome, codigo=codigo)
    return dispatcher.enviar(dest, msg, EVENTO_RESET_SENHA)[0]


# ----- eventos do PROFISSIONAL ---------------------------------------------
def enviar_agenda_do_dia(db: Session, cabeleireiro_id: int, dia: Optional[date] = None) -> List[str]:
    """Resumo matinal da agenda de um profissional (chamado pelo job).

    AGENDA VAZIA NAO GERA E-MAIL: devolve [] sem enviar. Um aviso diario de
    "voce nao tem nada hoje" vira ruido e treina o profissional a ignorar a
    mensagem — inclusive nos dias em que ela importa.
    """
    dia = dia or date.today()
    inicio = datetime.combine(dia, time.min)
    fim = inicio + timedelta(days=1)

    agendamentos = repo_ag.listar_por_cabeleireiro_no_dia(db, cabeleireiro_id, inicio, fim)
    if not agendamentos:
        return []

    itens = [
        mensagens.ItemAgenda(
            inicio=a.inicio,
            fim=a.fim,
            cliente=(a.cliente.nome if a.cliente else (a.nome_avulso or "Avulso")),
            servico=(a.servico.nome if a.servico else "Servico"),
        )
        for a in agendamentos
    ]

    dest_prof = _destinatario_profissional(db, cabeleireiro_id)
    msg = mensagens.agenda_do_dia(
        nome_profissional=dest_prof.nome,
        dia=dia,
        itens=itens,
        primeiro_horario=(itens[0].inicio.strftime("%H:%M") if itens else None),
    )
    return dispatcher.enviar(dest_prof, msg, EVENTO_PROF_AGENDA_DIA)
