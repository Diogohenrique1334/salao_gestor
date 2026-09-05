# ---------------------------------------------------------------------------
# ui/paginas/gestor_ocupacao.py - visao panoramica de ocupacao (gestor).
#
# Grade dos proximos dias (Nº de agendamentos + barra de preenchimento) vinda do
# componente compartilhado ui/componentes/ocupacao_ui.py. Ao clicar num dia,
# abre a agenda daquele dia com quem esta marcado em cada horario.
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
    st.markdown("## 📅 Ocupacao dos proximos dias")

    with sessao() as db:
        profs = repo_cab.listar(db)
    if not profs:
        st.info("Cadastre um cabeleireiro primeiro (pagina **Cabeleireiros**).")
        return

    opcoes = {"Todos os cabeleireiros": None}
    opcoes.update({p.nome: p.id for p in profs})
    por_id = {p.id: p for p in profs}

    c1, c2 = st.columns([2, 2])
    escolha = c1.selectbox("Cabeleireiro", list(opcoes.keys()), key=f"{_KEY}_cab")
    dias = c2.segmented_control("Periodo", [7, 14, 30], default=14,
                                format_func=lambda n: f"{n} dias", key=f"{_KEY}_per") or 14
    cab_id = opcoes[escolha]

    dia_sel = ocupacao_ui.grade_ocupacao(cabeleireiro_id=cab_id, dias=int(dias), key_prefix=_KEY)

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
