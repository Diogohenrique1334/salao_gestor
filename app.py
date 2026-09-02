# ---------------------------------------------------------------------------
# app.py — ENTRYPOINT do Streamlit.
#
# Responsabilidade: configurar a pagina, restaurar a sessao (cookie) e ROTEAR
# por papel:
#   - deslogado -> Login / Cadastro
#   - cliente   -> Agendar / Meus agendamentos
#   - gestor    -> Dashboard / Cabeleireiros / Servicos
# A logica de cada tela vive em src/ui/paginas/*. Aqui so se monta o menu.
#
# Rodar:  streamlit run app.py
# ---------------------------------------------------------------------------
from __future__ import annotations

import streamlit as st

from src.config.settings import aplicar_timezone, get_settings
from src.constantes import PAPEL_CABELEIREIRO, PAPEL_GESTOR
from src.ui.componentes import guards, styles
from src.ui.paginas import (
    agendar,
    cabeleireiro_atendimento,
    cabeleireiro_painel,
    entrada,
    gestor_atendimento,
    gestor_cabeleireiros,
    gestor_clientes,
    gestor_dashboard,
    gestor_ocupacao,
    gestor_servicos,
    meus_agendamentos,
)

# fixa o fuso do processo ANTES de qualquer datetime.now() (Streamlit Cloud roda
# em UTC e nao usa o Dockerfile — sem isto o app fica 3h deslocado)
aplicar_timezone()

st.set_page_config(
    page_title=f"Agendamentos · {get_settings().salao.nome}",
    page_icon="💈",
    layout="wide",
)


def _menu_deslogado():
    # uma unica pagina (Entrar/Criar conta no proprio corpo) — sem menu lateral
    return [st.Page(entrada.render, title="Entrar", icon="🔑", url_path="entrar", default=True)]


def _menu_cliente():
    return {
        "Agendamento": [
            st.Page(agendar.render, title="Agendar", icon="🗓️", url_path="agendar", default=True),
            st.Page(meus_agendamentos.render, title="Meus agendamentos", icon="📋", url_path="meus"),
        ]
    }


def _menu_cabeleireiro():
    return {
        "Minha area": [
            st.Page(cabeleireiro_painel.render, title="Meu painel", icon="📊", url_path="painel", default=True),
            st.Page(cabeleireiro_atendimento.render, title="Registrar atendimento", icon="🧍", url_path="registrar"),
        ]
    }


def _menu_gestor():
    return {
        "Gestao": [
            st.Page(gestor_dashboard.render, title="Dashboard", icon="📊", url_path="dashboard", default=True),
            st.Page(gestor_ocupacao.render, title="Ocupacao", icon="📅", url_path="ocupacao"),
            st.Page(gestor_atendimento.render, title="Atendimento avulso", icon="🧍", url_path="atendimento"),
            st.Page(gestor_cabeleireiros.render, title="Cabeleireiros", icon="✂️", url_path="cabeleireiros"),
            st.Page(gestor_servicos.render, title="Servicos", icon="🧾", url_path="servicos"),
            st.Page(gestor_clientes.render, title="Clientes", icon="👥", url_path="clientes"),
        ]
    }


def _sidebar_usuario(usuario: dict) -> None:
    with st.sidebar:
        st.markdown(f"**{usuario['nome']}**")
        _rotulos = {PAPEL_GESTOR: "Gestor", PAPEL_CABELEIREIRO: "Cabeleireiro"}
        papel = _rotulos.get(usuario.get("papel"), "Cliente")
        st.caption(f"{usuario['email']} · {papel}")
        if st.button("Sair", use_container_width=True):
            guards.logout()
            st.rerun()


def _avisar_segredo_inseguro() -> None:
    """Alerta o GESTOR se o cookie de sessao esta assinado com o segredo padrao.

    Nesse estado qualquer pessoa forja o token de qualquer usuario. O aviso vai
    para o log (visivel no Render) e so aparece na tela para o gestor — nao
    tem por que assustar o cliente do salao com um recado tecnico.
    """
    print(
        "[BOOT] *** SESSION_SECRET no valor PADRAO: o cookie de sessao e' "
        "forjavel. Gere um com `python -m scripts.gerar_segredo`. ***"
    )
    with st.sidebar:
        st.error("SESSION_SECRET esta no padrao — troque antes de expor o app.", icon="🔐")


def main() -> None:
    styles.logo_sidebar()   # marca no topo da sidebar, em todas as telas
    guards.restaurar_sessao()
    usuario = guards.usuario_atual()

    if usuario is None:
        # tela unica: esconde o menu lateral (nao ha o que navegar deslogado)
        st.navigation(_menu_deslogado(), position="hidden").run()
        return

    _sidebar_usuario(usuario)
    papel = usuario.get("papel")
    if papel == PAPEL_GESTOR:
        if get_settings().session_secret_inseguro:
            _avisar_segredo_inseguro()
        paginas = _menu_gestor()
    elif papel == PAPEL_CABELEIREIRO:
        paginas = _menu_cabeleireiro()
    else:
        paginas = _menu_cliente()

    st.navigation(paginas).run()


main()
