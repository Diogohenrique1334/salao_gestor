# ---------------------------------------------------------------------------
# ui/paginas/entrada.py - tela de entrada unica (Entrar / Criar conta).
#
# Substitui as duas paginas separadas do menu lateral. O objetivo e' que o
# cliente leigo veja o "Criar conta" com o MESMO destaque do "Entrar", sem ter
# de caca-lo no menu. Um alternador no topo escolhe qual formulario mostrar;
# o corpo de cada um vem de login.formulario_login / cadastro.formulario_cadastro.
# ---------------------------------------------------------------------------
from __future__ import annotations

import streamlit as st

from src.config.settings import get_settings
from src.ui.componentes import styles
from src.ui.paginas import cadastro, login

_ENTRAR = "Entrar"
_CRIAR = "Criar conta"
_CHAVE = "entrada_aba"


def render() -> None:
    styles.aplicar_estilo_base()
    styles.cabecalho_marca(get_settings().salao.nome, "Agendamentos")

    aba = st.segmented_control(
        "Acesso",
        [_ENTRAR, _CRIAR],
        default=st.session_state.get(_CHAVE, _ENTRAR),
        label_visibility="collapsed",
        key=_CHAVE,
    )

    if aba == _CRIAR:
        styles.titulo_secao("Criar sua conta")
        st.caption("É rápido: leva menos de um minuto e você já pode agendar.")
        cadastro.formulario_cadastro()
    else:
        styles.titulo_secao("Entrar")
        login.formulario_login()
        st.caption("Primeira vez aqui? Toque em **Criar conta** acima.")
