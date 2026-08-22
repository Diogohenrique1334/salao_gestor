# ---------------------------------------------------------------------------
# servicos/reservas.py - CAMADA DE NEGOCIO: ciclo de vida do agendamento.
#
# Orquestra criar / cancelar / reagendar uma reserva, aplicando as regras:
#   - o cabeleireiro precisa OFERECER o servico (vinculo ativo) -> define o preco
#   - o preco e' calculado com o desconto do vinculo (precificacao) e gravado
#     como snapshot no agendamento
#   - nao pode haver conflito de horario (double-booking) no mesmo cabeleireiro
#   - cancelar/reagendar exigem que o agendamento pertenca ao cliente
#
# As notificacoes (confirmacao) sao plugadas na Etapa 5 (dispatcher), mantendo
# esta camada focada na regra. Todas as funcoes recebem a Session.
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from src.constantes import (
    STATUS_ATIVOS,
    STATUS_CANCELADO,
    STATUS_CONCLUIDO,
    STATUS_NO_SHOW,
    STATUS_REAGENDADO,
)
from src.db.models import Agendamento
from src.repositorios import agendamentos as repo_ag
from src.repositorios import bloqueios as repo_bloqueios
from src.repositorios import servicos as repo_serv
from src.servicos import precificacao


# ----- erros de negocio ----------------------------------------------------
class ErroReserva(Exception):
    """Base p/ erros de regra de agendamento."""


class ServicoNaoOferecido(ErroReserva):
    """O cabeleireiro nao oferece o servico (sem vinculo ativo)."""


class SlotIndisponivel(ErroReserva):
    """O horario conflita com outro agendamento ativo."""


class HorarioBloqueado(ErroReserva):
    """O horario cai num bloqueio do cabeleireiro (ferias/folga)."""


class NaoAutorizado(ErroReserva):
    """Operacao sobre agendamento que nao pertence ao cliente."""


class IdentidadeAusente(ErroReserva):
    """Reserva sem cliente_id e sem nome_avulso (nao da p/ identificar)."""


class PresencaInvalida(ErroReserva):
    """Tentou dar baixa de presenca num agendamento que nao esta mais ativo."""


class CancelamentoInvalido(ErroReserva):
    """Tentou cancelar um agendamento que nao esta mais ativo (ja concluido/cancelado)."""


# ----- operacoes -----------------------------------------------------------
def criar_reserva(
    db: Session,
    *,
    cabeleireiro_id: int,
    servico_id: int,
    inicio: datetime,
    cliente_id: Optional[int] = None,
    nome_avulso: Optional[str] = None,
    telefone_avulso: Optional[str] = None,
) -> Agendamento:
    """Cria um agendamento confirmado, com preco (desconto aplicado) e sem conflito.

    Identidade: ou `cliente_id` (cliente com conta) ou `nome_avulso`
    (atendimento avulso/walk-in cadastrado pelo gestor).
    """
    if cliente_id is None and not (nome_avulso and nome_avulso.strip()):
        raise IdentidadeAusente()

    servico = repo_serv.buscar_por_id(db, servico_id)
    if servico is None or not servico.ativo:
        raise ServicoNaoOferecido(servico_id)

    vinculo = repo_serv.buscar_vinculo(db, cabeleireiro_id, servico_id)
    if vinculo is None or not vinculo.ativo:
        raise ServicoNaoOferecido(servico_id)

    fim = inicio + timedelta(minutes=int(servico.duracao_min))

    if repo_ag.existe_conflito(db, cabeleireiro_id=cabeleireiro_id, inicio=inicio, fim=fim):
        raise SlotIndisponivel(inicio)

    if repo_bloqueios.existe_no_intervalo(db, cabeleireiro_id=cabeleireiro_id, inicio=inicio, fim=fim):
        raise HorarioBloqueado(inicio)

    calc = precificacao.calcular_preco(servico.preco_base, vinculo.desconto_tipo, vinculo.desconto_valor)

    return repo_ag.criar(
        db,
        cliente_id=cliente_id,
        nome_avulso=nome_avulso,
        telefone_avulso=telefone_avulso,
        cabeleireiro_id=cabeleireiro_id,
        servico_id=servico_id,
        inicio=inicio,
        fim=fim,
        preco_aplicado=calc.preco_final,
        desconto_aplicado=calc.desconto,
    )


def cancelar_reserva(
    db: Session,
    *,
    agendamento_id: int,
    cliente_id: Optional[int] = None,
    cabeleireiro_id: Optional[int] = None,
    por_gestor: bool = False,
) -> Agendamento:
    """Cancela um agendamento ATIVO. Exige uma forma explicita de autorizacao:

      - `cliente_id`      : o proprio dono do agendamento (autoatendimento)
      - `cabeleireiro_id` : o profissional dono da agenda (ex.: ficou doente)
      - `por_gestor=True` : gestor, irrestrito (balcao do salao)

    Sem nenhum dos tres, nega - o default nao pode ser "pode tudo".
    """
    if not por_gestor and cliente_id is None and cabeleireiro_id is None:
        raise NaoAutorizado(agendamento_id)

    ag = repo_ag.buscar_por_id(db, agendamento_id)
    if ag is None:
        raise NaoAutorizado(agendamento_id)
    if cliente_id is not None and ag.cliente_id != cliente_id:
        raise NaoAutorizado(agendamento_id)
    if cabeleireiro_id is not None and ag.cabeleireiro_id != cabeleireiro_id:
        raise NaoAutorizado(agendamento_id)
    if ag.status not in STATUS_ATIVOS:
        raise CancelamentoInvalido(agendamento_id)

    repo_ag.atualizar_status(db, agendamento_id, STATUS_CANCELADO)
    return ag


def reagendar_reserva(
    db: Session, *, agendamento_id: int, cliente_id: int, novo_inicio: datetime
) -> Tuple[Agendamento, datetime]:
    """Move o agendamento do cliente p/ novo horario, sem conflito.

    Retorna (agendamento_ja_no_horario_novo, inicio_ANTIGO). O horario antigo
    so existe antes da escrita, e a notificacao de remarcacao precisa dele para
    dizer o de->para - por isso ele volta junto.
    """
    ag = repo_ag.buscar_por_id(db, agendamento_id)
    if ag is None or ag.cliente_id != cliente_id:
        raise NaoAutorizado(agendamento_id)

    servico = repo_serv.buscar_por_id(db, ag.servico_id)
    novo_fim = novo_inicio + timedelta(minutes=int(servico.duracao_min))

    if repo_ag.existe_conflito(
        db, cabeleireiro_id=ag.cabeleireiro_id, inicio=novo_inicio, fim=novo_fim, ignorar_id=ag.id
    ):
        raise SlotIndisponivel(novo_inicio)

    if repo_bloqueios.existe_no_intervalo(
        db, cabeleireiro_id=ag.cabeleireiro_id, inicio=novo_inicio, fim=novo_fim
    ):
        raise HorarioBloqueado(novo_inicio)

    inicio_antigo = ag.inicio  # capturar ANTES da escrita
    repo_ag.reagendar(db, agendamento_id, inicio=novo_inicio, fim=novo_fim)
    repo_ag.atualizar_status(db, agendamento_id, STATUS_REAGENDADO)
    return ag, inicio_antigo


def registrar_presenca(
    db: Session, *, agendamento_id: int, compareceu: bool, cabeleireiro_id: Optional[int] = None
) -> Agendamento:
    """Da baixa num agendamento ativo: comparecimento (concluido) ou falta (no_show).

    Quem da baixa e o gestor/cabeleireiro (nao o cliente). Se `cabeleireiro_id`
    vier, restringe a baixa aos agendamentos daquele profissional (o painel do
    cabeleireiro passa o proprio id; o gestor passa None e pode baixar qualquer).
    So agendamentos ATIVOS (confirmado/reagendado) podem receber baixa.
    """
    ag = repo_ag.buscar_por_id(db, agendamento_id)
    if ag is None or (cabeleireiro_id is not None and ag.cabeleireiro_id != cabeleireiro_id):
        raise NaoAutorizado(agendamento_id)
    if ag.status not in STATUS_ATIVOS:
        raise PresencaInvalida(agendamento_id)
    repo_ag.atualizar_status(
        db, agendamento_id, STATUS_CONCLUIDO if compareceu else STATUS_NO_SHOW
    )
    return ag
