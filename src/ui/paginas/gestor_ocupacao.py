# ---------------------------------------------------------------------------
# ui/paginas/gestor_ocupacao.py - visao panoramica de ocupacao (gestor).
#
# Grade de dias (Nº de agendamentos + barra de preenchimento) vinda do
# componente compartilhado ui/componentes/ocupacao_ui.py. Ao clicar num dia,
# abre a agenda daquele dia com quem esta marcado em cada horario.
#
# A janela olha para FRENTE ou para TRAS (retrospecto: quem esteve marcado),
# pelos controles de ocupacao_ui.controles_periodo().
# ---------------------------------------------------------------------------
from __future__ import annotations

import streamlit as st

from src.db.engine import sessao
from src.repositorios import cabeleireiros as repo_cab
from src.ui.componentes import atendimento_ui, guards, ocupacao_ui, styles

_KEY = "gocup"


def render() -> None:
    styles.aplicar_estilo_base()
    guards.require_gestor()
    st.markdown("## 📅 Ocupacao da agenda")

    with sessao() as db:
        profs = repo_cab.listar(db)
    if not profs:
        st.info("Cadastre um cabeleireiro primeiro (pagina **Cabeleireiros**).")
        return

    opcoes = {"Todos os cabeleireiros": None}
    opcoes.update({p.nome: p.id for p in profs})
    por_id = {p.id: p for p in profs}

    escolha = st.selectbox("Cabeleireiro", list(opcoes.keys()), key=f"{_KEY}_cab")
    cab_id = opcoes[escolha]

    dias, inicio = ocupacao_ui.controles_periodo(_KEY, default_dias=14)
    dia_sel = ocupacao_ui.grade_ocupacao(
        cabeleireiro_id=cab_id, dias=dias, inicio=inicio, key_prefix=_KEY
    )

    if dia_sel is None:
        return

    st.divider()
    styles.titulo_secao(f"Agenda de {styles.formatar_data_br(dia_sel)}")
    # com um cabeleireiro escolhido, trava nele; em "Todos", a tabela oferece o seletor
    atendimento_ui.tabela_agenda_do_dia(
        cabeleireiro_fixo=por_id.get(cab_id), dia=dia_sel, key_prefix=f"{_KEY}_ag"
    )
    if st.button("Fechar agenda do dia", key=f"{_KEY}_fechar"):
        ocupacao_ui.limpar_selecao(_KEY)
        st.rerun()
