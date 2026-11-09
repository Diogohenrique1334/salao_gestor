# ---------------------------------------------------------------------------
# ui/paginas/agendar.py - fluxo de agendamento do cliente.
#
# Passos: SERVICO -> PROFISSIONAL -> dia -> horario -> confirmar.
#
# POR QUE O SERVICO VEM ANTES DO PROFISSIONAL
# -------------------------------------------
# Com o servico ja escolhido, o card de cada profissional pode mostrar coisa
# que ajuda a decidir de verdade: a PROXIMA VAGA real (que depende da duracao
# do servico) e o PRECO daquele servico com aquele profissional (que depende do
# desconto do vinculo). Na ordem antiga isso era impossivel - a vaga teria de
# ser chutada com uma duracao generica.
#
# E O PROFISSIONAL NAO VEM PRE-ESCOLHIDO
# --------------------------------------
# Era um st.selectbox, que sempre marca o primeiro item. Como a listagem e'
# alfabetica, o default era sempre o mesmo profissional: o cliente descia para
# o servico sem perceber que tinha "escolhido" alguem, e aparecia no salao
# esperando outra pessoa. Agora sao cards que exigem um toque, e o escolhido
# fica visivel numa faixa ate o fim do fluxo.
#
# A criacao usa servicos.agendamento_fluxo (grava, COMMITA, so entao notifica).
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

import streamlit as st

from src.constantes import NOMES_DIAS_SEMANA
from src.db.engine import sessao
from src.repositorios import cabeleireiros as repo_cab
from src.repositorios import servicos as repo_serv
from src.servicos import agenda, agendamento_fluxo, precificacao, reservas
from src.ui.componentes import acao_unica, guards, styles


_CHAVE_CONFIRMADO = "agendamento_confirmado"
# Nome da acao de confirmar (ver componentes/acao_unica.py). O botao fica
# DESABILITADO na tela enquanto a reserva e' gravada: cliques enfileirados
# pelo navegador chegavam como reruns independentes, cada um com o botao em
# True, e cada um virava uma reserva.
_ACAO_CONFIRMAR = "agendar_confirmar"
# Impressao da lista de horarios que o cliente REALMENTE viu. O selectbox do
# Streamlit trafega o INDICE, nao o valor: se a lista mudar entre a tela e o
# clique, o mesmo indice aponta para outro horario. Comparar a lista detecta
# isso e nos faz recusar em vez de reservar um horario que ninguem escolheu.
_CHAVE_SLOTS_NA_TELA = "agendamento_slots_na_tela"
# Profissional escolhido. Vive em session_state porque a escolha e' por BOTAO
# (card), nao por widget com valor proprio.
_CHAVE_PROF = "agendar_prof_id"


def _liberar_trava() -> None:
    acao_unica.liberar(_ACAO_CONFIRMAR)


def _reiniciar_fluxo() -> None:
    """Volta o fluxo ao inicio (usado ao confirmar e ao trocar de profissional)."""
    _liberar_trava()
    st.session_state.pop(_CHAVE_SLOTS_NA_TELA, None)
    st.session_state.pop(_CHAVE_PROF, None)


def _aviso_telefone(usuario: dict) -> None:
    if not usuario.get("telefone"):
        st.caption("ℹ️ Voce ainda nao cadastrou WhatsApp, a confirmacao por WhatsApp "
                   "depende disso (atualize em 'Meus agendamentos' futuramente).")


def _tela_confirmacao(dados: dict) -> None:
    """Tela dedicada de sucesso - substitui o balao/toast por uma mudanca de tela."""
    st.markdown("## ✅ Agendamento confirmado!")
    st.markdown('<div class="bloco-card">', unsafe_allow_html=True)
    st.markdown(
        f"### {dados['servico']}\n"
        f"**Profissional:** {dados['prof']}  \n"
        f"**Quando:** {dados['inicio'].strftime('%d/%m/%Y às %H:%M')}  \n"
        f"**Valor:** {styles.moeda_br(dados['preco'])}",
    )
    st.markdown("</div>", unsafe_allow_html=True)
    if dados.get("canais"):
        st.caption(f"Enviamos a confirmacao por: {', '.join(dados['canais'])}.")
        # Aviso de spam SO quando o e-mail realmente saiu: o Gmail costuma filtrar
        # a primeira mensagem de um remetente novo. Dito aqui, no momento em que o
        # cliente vai procurar, evita o "nao recebi" virar suporte para o salao.
        if "email" in dados["canais"]:
            st.caption("📩 Não achou o e-mail? Veja a **caixa de spam** e marque como "
                       "\"não é spam\" - assim os próximos chegam direto.")
    st.info("Você pode ver, remarcar ou cancelar em **Meus agendamentos** (no menu ao lado).")
    # Secundario e estreito DE PROPOSITO: antes era primario e de largura
    # total, igualzinho ao "Confirmar agendamento" e na mesma posicao da tela.
    # Quem clicava duas vezes no mesmo ponto voltava ao formulario e confirmava
    # de novo sem perceber.
    if st.button("Agendar outro horário"):
        del st.session_state[_CHAVE_CONFIRMADO]
        _reiniciar_fluxo()
        st.rerun()


# ----- passo 1: servico -----------------------------------------------------
def _passo_servico(servicos) -> Tuple[object, object]:
    """Lista aberta de servicos, na ORDEM definida pelo gestor."""
    styles.titulo_secao("1. Qual servico você quer?")

    # RADIO, nao selectbox: sao 11 servicos e cinco comecam com "Corte"
    # (Corte, Corte e alisante, Corte e barba, Corte e luzes, Corte e
    # sombrancelha). Num menu fechado, com a fonte pequena do Streamlit, viram
    # cinco linhas quase identicas no celular - e o cliente marcava o errado.
    indice = st.radio(
        "Servico",
        options=range(len(servicos)),
        format_func=lambda i: servicos[i].nome,
        captions=[
            f"{styles.moeda_br(s.preco_base)} - {s.duracao_min} min" for s in servicos
        ],
        label_visibility="collapsed",
    )
    return servicos[indice]


# ----- passo 2: profissional ------------------------------------------------
def _jornada(horarios) -> str:
    """Dias em que o profissional atende: 'Ter a Sab' ou 'Seg, Qua, Sex'.

    SO os dias, de proposito. A versao com "a partir das Xh" usava a hora mais
    cedo da semana e mentia: o Guilherme abre 9h no sabado mas so 13h de terca
    a sexta, e o card prometia 9h todo dia. A hora de verdade quem da e' a
    proxima vaga, que e' calculada para o servico escolhido.
    """
    if not horarios:
        return "sem dias definidos"
    dias = sorted({h.dia_semana for h in horarios})
    abrev = [NOMES_DIAS_SEMANA[d][:3] for d in dias]
    if len(dias) > 2 and dias == list(range(dias[0], dias[-1] + 1)):
        return f"Atende de {abrev[0]} a {abrev[-1]}"
    return "Atende " + ", ".join(abrev)


def _texto_vaga(quando: Optional[datetime]) -> Optional[str]:
    if quando is None:
        return None
    dias = (quando.date() - datetime.now().date()).days
    if dias == 0:
        return f"livre hoje às {quando.strftime('%H:%M')}"
    if dias == 1:
        return f"livre amanhã às {quando.strftime('%H:%M')}"
    return f"livre {quando.strftime('%d/%m')} às {quando.strftime('%H:%M')}"


def _proxima_vaga(db, cabeleireiro_id: int, servico_id: int) -> Optional[datetime]:
    """Primeiro horario livre do profissional PARA ESTE servico (ou None)."""
    dias = agenda.proximos_dias_disponiveis(
        db, cabeleireiro_id=cabeleireiro_id, servico_id=servico_id, max_dias=1
    )
    if not dias:
        return None
    slots = agenda.horarios_disponiveis(
        db, cabeleireiro_id=cabeleireiro_id, dia=dias[0], servico_id=servico_id
    )
    return slots[0] if slots else None


def _opcoes_profissionais(db, servico) -> List[dict]:
    """Quem oferece o servico, com preco, jornada e proxima vaga."""
    opcoes: List[dict] = []
    for vinculo in repo_serv.listar_vinculos_do_servico(db, servico.id):
        prof = repo_cab.buscar_por_id(db, vinculo.cabeleireiro_id)
        if prof is None or not prof.ativo:
            continue
        opcoes.append({
            "prof": prof,
            "calc": precificacao.calcular_preco(
                servico.preco_base, vinculo.desconto_tipo, vinculo.desconto_valor
            ),
            "jornada": _jornada(repo_cab.listar_horarios(db, prof.id)),
            "vaga": _proxima_vaga(db, prof.id, servico.id),
        })
    opcoes.sort(key=lambda o: o["prof"].nome)
    return opcoes


def _card_profissional(opcao: dict) -> bool:
    """Card clicavel. True quando o cliente escolhe este profissional."""
    prof = opcao["prof"]
    with st.container(border=True):
        col_foto, col_txt = st.columns([1, 3.4], vertical_alignment="center")
        with col_foto:
            caminho = styles.caminho_foto(getattr(prof, "foto", None))
            if caminho is not None:
                st.markdown(styles.avatar_foto(caminho, 72), unsafe_allow_html=True)
            else:
                st.markdown(styles.avatar_iniciais(prof.nome, 72), unsafe_allow_html=True)
        with col_txt:
            st.markdown(f"<div class='ag-quem'>{prof.nome}</div>", unsafe_allow_html=True)
            st.caption(opcao["jornada"])
            vaga = _texto_vaga(opcao["vaga"])
            if vaga:
                st.markdown(
                    styles.badge(vaga, styles.COR_DESTAQUE, styles.COR_SOBRE_DESTAQUE),
                    unsafe_allow_html=True,
                )
            else:
                st.caption("sem horário livre nos próximos dias")
        return st.button(f"Escolher {prof.nome}", key=f"escolher_prof_{prof.id}",
                         type="primary", use_container_width=True)


def _passo_profissional(opcoes: List[dict]) -> Optional[dict]:
    """Devolve a opcao escolhida, ou None enquanto o cliente nao escolher."""
    por_id = {o["prof"].id: o for o in opcoes}
    escolhido = st.session_state.get(_CHAVE_PROF)
    # trocou de servico e quem estava escolhido nao oferece o novo
    if escolhido is not None and escolhido not in por_id:
        st.session_state.pop(_CHAVE_PROF, None)
        escolhido = None

    if escolhido is not None:
        opcao = por_id[escolhido]
        col_a, col_b = st.columns([3, 1], vertical_alignment="center")
        col_a.markdown(f"**Agendando com {opcao['prof'].nome}**")
        if col_b.button("Trocar", key="trocar_prof", use_container_width=True):
            st.session_state.pop(_CHAVE_PROF, None)
            st.session_state.pop(_CHAVE_SLOTS_NA_TELA, None)
            st.rerun()
        return opcao

    styles.titulo_secao("2. Com quem você quer cortar?")
    st.caption("Toque no profissional. Nada vem escolhido.")
    for opcao in opcoes:
        if _card_profissional(opcao):
            st.session_state[_CHAVE_PROF] = opcao["prof"].id
            st.session_state.pop(_CHAVE_SLOTS_NA_TELA, None)
            st.rerun()
    return None


# ----- pagina ---------------------------------------------------------------
def render() -> None:
    styles.aplicar_estilo_base()
    usuario = guards.require_login()

    # se acabou de confirmar, mostra a tela de sucesso e PARA aqui
    if _CHAVE_CONFIRMADO in st.session_state:
        _tela_confirmacao(st.session_state[_CHAVE_CONFIRMADO])
        return

    st.markdown("## 🗓️ Agendar")
    _aviso_telefone(usuario)

    # 1) Servico
    with sessao() as db:
        servicos = repo_serv.listar(db)   # ativos, na ordem do gestor
    if not servicos:
        st.warning("Nenhum servico disponivel no momento.")
        return
    servico = _passo_servico(servicos)

    # 2) Profissional que oferece esse servico
    with sessao() as db:
        opcoes = _opcoes_profissionais(db, servico)
    if not opcoes:
        st.warning("Nenhum profissional oferece este servico no momento. Escolha outro.")
        return
    opcao = _passo_profissional(opcoes)
    if opcao is None:
        return          # ainda nao escolheu: o resto do fluxo nem aparece
    prof, calc = opcao["prof"], opcao["calc"]

    if calc.desconto > 0:
        st.markdown(
            styles.badge(f"Desconto: {styles.moeda_br(calc.desconto)}",
                         styles.COR_DESTAQUE, styles.COR_SOBRE_DESTAQUE),
            unsafe_allow_html=True,
        )

    # 3) Dia (apenas dias que realmente tem vaga p/ este cabeleireiro+servico)
    styles.titulo_secao("3. Escolha o dia")
    with sessao() as db:
        dias = agenda.proximos_dias_disponiveis(
            db, cabeleireiro_id=prof.id, servico_id=servico.id, max_dias=30
        )
    if not dias:
        st.info(f"{prof.nome} nao tem horarios livres para este servico nos proximos dias.")
        return
    dia = st.selectbox("Dia", dias, format_func=styles.formatar_data_br)

    # 4) Slots livres
    styles.titulo_secao("4. Escolha o horario")
    with sessao() as db:
        slots = agenda.horarios_disponiveis(
            db, cabeleireiro_id=prof.id, dia=dia, servico_id=servico.id
        )
    if not slots:
        st.info("Sem horarios livres nesse dia.")
        return
    slot = st.selectbox("Horario", slots, format_func=lambda dt: dt.strftime("%H:%M"))

    # Guarda a lista EXATA que foi desenhada agora. No proximo run (o do clique)
    # ela vira a referencia: se a lista tiver mudado, o indice que o navegador
    # mandou aponta para outro horario e nos recusamos em vez de reservar
    # errado. Tem que ser lido ANTES de sobrescrever.
    slots_agora = [dt.isoformat() for dt in slots]
    slots_na_tela = st.session_state.get(_CHAVE_SLOTS_NA_TELA)
    lista_mudou = slots_na_tela is not None and slots_na_tela != slots_agora
    st.session_state[_CHAVE_SLOTS_NA_TELA] = slots_agora

    # 5) Confirmar
    st.divider()
    resumo = (f"**{servico.nome}** com **{prof.nome}** em "
              f"**{slot.strftime('%d/%m/%Y às %H:%M')}** - total "
              f"**{styles.moeda_br(calc.preco_final)}**")
    st.markdown(resumo)

    # A agenda mudou desde a tela que o cliente estava vendo (outra pessoa
    # pegou um horario). Nem desenhamos o botao de verdade: assim um clique
    # que ja estava a caminho nao tem onde pegar, e o cliente reconfere.
    # O `ocupado` evita entrar aqui no run que esta EXECUTANDO a reserva -
    # ali a lista mudou por culpa nossa, e sair agora travaria o botao.
    if lista_mudou and not acao_unica.ocupado(_ACAO_CONFIRMAR):
        st.warning("A agenda mudou enquanto você confirmava. "
                   "Confira o horário acima e toque em confirmar de novo.")
        st.button("Confirmar agendamento", type="primary",
                  use_container_width=True, disabled=True, key="confirmar_bloqueado")
        return

    if not acao_unica.botao("Confirmar agendamento", nome=_ACAO_CONFIRMAR,
                            rotulo_ocupado="Registrando seu agendamento...",
                            type="primary", use_container_width=True):
        return

    try:
        with st.spinner("Registrando seu agendamento..."):
            _id, canais = agendamento_fluxo.criar_e_notificar(
                cliente_id=usuario["id"], cabeleireiro_id=prof.id,
                servico_id=servico.id, inicio=slot,
            )
    except reservas.SlotIndisponivel:
        _liberar_trava()
        st.error("Ops, esse horario acabou de ser ocupado. Escolha outro.")
        return
    except reservas.HorarioBloqueado:
        _liberar_trava()
        st.error("Este cabeleireiro bloqueou a agenda nesse periodo. Escolha outro dia.")
        return
    except reservas.ServicoNaoOferecido:
        _liberar_trava()
        st.error("Este servico nao esta mais disponivel com este cabeleireiro.")
        return
    except Exception:  # noqa: BLE001 - nao deixar a trava presa por erro inesperado
        _liberar_trava()
        st.error("Nao conseguimos registrar agora. Tente novamente em instantes.")
        return

    # guarda os dados e troca para a tela de confirmacao (sem balao). A trava
    # SEGUE marcada de proposito: so o botao "Agendar outro horário" a libera.
    st.session_state[_CHAVE_CONFIRMADO] = {
        "servico": servico.nome, "prof": prof.nome,
        "inicio": slot, "preco": calc.preco_final, "canais": canais,
    }
    st.rerun()
