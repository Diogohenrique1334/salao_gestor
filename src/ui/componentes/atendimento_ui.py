# ---------------------------------------------------------------------------
# ui/componentes/atendimento_ui.py - blocos de UI reutilizaveis de atendimento.
#
# Compartilhados entre o painel do GESTOR (cabeleireiro selecionavel) e o painel
# do CABELEIREIRO (cabeleireiro fixo = ele mesmo). Mantem a regra na camada de
# servicos; aqui so renderiza e delega.
#
#   formulario_atendimento(cabeleireiro_fixo=None, ...)  -> registra atendimento
#   tabela_agenda_do_dia(cabeleireiro_fixo=None, ...)    -> marcados no dia
#   lista_blocos_livres(cabeleireiro_id, dia)            -> faixas vagas no dia
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Optional, Tuple

import streamlit as st

from src.constantes import STATUS_ATIVOS
from src.db.engine import sessao
from src.notificacoes import eventos
from src.repositorios import agendamentos as repo_ag
from src.repositorios import cabeleireiros as repo_cab
from src.repositorios import clientes as repo_cli
from src.repositorios import servicos as repo_serv
from src.servicos import agenda, agendamento_fluxo, precificacao, reservas
from src.ui.componentes import styles


def formulario_atendimento(*, cabeleireiro_fixo=None, key_prefix: str = "at") -> None:
    """Form de registro de atendimento. Se `cabeleireiro_fixo`, trava no perfil."""
    if cabeleireiro_fixo is not None:
        prof = cabeleireiro_fixo
        st.caption(f"Cabeleireiro: **{prof.nome}**")
    else:
        with sessao() as db:
            profs = repo_cab.listar(db)
        if not profs:
            st.warning("Cadastre um cabeleireiro primeiro.")
            return
        prof = st.selectbox("Cabeleireiro", profs, format_func=lambda p: p.nome, key=f"{key_prefix}_prof")

    # servico ofertado pelo cabeleireiro (preco c/ desconto)
    with sessao() as db:
        vinculos = repo_serv.listar_vinculos_do_cabeleireiro(db, prof.id, apenas_ativos=True)
        servicos = []
        for v in vinculos:
            s = repo_serv.buscar_por_id(db, v.servico_id)
            if s and s.ativo:
                calc = precificacao.calcular_preco(s.preco_base, v.desconto_tipo, v.desconto_valor)
                servicos.append((s, calc))
    if not servicos:
        st.warning("Este cabeleireiro nao tem servicos configurados.")
        return
    servico, _calc = st.selectbox(
        "Servico", servicos,
        format_func=lambda it: f"{it[0].nome} - {styles.moeda_br(it[1].preco_final)} · {it[0].duracao_min} min",
        key=f"{key_prefix}_serv",
    )

    # identidade: avulso ou cliente cadastrado
    tipo = st.radio("Quem sera atendido?", ["Pessoa avulsa", "Cliente cadastrado"],
                    horizontal=True, key=f"{key_prefix}_tipo")
    cliente_id: Optional[int] = None
    nome_avulso: Optional[str] = None
    telefone_avulso: Optional[str] = None
    if tipo == "Pessoa avulsa":
        c1, c2 = st.columns(2)
        nome_avulso = c1.text_input("Nome", key=f"{key_prefix}_nome")
        telefone_avulso = c2.text_input("WhatsApp (opcional)", key=f"{key_prefix}_tel")
    else:
        with sessao() as db:
            clientes = repo_cli.listar(db)
        if not clientes:
            st.info("Nenhum cliente cadastrado; use 'Pessoa avulsa'.")
            return
        cli = st.selectbox("Cliente", clientes, format_func=lambda c: f"{c.nome} ({c.email})",
                           key=f"{key_prefix}_cli")
        cliente_id = cli.id

    # dia + horario (somente dias com vaga)
    with sessao() as db:
        dias = agenda.proximos_dias_disponiveis(db, cabeleireiro_id=prof.id, servico_id=servico.id, max_dias=30)
    if not dias:
        st.info("Sem dias com horario livre para este cabeleireiro.")
        return
    dia = st.selectbox("Dia", dias, format_func=styles.formatar_data_br, key=f"{key_prefix}_dia")
    with sessao() as db:
        slots = agenda.horarios_disponiveis(db, cabeleireiro_id=prof.id, dia=dia, servico_id=servico.id)
    if not slots:
        st.info("Sem horarios livres nesse dia.")
        return
    slot = st.selectbox("Horario", slots, format_func=lambda dt: dt.strftime("%H:%M"), key=f"{key_prefix}_slot")

    if st.button("Registrar atendimento", type="primary", use_container_width=True, key=f"{key_prefix}_btn"):
        if tipo == "Pessoa avulsa" and not (nome_avulso and nome_avulso.strip()):
            st.error("Informe o nome da pessoa.")
            return

        # Idempotencia por CONTEUDO: esta tela nao troca de pagina no sucesso,
        # entao um clique repetido reenviaria exatamente o mesmo atendimento.
        # Guardar a assinatura do ultimo registro barra a repeticao sem travar
        # o balcao, que precisa lancar varios atendimentos em sequencia.
        assinatura = (prof.id, servico.id, slot.isoformat(), cliente_id, nome_avulso)
        chave_ultimo = f"{key_prefix}_ultimo"
        if st.session_state.get(chave_ultimo) == assinatura:
            st.info("Esse atendimento ja foi registrado. Mude algum campo para lancar outro.")
            return

        try:
            with st.spinner("Registrando..."):
                ag_id, canais = agendamento_fluxo.criar_e_notificar(
                    cabeleireiro_id=prof.id, servico_id=servico.id, inicio=slot,
                    cliente_id=cliente_id, nome_avulso=nome_avulso, telefone_avulso=telefone_avulso,
                )
        except reservas.SlotIndisponivel:
            st.error("Esse horario acabou de ser ocupado. Escolha outro.")
            return
        except reservas.HorarioBloqueado:
            st.error("A agenda deste cabeleireiro esta bloqueada nesse periodo.")
            return
        except reservas.ServicoNaoOferecido:
            st.error("Servico indisponivel para este cabeleireiro.")
            return

        st.session_state[chave_ultimo] = assinatura
        via = ", ".join(canais) if canais else "console"
        st.success(f"Atendimento registrado (#{ag_id}) - confirmacao via {via}.")


def _baixa_presenca(agendamento_id: int, *, compareceu: bool, restrito_a: Optional[int]) -> None:
    """Da baixa (compareceu/faltou) num agendamento e atualiza a tela."""
    try:
        with sessao() as db:
            reservas.registrar_presenca(
                db, agendamento_id=agendamento_id, compareceu=compareceu, cabeleireiro_id=restrito_a
            )
        st.toast("Presenca confirmada." if compareceu else "Falta registrada.")
        st.rerun()
    except reservas.NaoAutorizado:
        st.error("Voce nao pode dar baixa neste agendamento.")
    except reservas.PresencaInvalida:
        st.warning("Este agendamento ja foi finalizado.")


def _cancelar_pelo_salao(agendamento_id: int, *, restrito_a: Optional[int]) -> None:
    """Cancela um agendamento pelo lado do salao e avisa o cliente.

    `restrito_a` None = gestor (irrestrito); com id = o proprio cabeleireiro.
    """
    try:
        with sessao() as db:
            cancelado = reservas.cancelar_reserva(
                db,
                agendamento_id=agendamento_id,
                cabeleireiro_id=restrito_a,
                por_gestor=(restrito_a is None),
            )
            eventos.enviar_cancelamento(db, cancelado)
        st.toast("Agendamento cancelado. Cliente avisado.")
        st.rerun()
    except reservas.NaoAutorizado:
        st.error("Voce nao pode cancelar este agendamento.")
    except reservas.CancelamentoInvalido:
        st.warning("Este agendamento ja foi finalizado.")


def _card_agenda(a, *, quem: str, servico_nome: str, pode_dar_baixa: bool,
                 restrito_a: Optional[int], key_prefix: str,
                 profissional: Optional[str] = None) -> None:
    """Renderiza um atendimento do dia com badge e, se aplicavel, as acoes.

    `profissional` so e' preenchido quando a lista mistura varios profissionais
    (visao "Todos"); com um so, repetir o nome em toda linha seria ruido.
    """
    st.markdown('<div class="bloco-card">', unsafe_allow_html=True)
    com_quem = f" · ✂️ {profissional}" if profissional else ""
    st.markdown(
        f"🕑 **{a.inicio.strftime('%H:%M')}–{a.fim.strftime('%H:%M')}** · "
        f"**{quem}** · {servico_nome}{com_quem} · 💰 {styles.moeda_br(a.preco_aplicado)}  "
        f"{styles.badge_status(a.status)}",
        unsafe_allow_html=True,
    )
    if a.status in STATUS_ATIVOS:
        if pode_dar_baixa:
            c1, c2, _ = st.columns([1, 1, 4])
            if c1.button("Compareceu", key=f"{key_prefix}_pres_{a.id}", type="primary"):
                _baixa_presenca(a.id, compareceu=True, restrito_a=restrito_a)
            if c2.button("Faltou", key=f"{key_prefix}_falta_{a.id}"):
                _baixa_presenca(a.id, compareceu=False, restrito_a=restrito_a)

        # Cancelar vale para QUALQUER dia (o caso de uso e' o profissional que
        # faltou e precisa limpar a agenda de amanha). Fica atras de um passo de
        # confirmacao porque dispara e-mail ao cliente - clique errado nao volta.
        with st.expander("Cancelar atendimento"):
            st.caption("O cliente sera avisado por e-mail do cancelamento.")
            if st.button("Confirmar cancelamento", key=f"{key_prefix}_canc_{a.id}"):
                _cancelar_pelo_salao(a.id, restrito_a=restrito_a)
    st.markdown("</div>", unsafe_allow_html=True)


def tabela_agenda_do_dia(
    *, cabeleireiro_fixo=None, dia: Optional[date] = None, key_prefix: str = "ag"
) -> Optional[Tuple[object, date]]:
    """Agenda MARCADA de um dia, com baixa de presenca (compareceu/faltou).

    Gestor (cabeleireiro selecionavel) pode baixar qualquer; cabeleireiro fixo so
    os proprios. Botoes so aparecem para agendamentos ATIVOS de dias ja chegados.

    `dia` vindo de fora (ex.: clique na grade de ocupacao) suprime o seletor de
    data interno; sem ele, a funcao desenha o proprio `date_input`.
    """
    dia_externo = dia is not None
    if cabeleireiro_fixo is not None:
        prof = cabeleireiro_fixo
        if not dia_externo:
            dia = st.date_input("Dia", value=date.today(), key=f"{key_prefix}_dia")
    else:
        with sessao() as db:
            profs = repo_cab.listar(db)
        if not profs:
            return None
        if dia_externo:
            # a grade de ocupacao pode estar somando TODOS; o detalhe precisa
            # oferecer o mesmo, senao o dia diz "6 agendamentos" e a lista
            # aparece vazia por estar filtrada num profissional sem atendimento
            prof = st.selectbox(
                "Cabeleireiro", [None] + list(profs),
                format_func=lambda p: "Todos os cabeleireiros" if p is None else p.nome,
                key=f"{key_prefix}_prof",
            )
        else:
            c1, c2 = st.columns(2)
            prof = c1.selectbox("Cabeleireiro", profs, format_func=lambda p: p.nome,
                                key=f"{key_prefix}_prof")
            dia = c2.date_input("Dia", value=date.today(), key=f"{key_prefix}_dia")

    restrito_a = prof.id if cabeleireiro_fixo is not None else None
    pode_dar_baixa = dia <= date.today()  # nao da baixa em agendamento futuro

    # prof None = "Todos": agrega os profissionais e identifica cada linha
    alvos = [prof] if prof is not None else list(profs)
    varios = prof is None

    dia_ini = datetime.combine(dia, time.min)
    dia_fim = dia_ini + timedelta(days=1)
    with sessao() as db:
        cards = []
        for alvo in alvos:
            for a in repo_ag.listar_por_cabeleireiro_no_dia(
                db, alvo.id, dia_ini, dia_fim, apenas_ativos=False
            ):
                if a.cliente_id is not None:
                    cli = repo_cli.buscar_por_id(db, a.cliente_id)
                    quem = cli.nome if cli else "cliente"
                else:
                    quem = f"{a.nome_avulso or 'avulso'} (avulso)"
                serv = repo_serv.buscar_por_id(db, a.servico_id)
                cards.append((a, quem, serv.nome if serv else "-", alvo.nome))
    cards.sort(key=lambda t: t[0].inicio)  # ordem cronologica entre profissionais

    if not cards:
        st.caption("Nenhum atendimento marcado nesse dia.")
        return prof, dia
    for a, quem, servico_nome, nome_prof in cards:
        _card_agenda(a, quem=quem, servico_nome=servico_nome, pode_dar_baixa=pode_dar_baixa,
                     restrito_a=restrito_a, key_prefix=key_prefix,
                     profissional=nome_prof if varios else None)
    return prof, dia


def lista_blocos_livres(cabeleireiro_id: int, dia: date) -> None:
    """Mostra as faixas de horario VAGAS no dia (independente de servico)."""
    with sessao() as db:
        blocos = agenda.blocos_livres(db, cabeleireiro_id=cabeleireiro_id, dia=dia)
    if not blocos:
        st.caption("Sem horarios vagos nesse dia.")
        return
    texto = " · ".join(f"{ini.strftime('%H:%M')}–{fim.strftime('%H:%M')}" for ini, fim in blocos)
    st.markdown(styles.badge("Vago", "#1d4d12") + f" &nbsp; {texto}", unsafe_allow_html=True)
