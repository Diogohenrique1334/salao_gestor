# ---------------------------------------------------------------------------
# ui/paginas/agendar.py — fluxo de agendamento do cliente.
#
# Passos: escolher cabeleireiro -> servico (mostra preco JA com desconto) ->
# dia -> slot livre -> confirmar. A criacao usa servicos.reservas (regra +
# trava de conflito) e servicos.agenda (slots livres).
# ---------------------------------------------------------------------------
from __future__ import annotations

import streamlit as st

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


def _liberar_trava() -> None:
    acao_unica.liberar(_ACAO_CONFIRMAR)


def _aviso_telefone(usuario: dict) -> None:
    if not usuario.get("telefone"):
        st.caption("ℹ️ Voce ainda nao cadastrou WhatsApp, a confirmacao por WhatsApp "
                   "depende disso (atualize em 'Meus agendamentos' futuramente).")


def _tela_confirmacao(dados: dict) -> None:
    """Tela dedicada de sucesso — substitui o balao/toast por uma mudanca de tela."""
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
        _liberar_trava()
        st.session_state.pop(_CHAVE_SLOTS_NA_TELA, None)
        st.rerun()


def render() -> None:
    styles.aplicar_estilo_base()
    usuario = guards.require_login()

    # se acabou de confirmar, mostra a tela de sucesso e PARA aqui
    if _CHAVE_CONFIRMADO in st.session_state:
        _tela_confirmacao(st.session_state[_CHAVE_CONFIRMADO])
        return

    st.markdown("## 🗓️ Agendar")
    _aviso_telefone(usuario)

    # 1) Cabeleireiro
    with sessao() as db:
        profs = repo_cab.listar(db)  # ativos
    if not profs:
        st.warning("Nenhum cabeleireiro disponivel no momento.")
        return
    styles.titulo_secao("1. Escolha o cabeleireiro")
    prof = st.selectbox("Cabeleireiro", profs, format_func=lambda p: p.nome)

    # 2) Servico oferecido por ele (com preco/desconto)
    with sessao() as db:
        vinculos = repo_serv.listar_vinculos_do_cabeleireiro(db, prof.id, apenas_ativos=True)
        servicos = []
        for v in vinculos:
            s = repo_serv.buscar_por_id(db, v.servico_id)
            if s and s.ativo:
                calc = precificacao.calcular_preco(s.preco_base, v.desconto_tipo, v.desconto_valor)
                servicos.append((s, calc))
    if not servicos:
        st.warning("Este cabeleireiro ainda nao tem servicos configurados.")
        return

    styles.titulo_secao("2. Escolha o servico")

    # RADIO, nao selectbox: sao 11 servicos e cinco comecam com "Corte"
    # (Corte, Corte e alisante, Corte e barba, Corte e luzes, Corte e
    # sombrancelha). Num menu fechado, com a fonte pequena do Streamlit, viram
    # cinco linhas quase identicas no celular - e o cliente marcava o servico
    # errado. Em lista aberta, cada um ocupa a propria linha, com o nome em
    # destaque e preco/duracao na legenda abaixo (ver o CSS stRadio em styles).
    def _legenda(item):
        s, calc = item
        preco = styles.moeda_br(calc.preco_final)
        if calc.desconto > 0:
            return f"{preco} (de {styles.moeda_br(calc.preco_base)}) - {s.duracao_min} min"
        return f"{preco} - {s.duracao_min} min"

    indice = st.radio(
        "Servico",
        options=range(len(servicos)),
        format_func=lambda i: servicos[i][0].nome,
        captions=[_legenda(item) for item in servicos],
        label_visibility="collapsed",
    )
    servico, calc = servicos[indice]
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
        st.info("Este cabeleireiro nao tem horarios livres nos proximos dias.")
        return
    dia = st.selectbox("Dia", dias, format_func=styles.formatar_data_br)

    # 4) Slots livres
    styles.titulo_secao("4. Escolha o horario")
    with sessao() as db:
        slots = agenda.horarios_disponiveis(db, cabeleireiro_id=prof.id, dia=dia, servico_id=servico.id)
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
              f"**{slot.strftime('%d/%m/%Y às %H:%M')}** - total **{styles.moeda_br(calc.preco_final)}**")
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
