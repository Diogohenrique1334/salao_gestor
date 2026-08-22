# ---------------------------------------------------------------------------
# ui/paginas/cadastro.py - cadastro de novo cliente.
#
# Coleta nome, e-mail, telefone (opcional, usado p/ WhatsApp) e senha; valida
# e cria o usuario via servicos.auth. Em sucesso, ja faz login automatico.
# ---------------------------------------------------------------------------
from __future__ import annotations

import re
from datetime import date

import streamlit as st

from src.config.settings import get_settings
from src.db.engine import sessao
from src.servicos import auth
from src.ui.componentes import guards, styles

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_SENHA = 6


def render() -> None:
    styles.aplicar_estilo_base()
    styles.cabecalho_marca(get_settings().salao.nome, "Criar conta")
    styles.titulo_secao("Seus dados")

    with st.form("form_cadastro"):
        nome = st.text_input("Nome completo")
        email = st.text_input("E-mail")
        telefone = st.text_input("WhatsApp (com DDD)", placeholder="+55 11 99999-9999",
                                 help="Opcional agora; necessario p/ confirmacao via WhatsApp.")
        nascimento = st.date_input(
            "Data de nascimento", value=None,
            min_value=date(1900, 1, 1), max_value=date.today(), format="DD/MM/YYYY",
        )
        col1, col2 = st.columns(2)
        senha = col1.text_input("Senha", type="password")
        senha2 = col2.text_input("Confirmar senha", type="password")
        enviar = st.form_submit_button("Cadastrar", type="primary", use_container_width=True)

    if not enviar:
        st.caption("Ja tem conta? Use a pagina **Login** no menu lateral.")
        return

    # Validacoes
    if not nome.strip():
        st.error("Informe seu nome.")
        return
    if not _EMAIL_RE.match(email.strip()):
        st.error("E-mail invalido.")
        return
    if nascimento is None:
        st.error("Informe sua data de nascimento.")
        return
    if len(senha) < _MIN_SENHA:
        st.error(f"A senha deve ter ao menos {_MIN_SENHA} caracteres.")
        return
    if senha != senha2:
        st.error("As senhas nao conferem.")
        return

    try:
        with sessao() as db:
            cliente = auth.registrar_cliente(
                db, nome=nome, email=email, senha=senha, telefone=(telefone or None),
                data_nascimento=nascimento,
            )
        guards.login(cliente, lembrar=True)
        st.success("Conta criada com sucesso!")
        st.rerun()
    except auth.EmailJaCadastrado:
        st.error("Ja existe uma conta com esse e-mail. Faca login.")
