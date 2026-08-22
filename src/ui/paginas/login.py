# ---------------------------------------------------------------------------
# ui/paginas/login.py - tela de login.
#
# Coleta e-mail/senha, autentica via servicos.auth e abre a sessao (guards).
# "Lembrar de mim" grava o cookie assinado p/ login persistente.
# ---------------------------------------------------------------------------
from __future__ import annotations

import streamlit as st

from src.config.settings import get_settings
from src.db.engine import sessao
from src.notificacoes import eventos
from src.servicos import auth
from src.ui.componentes import guards, styles

_MIN_SENHA = 6


def _esqueci_senha() -> None:
    with st.expander("Esqueci minha senha"):
        st.caption("Enviamos um codigo de 6 digitos para o seu e-mail (valido por 30 min).")
        email = st.text_input("E-mail da conta", key="reset_email")
        if st.button("Enviar codigo"):
            if not email:
                st.error("Informe o e-mail.")
            else:
                with sessao() as db:
                    par = auth.gerar_codigo_reset(db, email)
                    if par:
                        cliente, codigo = par
                        canal = eventos.enviar_codigo_reset(nome=cliente.nome, email=cliente.email, codigo=codigo)
                        st.info(f"Se o e-mail existir, o codigo foi enviado (via {canal}).")
                    else:
                        # mensagem generica: nao revela se o e-mail existe
                        st.info("Se o e-mail existir, o codigo foi enviado.")

        st.markdown("Ja tem o codigo? Redefina abaixo:")
        with st.form("form_reset"):
            codigo = st.text_input("Codigo recebido")
            nova = st.text_input("Nova senha", type="password")
            nova2 = st.text_input("Confirmar nova senha", type="password")
            if st.form_submit_button("Redefinir senha"):
                if len(nova) < _MIN_SENHA:
                    st.error(f"A senha deve ter ao menos {_MIN_SENHA} caracteres.")
                elif nova != nova2:
                    st.error("As senhas nao conferem.")
                elif not email or not codigo:
                    st.error("Informe o e-mail (acima) e o codigo.")
                else:
                    with sessao() as db:
                        ok = auth.redefinir_com_codigo(db, email, codigo, nova)
                    if ok:
                        st.success("Senha redefinida! Agora e so entrar.")
                    else:
                        st.error("Codigo invalido ou expirado.")


def render() -> None:
    styles.aplicar_estilo_base()
    # nome vem de settings (SALAO_NOME / [salao].nome) - nao hardcode a marca
    styles.cabecalho_marca(get_settings().salao.nome, "Agendamentos")
    styles.titulo_secao("Entrar")

    with st.form("form_login"):
        email = st.text_input("E-mail", placeholder="voce@email.com")
        senha = st.text_input("Senha", type="password")
        lembrar = st.checkbox("Lembrar de mim", value=True)
        enviar = st.form_submit_button("Entrar", type="primary", use_container_width=True)

    if enviar:
        if not email or not senha:
            st.error("Preencha e-mail e senha.")
            return
        with sessao() as db:
            cliente = auth.autenticar(db, email, senha)
        if cliente is None:
            st.error("E-mail ou senha invalidos.")
            return
        guards.login(cliente, lembrar=lembrar)
        st.success(f"Bem-vindo(a), {cliente.nome}!")
        st.rerun()

    _esqueci_senha()
    st.caption("Ainda nao tem conta? Use a pagina **Cadastro** no menu lateral.")
