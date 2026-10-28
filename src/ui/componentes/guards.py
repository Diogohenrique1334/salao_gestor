# ---------------------------------------------------------------------------
# ui/componentes/guards.py - sessao do usuario e protecao de paginas.
#
# Mantem o usuario logado em st.session_state (fonte da verdade durante a
# sessao) e persiste um TOKEN ASSINADO em cookie para que o login sobreviva ao
# refresh ("Lembrar de mim").
#
# Token = "<cliente_id>.<expira_epoch>.<hmac_sha256(secret, "id.expira")>"
# Nao guarda dados sensiveis; a fonte real e' sempre o banco (recarrega o
# cliente pelo id). A VALIDADE entra dentro do payload assinado: sem ela, o
# prazo so existiria no navegador (expires do cookie) e um token copiado
# valeria para sempre. Tokens no formato antigo (2 partes) sao recusados.
#
# LEITURA x ESCRITA usam caminhos DIFERENTES, de proposito:
#   - LER  : st.context.cookies (nativo) -> vem nos headers do request e ja
#            esta disponivel na PRIMEIRA execucao do script.
#   - GRAVAR/APAGAR: CookieManager (componente de frontend), que e' o unico que
#            consegue escrever no navegador.
#
# Por que: o CookieManager e' um componente e so responde depois de um
# round-trip com o frontend. Usa-lo para LER fazia `mgr.get()` devolver None na
# primeira execucao - o app montava o menu de deslogado e nunca tentava de
# novo. Resultado: "Lembrar de mim" nao funcionava (F5 deslogava) e link direto
# caia em "Page not found". O componente segue como fallback.
# ---------------------------------------------------------------------------
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Optional

import streamlit as st

from src.config.settings import get_settings
from src.constantes import PAPEL_CABELEIREIRO, PAPEL_GESTOR
from src.db.engine import sessao
from src.db.models import Cliente
from src.repositorios import clientes as repo_clientes

_COOKIE_NOME = "salao_sessao"
_CHAVE_USUARIO = "usuario"
_CHAVE_COOKIE_PENDENTE = "_cookie_pendente"
# marca que o usuario saiu de proposito nesta sessao. Necessario porque
# st.context.cookies vem dos headers do HANDSHAKE: apos o logout o cookie ja
# foi apagado no navegador, mas os headers desta conexao ainda o contem - sem
# esta trava, o restaurar_sessao() logaria o usuario de volta.
_CHAVE_LOGOUT = "_logout_explicito"


# ----- token assinado ------------------------------------------------------
SESSAO_VALIDADE_DIAS = 30   # vale p/ o token E p/ o cookie (nao podem divergir)


def _hmac(payload: str) -> str:
    return hmac.new(
        get_settings().session_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _assinar(cliente_id: int, validade_dias: int = SESSAO_VALIDADE_DIAS) -> str:
    """Monta o token assinado com prazo de validade embutido."""
    expira = int(time.time()) + validade_dias * 86400
    payload = f"{cliente_id}.{expira}"
    return f"{payload}.{_hmac(payload)}"


def _verificar_token(token: str) -> Optional[int]:
    """Valida assinatura E prazo. Retorna o cliente_id, ou None se invalido."""
    try:
        cliente_id, expira, sig = token.split(".")
        payload = f"{cliente_id}.{expira}"
    except (ValueError, AttributeError):
        return None   # inclui o formato antigo de 2 partes (sem validade)

    if not hmac.compare_digest(sig, _hmac(payload)):
        return None
    try:
        if int(expira) < int(time.time()):
            return None   # token vencido
        return int(cliente_id)
    except ValueError:
        return None


# ----- cookie manager: usado apenas para ESCREVER/APAGAR --------------------
def _cookie_mgr():
    """Constroi um CookieManager. NAO cachear a instancia.

    O `__init__` do CookieManager e' o que MONTA o componente na pagina. Ao
    guardar a instancia em session_state, os runs seguintes recebiam o objeto
    sem renderizar nada - e o Streamlit descarta o componente que nao foi
    desenhado no run. Resultado: a escrita pendente nunca chegava ao navegador.
    """
    try:
        import extra_streamlit_components as stx

        return stx.CookieManager(key="cookie_mgr_salao")
    except Exception:
        return None


# ----- leitura do cookie ---------------------------------------------------
def _ler_cookie() -> Optional[str]:
    """Le o token de sessao. Tenta o caminho SINCRONO primeiro.

    1) st.context.cookies - headers do request, disponivel ja na 1a execucao.
    2) CookieManager - fallback (versoes antigas do Streamlit / caso raro em
       que o cookie foi gravado depois do handshake desta conexao).
    """
    try:
        token = st.context.cookies.get(_COOKIE_NOME)
        if token:
            return token
    except Exception:
        pass

    mgr = _cookie_mgr()
    if mgr is None:
        return None
    try:
        return mgr.get(_COOKIE_NOME)
    except Exception:
        return None


def _para_dict(c: Cliente) -> dict:
    return {
        "id": c.id, "nome": c.nome, "email": c.email, "papel": c.papel,
        "telefone": c.telefone, "cabeleireiro_id": c.cabeleireiro_id,
    }


# ----- API publica ---------------------------------------------------------
def usuario_atual() -> Optional[dict]:
    """Usuario logado (dict) ou None."""
    return st.session_state.get(_CHAVE_USUARIO)


def restaurar_sessao() -> None:
    """Se nao ha usuario na sessao, tenta restaurar pelo cookie assinado.

    Chamado no topo do app.py a cada execucao: e' o que faz o F5 e o link
    direto (ex.: /agendar nos favoritos) continuarem logados.
    """
    if usuario_atual() is not None:
        return
    if st.session_state.get(_CHAVE_LOGOUT):   # saiu de proposito: nao re-logar
        return
    token = _ler_cookie()
    if not token:
        return
    cliente_id = _verificar_token(token)
    if cliente_id is None:
        return
    with sessao() as db:
        cliente = repo_clientes.buscar_por_id(db, cliente_id)
        if cliente:
            st.session_state[_CHAVE_USUARIO] = _para_dict(cliente)


def login(cliente: Cliente, lembrar: bool = True) -> None:
    """Registra o usuario na sessao e AGENDA a gravacao do cookie assinado.

    A escrita nao acontece aqui de proposito: quem chama faz `st.rerun()` logo
    em seguida, e um rerun no mesmo run aborta o script ANTES de o delta do
    componente chegar ao navegador - o cookie simplesmente nao era gravado.
    Quem grava e' sincronizar_cookie(), no topo do run seguinte, que termina
    renderizando a pagina normalmente.
    """
    st.session_state[_CHAVE_USUARIO] = _para_dict(cliente)
    st.session_state.pop(_CHAVE_LOGOUT, None)   # limpa a trava de logout
    if lembrar:
        st.session_state[_CHAVE_COOKIE_PENDENTE] = ("gravar", _assinar(cliente.id))


def logout() -> None:
    """Encerra a sessao e agenda a remocao do cookie."""
    st.session_state.pop(_CHAVE_USUARIO, None)
    # trava a restauracao: o cookie sai do navegador, mas os headers DESTA
    # conexao ainda o carregam (ver _CHAVE_LOGOUT).
    st.session_state[_CHAVE_LOGOUT] = True
    st.session_state[_CHAVE_COOKIE_PENDENTE] = ("apagar", None)


def sincronizar_cookie() -> None:
    """Executa a gravacao/remocao pendente do cookie. Chamar no TOPO do app.

    Precisa rodar num run que termina desenhando a pagina (sem st.rerun), para
    o componente ser enviado ao navegador e de fato executar.
    """
    pendente = st.session_state.pop(_CHAVE_COOKIE_PENDENTE, None)
    if pendente is None:
        return
    acao, valor = pendente
    mgr = _cookie_mgr()
    if mgr is None:
        return
    try:
        if acao == "gravar":
            mgr.set(
                _COOKIE_NOME,
                valor,
                # mesma janela do token: o navegador descarta o cookie no
                # mesmo momento em que o servidor deixaria de aceita-lo
                expires_at=datetime.now() + timedelta(days=SESSAO_VALIDADE_DIAS),
                # LAX, nao o "strict" que e' o default da biblioteca: com
                # strict o navegador NAO manda o cookie quando o app e' aberto
                # a partir de um link externo (WhatsApp, QR code, atalho na
                # tela inicial) - a pessoa caia na tela de login mesmo com a
                # sessao valida. Lax manda em navegacao de topo e continua
                # barrando requisicao de terceiro.
                same_site="lax",
                key="set_cookie_login",
            )
        else:
            mgr.delete(_COOKIE_NOME, key="del_cookie_login")
    except Exception:
        pass


def esta_logado() -> bool:
    return usuario_atual() is not None


def eh_gestor() -> bool:
    u = usuario_atual()
    return bool(u and u.get("papel") == PAPEL_GESTOR)


def eh_cabeleireiro() -> bool:
    u = usuario_atual()
    return bool(u and u.get("papel") == PAPEL_CABELEIREIRO)


def require_login() -> dict:
    """Garante usuario logado; senao interrompe a pagina com aviso."""
    u = usuario_atual()
    if u is None:
        st.warning("Faca login para acessar esta pagina.")
        st.stop()
    return u


def require_gestor() -> dict:
    """Garante usuario gestor; senao interrompe a pagina."""
    u = require_login()
    if u.get("papel") != PAPEL_GESTOR:
        st.error("Acesso restrito ao gestor.")
        st.stop()
    return u


def require_cabeleireiro() -> dict:
    """Garante usuario cabeleireiro (com perfil vinculado); senao interrompe."""
    u = require_login()
    if u.get("papel") != PAPEL_CABELEIREIRO or not u.get("cabeleireiro_id"):
        st.error("Acesso restrito ao cabeleireiro.")
        st.stop()
    return u
