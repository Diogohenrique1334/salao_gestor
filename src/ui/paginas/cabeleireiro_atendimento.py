# ---------------------------------------------------------------------------
# ui/paginas/cabeleireiro_atendimento.py — o cabeleireiro registra um
# atendimento na PROPRIA agenda (avulso ou cliente cadastrado).
#
# Reaproveita o componente compartilhado, travando o cabeleireiro no perfil
# logado (cabeleireiro_id da sessao).
# ---------------------------------------------------------------------------
from __future__ import annotations

import streamlit as st

from src.db.engine import sessao
from src.repositorios import cabeleireiros as repo_cab
from src.ui.componentes import atendimento_ui, guards, styles


def render() -> None:
    styles.aplicar_estilo_base()
    usuario = guards.require_cabeleireiro()
    with sessao() as db:
        prof = repo_cab.buscar_por_id(db, usuario["cabeleireiro_id"])
    if prof is None:
        st.error("Perfil de cabeleireiro nao encontrado. Fale com o gestor.")
        return

    st.markdown("## 🧍 Registrar atendimento")
    atendimento_ui.formulario_atendimento(cabeleireiro_fixo=prof, key_prefix="cab_at")
