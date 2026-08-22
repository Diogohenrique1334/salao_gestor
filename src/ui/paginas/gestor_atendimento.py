# ---------------------------------------------------------------------------
# ui/paginas/gestor_atendimento.py - atendimento avulso (walk-in) pelo gestor.
#
# O gestor agenda para qualquer cabeleireiro (selecionavel) e ve a agenda do
# dia. A logica vive no componente compartilhado ui.componentes.atendimento_ui
# (reaproveitado pelo painel do cabeleireiro).
# ---------------------------------------------------------------------------
from __future__ import annotations

import streamlit as st

from src.ui.componentes import atendimento_ui, guards, styles


def render() -> None:
    styles.aplicar_estilo_base()
    guards.require_gestor()
    st.markdown("## 🧍 Atendimento avulso")

    atendimento_ui.formulario_atendimento(key_prefix="gestor_at")
    st.divider()
    styles.titulo_secao("Agenda do dia")
    atendimento_ui.tabela_agenda_do_dia(key_prefix="gestor_ag")
