# ---------------------------------------------------------------------------
# ui/componentes/bloqueio_ui.py - bloco de UI de bloqueio de agenda (ferias/folga).
#
# Compartilhado entre o painel do CABELEIREIRO (bloqueia a propria agenda) e a
# gestao de cabeleireiros do GESTOR (bloqueia a de um profissional selecionado).
# So renderiza e delega; a regra vive em servicos/bloqueios.
#
#   gerenciar_bloqueios(cabeleireiro_id, key_prefix) -> form + lista removivel
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from src.db.engine import sessao
from src.servicos import bloqueios as srv_bloqueios
from src.ui.componentes import styles


def _formatar_periodo(b) -> str:
    """Bloqueio (inicio/fim com fim exclusivo) -> 'dd/mm/aaaa a dd/mm/aaaa'."""
    fim_inclusivo = (b.fim - timedelta(days=1)).date() if b.fim else b.inicio.date()
    ini = b.inicio.strftime("%d/%m/%Y")
    if fim_inclusivo <= b.inicio.date():
        return ini
    return f"{ini} a {fim_inclusivo.strftime('%d/%m/%Y')}"


def gerenciar_bloqueios(cabeleireiro_id: int, *, key_prefix: str = "blq") -> None:
    """Form para criar bloqueio (dia(s) inteiro(s)) + lista dos futuros, removivel."""
    with st.form(f"{key_prefix}_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        data_inicio = c1.date_input("Inicio", value=date.today(), min_value=date.today(),
                                    format="DD/MM/YYYY", key=f"{key_prefix}_ini")
        data_fim = c2.date_input("Fim", value=date.today(), min_value=date.today(),
                                format="DD/MM/YYYY", key=f"{key_prefix}_fim")
        motivo = st.text_input("Motivo (opcional)", placeholder="Ferias, folga...",
                               key=f"{key_prefix}_mot")
        if st.form_submit_button("Bloquear periodo", type="primary"):
            if data_fim < data_inicio:
                st.error("O fim deve ser igual ou depois do inicio.")
            else:
                with sessao() as db:
                    srv_bloqueios.criar_bloqueio(
                        db, cabeleireiro_id=cabeleireiro_id,
                        data_inicio=data_inicio, data_fim=data_fim, motivo=(motivo or None),
                    )
                st.success("Periodo bloqueado.")
                st.rerun()

    with sessao() as db:
        futuros = srv_bloqueios.listar(db, cabeleireiro_id, apenas_futuros=True)
    if not futuros:
        st.caption("Nenhum bloqueio ativo ou futuro.")
        return
    for b in futuros:
        col1, col2 = st.columns([4, 1])
        rotulo = _formatar_periodo(b)
        motivo = f" · {b.motivo}" if b.motivo else ""
        col1.markdown(f"{styles.badge('Bloqueado', '#5a1f1f')} &nbsp; {rotulo}{motivo}",
                      unsafe_allow_html=True)
        if col2.button("Remover", key=f"{key_prefix}_rm_{b.id}"):
            with sessao() as db:
                srv_bloqueios.remover_bloqueio(db, b.id)
            st.rerun()
