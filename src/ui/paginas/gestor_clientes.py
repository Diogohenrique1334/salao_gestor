# ---------------------------------------------------------------------------
# ui/paginas/gestor_clientes.py — gestao de clientes pelo gestor.
#
# Lista os clientes e permite REDEFINIR A SENHA de cada um (reset assistido,
# sem depender de e-mail). Usa servicos.auth.redefinir_senha.
# ---------------------------------------------------------------------------
from __future__ import annotations

import streamlit as st

from src.db.engine import sessao
from src.repositorios import clientes as repo_cli
from src.servicos import auth
from src.ui.componentes import guards, styles

_MIN_SENHA = 6


def render() -> None:
    styles.aplicar_estilo_base()
    guards.require_gestor()
    st.markdown("## 👥 Clientes")

    styles.titulo_secao("Clientes cadastrados")
    with sessao() as db:
        clientes = repo_cli.listar(db)
    if not clientes:
        st.caption("Nenhum cliente cadastrado ainda.")
        return

    for c in clientes:
        with st.expander(f"{c.nome} — {c.email}"):
            st.caption(f"WhatsApp: {c.telefone or '—'}")
            with st.form(f"reset_{c.id}"):
                st.markdown("**Redefinir senha**")
                nova = st.text_input("Nova senha", type="password", key=f"ns_{c.id}")
                nova2 = st.text_input("Confirmar", type="password", key=f"ns2_{c.id}")
                if st.form_submit_button("Definir nova senha", type="primary"):
                    if len(nova) < _MIN_SENHA:
                        st.error(f"A senha deve ter ao menos {_MIN_SENHA} caracteres.")
                    elif nova != nova2:
                        st.error("As senhas nao conferem.")
                    else:
                        with sessao() as db:
                            auth.redefinir_senha(db, c.id, nova)
                        st.success(f"Senha de {c.nome} redefinida.")
