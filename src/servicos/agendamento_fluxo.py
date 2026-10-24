# ---------------------------------------------------------------------------
# servicos/agendamento_fluxo.py - orquestra CRIAR + NOTIFICAR, nessa ordem.
#
# POR QUE ESTA CAMADA EXISTE
# --------------------------
# A reserva precisa estar COMMITADA antes de qualquer I/O de rede. Antes, a UI
# fazia assim:
#
#     with sessao() as db:
#         ag = reservas.criar_reserva(...)
#         canais = eventos.enviar_confirmacao(db, ag)   # SMTP: ~1,2s
#         repo_ag.marcar_canal_confirmacao(...)
#     # <- o commit so acontecia AQUI
#
# Enquanto o SMTP rodava, a linha nova nao existia para as outras conexoes:
# `existe_conflito` nao a enxergava e liberava o MESMO horario de novo. Foi
# assim que #161 e #162 entraram ambos as 19:30 com o mesmo profissional.
#
# Aqui o commit fecha antes de o e-mail comecar. A notificacao e' um efeito
# colateral: se ela falhar, o agendamento continua valendo (perder o e-mail e'
# ruim; perder a reserva do cliente e' pior).
#
# Tambem e' o ponto UNICO do fluxo. Antes, paginas/agendar.py e
# componentes/atendimento_ui.py repetiam a sequencia, e so um dos dois seria
# corrigido.
#
# Camadas: ui -> AQUI -> servicos.reservas (regra) -> repositorios -> db
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.exc import IntegrityError

from src.db.engine import sessao
from src.notificacoes import eventos
from src.repositorios import agendamentos as repo_ag
from src.servicos import reservas


def _e_conflito_de_agenda(exc: IntegrityError) -> bool:
    """True se a IntegrityError veio da constraint de sobreposicao de agenda."""
    return "agendamento_sem_sobreposicao" in str(getattr(exc, "orig", exc))


def criar_e_notificar(
    *,
    cabeleireiro_id: int,
    servico_id: int,
    inicio: datetime,
    cliente_id: Optional[int] = None,
    nome_avulso: Optional[str] = None,
    telefone_avulso: Optional[str] = None,
) -> Tuple[int, List[str]]:
    """Cria a reserva, COMMITA, e so entao notifica. Retorna (id, canais).

    Propaga os erros de regra de `reservas` (SlotIndisponivel, HorarioBloqueado,
    ServicoNaoOferecido, IdentidadeAusente) para a UI tratar. Falha de
    notificacao NAO propaga: devolve canais vazio.
    """
    # --- transacao 1: grava e fecha. Nada de rede aqui dentro. ---
    try:
        with sessao() as db:
            ag = reservas.criar_reserva(
                db,
                cabeleireiro_id=cabeleireiro_id,
                servico_id=servico_id,
                inicio=inicio,
                cliente_id=cliente_id,
                nome_avulso=nome_avulso,
                telefone_avulso=telefone_avulso,
            )
            agendamento_id = int(ag.id)
    except IntegrityError as exc:
        # A constraint EXCLUDE do banco (migration 0008) e' a ultima barreira:
        # pega a sobreposicao que escapar da checagem da aplicacao. Traduzimos
        # para o erro de negocio p/ a UI mostrar a mesma mensagem amigavel de
        # sempre, em vez de vazar um traceback de SQL para o cliente.
        if _e_conflito_de_agenda(exc):
            raise reservas.SlotIndisponivel(inicio) from exc
        raise

    # --- o commit ja aconteceu: a reserva e' visivel p/ qualquer conexao ---
    canais: List[str] = []
    try:
        with sessao() as db:
            ag = repo_ag.buscar_por_id(db, agendamento_id)
            if ag is not None:
                canais = eventos.enviar_confirmacao(db, ag)
                repo_ag.marcar_canal_confirmacao(db, agendamento_id, ",".join(canais))
    except Exception:  # noqa: BLE001 - reserva ja vale; e-mail e' acessorio
        canais = []

    return agendamento_id, canais
