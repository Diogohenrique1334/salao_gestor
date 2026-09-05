# ---------------------------------------------------------------------------
# ui/paginas/gestor_dashboard.py — visao do gestor: KPIs + graficos.
#
# Le metricas agregadas (repositorios.relatorios) e renderiza KPIs em boxes
# estilizados + graficos ECharts (ui.componentes.graficos, self-contained).
# Filtro de periodo no topo (segmented_control), conforme padrao do Diogo.
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from src.db.engine import sessao
from src.repositorios import nps as repo_nps
from src.repositorios import relatorios
from src.servicos import nps as srv_nps
from src.ui.componentes import graficos, guards, styles

# rotulos/cores de status vem de styles (fonte unica, compartilhada com badges)
_PERIODOS = {"7 dias": 7, "30 dias": 30, "90 dias": 90}


def _kpis(resumo: dict) -> None:
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        styles.kpi_box("Agendamentos", str(resumo["total"]))
    with c2:
        styles.kpi_box("Receita", styles.moeda_br(resumo["receita"]))
    with c3:
        styles.kpi_box("Ticket medio", styles.moeda_br(resumo["ticket_medio"]))
    with c4:
        styles.kpi_box("Cancelamento", f"{resumo['taxa_cancelamento']:.0f}%",
                       cor="#b3402f" if resumo["taxa_cancelamento"] >= 20 else None)
    with c5:
        styles.kpi_box("No-show", f"{resumo['taxa_no_show']:.0f}%",
                       cor="#b3402f" if resumo["taxa_no_show"] >= 20 else None)


def _secao_nps(desde) -> None:
    with sessao() as db:
        notas = repo_nps.notas_no_periodo(db, desde)
    nps = srv_nps.calcular_nps(notas)
    styles.titulo_secao("Satisfacao (NPS)")
    if nps["total"] == 0:
        st.caption("Sem avaliacoes no periodo.")
        return
    c1, c2, c3 = st.columns(3)
    with c1:
        styles.kpi_box("Score NPS", str(nps["score"]),
                       cor="#b3402f" if nps["score"] < 0 else None)
    with c2:
        styles.kpi_box("Respostas", str(nps["total"]))
    with c3:
        styles.kpi_box("Promotores", f"{nps['pct_promotores']:.0f}%")


def render() -> None:
    styles.aplicar_estilo_base()
    guards.require_gestor()
    st.markdown("## 📊 Dashboard")

    escolha = st.segmented_control("Periodo", list(_PERIODOS.keys()), default="30 dias")
    dias = _PERIODOS.get(escolha, 30)
    desde = datetime.now() - timedelta(days=dias)

    with sessao() as db:
        resumo = relatorios.resumo(db, desde)
        por_cab = relatorios.por_cabeleireiro(db, desde)
        por_status = relatorios.por_status(db, desde)
        por_dia = relatorios.por_dia(db, desde)

    styles.titulo_secao(f"Resumo ultimos {dias} dias")
    _kpis(resumo)
    if resumo.get("gratuitos"):
        st.caption(
            f"O ticket medio considera apenas os {resumo['pagos']} atendimentos pagos — "
            f"{resumo['gratuitos']} lancados a R$ 0 (plano/cortesia) ficam de fora da media."
        )

    _secao_nps(desde)

    if resumo["total"] == 0:
        st.info("Sem agendamentos no periodo selecionado.")
        return

    col_esq, col_dir = st.columns(2)

    with col_esq:
        styles.titulo_secao("Agendamentos por cabeleireiro")
        if por_cab:
            df = pd.DataFrame(por_cab, columns=["cabeleireiro", "qtd"])
            graficos.barras(df, "cabeleireiro", "qtd", key="dash_cab")
        else:
            st.caption("Sem dados.")

    with col_dir:
        styles.titulo_secao("Distribuicao por status")
        if por_status:
            chaves = [s for s, _ in por_status]
            labels = [styles.rotulo_status(s) for s in chaves]
            valores = [q for _, q in por_status]
            # cores vindas da MESMA fonte dos badges -> donut e listas combinam
            graficos.rosca(labels, valores, key="dash_status",
                           cores=graficos.paleta_status(chaves))
        else:
            st.caption("Sem dados.")

    styles.titulo_secao("Agendamentos por dia")
    if por_dia:
        df_dia = pd.DataFrame(por_dia, columns=["dia", "qtd"])
        graficos.linha(df_dia, "dia", "qtd", key="dash_dia")
    else:
        st.caption("Sem dados.")
