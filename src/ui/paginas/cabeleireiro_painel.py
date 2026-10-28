# ---------------------------------------------------------------------------
# ui/paginas/cabeleireiro_painel.py - painel do CABELEIREIRO logado.
#
# Mostra: KPIs do periodo (so dele), grafico de atendimentos por dia, a agenda
# do dia (horarios MARCADOS) e os horarios VAGOS do dia. Tudo restrito ao seu
# proprio perfil (cabeleireiro_id da sessao).
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from src.db.engine import sessao
from src.repositorios import cabeleireiros as repo_cab
from src.repositorios import nps as repo_nps
from src.repositorios import relatorios
from src.servicos import nps as srv_nps
from src.ui.componentes import (atendimento_ui, bloqueio_ui, graficos, guards,
                                  ocupacao_ui, styles)

_PERIODOS = {"7 dias": 7, "30 dias": 30, "90 dias": 90}
_KEY_OCUP = "cab_ocup"
_CHAVE_ABRIU_HOJE = "cab_painel_abriu_hoje"


def _abrir_hoje_na_primeira_visita() -> None:
    """Na primeira carga do painel na sessao, ja deixa a agenda de HOJE aberta.

    O barbeiro abre o app para ver quem vem hoje; antes caia na grade da
    semana e precisava de um toque a mais.

    A flag propria e' necessaria: se a regra fosse so "sem dia escolhido ->
    hoje", o botao 'Fechar agenda do dia' (que limpa a escolha) reabriria a
    agenda no run seguinte, e o botao nunca fecharia nada.
    """
    if st.session_state.get(_CHAVE_ABRIU_HOJE):
        return
    st.session_state[_CHAVE_ABRIU_HOJE] = True
    st.session_state.setdefault(f"{_KEY_OCUP}_sel", date.today())


def _secao_agenda_do_dia(cab_id: int, prof, dia) -> None:
    """Agenda marcada + horarios vagos do dia escolhido."""
    e_hoje = dia == date.today()
    styles.titulo_secao("Agenda de hoje" if e_hoje
                        else f"Agenda de {styles.formatar_data_br(dia)}")
    if e_hoje:
        st.caption(styles.formatar_data_br(dia))

    atendimento_ui.tabela_agenda_do_dia(cabeleireiro_fixo=prof, dia=dia, key_prefix="cab_ag")
    st.markdown("**Horarios vagos**")
    atendimento_ui.lista_blocos_livres(cab_id, dia)
    if st.button("Fechar agenda do dia", key="cab_fechar"):
        ocupacao_ui.limpar_selecao(_KEY_OCUP)
        st.rerun()


def render() -> None:
    styles.aplicar_estilo_base()
    usuario = guards.require_cabeleireiro()
    cab_id = usuario["cabeleireiro_id"]
    with sessao() as db:
        prof = repo_cab.buscar_por_id(db, cab_id)
    if prof is None:
        st.error("Perfil de cabeleireiro nao encontrado. Fale com o gestor.")
        return

    st.markdown(f"## 💈 Painel - {prof.nome}")

    # A AGENDA DO DIA VEM PRIMEIRO. Os KPIs sao consulta ocasional; o que o
    # barbeiro abre o app para ver e' quem chega hoje.
    _abrir_hoje_na_primeira_visita()
    dia_sel = st.session_state.get(f"{_KEY_OCUP}_sel")
    if dia_sel is not None:
        _secao_agenda_do_dia(cab_id, prof, dia_sel)
        st.divider()

    escolha = st.segmented_control("Periodo", list(_PERIODOS.keys()), default="30 dias")
    dias = _PERIODOS.get(escolha, 30)
    desde = datetime.now() - timedelta(days=dias)

    with sessao() as db:
        resumo = relatorios.resumo(db, desde, cabeleireiro_id=cab_id)
        por_dia = relatorios.por_dia(db, desde, cabeleireiro_id=cab_id)
        nps = srv_nps.calcular_nps(repo_nps.notas_no_periodo(db, desde, cabeleireiro_id=cab_id))

    styles.titulo_secao(f"Resumo - ultimos {dias} dias")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        styles.kpi_box("Atendimentos", str(resumo["total"]))
    with c2:
        styles.kpi_box("Receita", styles.moeda_br(resumo["receita"]))
    with c3:
        styles.kpi_box("Ticket medio", styles.moeda_br(resumo["ticket_medio"]))
    with c4:
        styles.kpi_box("No-show", f"{resumo['taxa_no_show']:.0f}%",
                       cor="#b3402f" if resumo["taxa_no_show"] >= 20 else None)
    with c5:
        valor_nps = str(nps["score"]) if nps["total"] else "-"
        styles.kpi_box("NPS", valor_nps,
                       cor="#b3402f" if nps["total"] and nps["score"] < 0 else None)

    if resumo.get("gratuitos"):
        st.caption(
            f"O ticket medio considera apenas os {resumo['pagos']} atendimentos pagos — "
            f"{resumo['gratuitos']} lancados a R$ 0 (plano/cortesia) ficam de fora da media."
        )

    if por_dia:
        styles.titulo_secao("Atendimentos por dia")
        df = pd.DataFrame(por_dia, columns=["dia", "qtd"])
        graficos.linha(df, "dia", "qtd", key="cab_por_dia")

    # A grade da semana desce para ca: serve para NAVEGAR ate outro dia, e o
    # dia escolhido abre la em cima (o grade_ocupacao da rerun ao escolher).
    styles.titulo_secao("Proximos dias")
    dias_grade, inicio_grade = ocupacao_ui.controles_periodo(_KEY_OCUP, default_dias=7)
    ocupacao_ui.grade_ocupacao(
        cabeleireiro_id=cab_id, dias=dias_grade, inicio=inicio_grade, key_prefix=_KEY_OCUP
    )

    styles.titulo_secao("Bloquear minha agenda")
    st.caption("Bloqueie dias de ferias/folga: eles somem dos horarios oferecidos aos clientes.")
    bloqueio_ui.gerenciar_bloqueios(cab_id, key_prefix="cab_blq")
