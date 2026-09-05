# ---------------------------------------------------------------------------
# ui/paginas/cabeleireiro_painel.py - painel do CABELEIREIRO logado.
#
# Mostra: KPIs do periodo (so dele), grafico de atendimentos por dia, a agenda
# do dia (horarios MARCADOS) e os horarios VAGOS do dia. Tudo restrito ao seu
# proprio perfil (cabeleireiro_id da sessao).
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import datetime, timedelta

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

    styles.titulo_secao("Minha agenda - proximos dias")
    dias_grade = st.segmented_control(
        "Ver", [7, 14, 30], default=7, format_func=lambda n: f"{n} dias", key="cab_ocup_per"
    ) or 7
    dia_sel = ocupacao_ui.grade_ocupacao(
        cabeleireiro_id=cab_id, dias=int(dias_grade), key_prefix="cab_ocup"
    )

    if dia_sel is not None:
        st.divider()
        styles.titulo_secao(f"Agenda de {styles.formatar_data_br(dia_sel)}")
        atendimento_ui.tabela_agenda_do_dia(
            cabeleireiro_fixo=prof, dia=dia_sel, key_prefix="cab_ag"
        )
        st.markdown("**Horarios vagos**")
        atendimento_ui.lista_blocos_livres(cab_id, dia_sel)
        if st.button("Fechar agenda do dia", key="cab_fechar"):
            ocupacao_ui.limpar_selecao("cab_ocup")
            st.rerun()

    styles.titulo_secao("Bloquear minha agenda")
    st.caption("Bloqueie dias de ferias/folga: eles somem dos horarios oferecidos aos clientes.")
    bloqueio_ui.gerenciar_bloqueios(cab_id, key_prefix="cab_blq")
