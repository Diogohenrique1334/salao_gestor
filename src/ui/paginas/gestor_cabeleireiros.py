# ---------------------------------------------------------------------------
# ui/paginas/gestor_cabeleireiros.py - gestao de cabeleireiros.
#
# O gestor pode: cadastrar/editar/remover (soft) cabeleireiros; definir suas
# janelas de trabalho (base p/ gerar slots); e configurar os DESCONTOS
# especificos por servico (percentual ou valor), com preview do preco final.
#
# Camadas usadas: repositorios.cabeleireiros, repositorios.servicos e
# servicos.precificacao (preview).
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import time
from decimal import Decimal

import streamlit as st

from src.constantes import DESCONTO_PERCENTUAL, DESCONTO_VALOR
from src.db.engine import sessao
from src.repositorios import cabeleireiros as repo_cab
from src.repositorios import clientes as repo_cli
from src.repositorios import servicos as repo_serv
from src.servicos import auth, precificacao
from src.ui.componentes import bloqueio_ui, guards, styles

_MIN_SENHA = 6

_DIAS = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]
_OPC_DESCONTO = {"Sem desconto": None, "Percentual (%)": DESCONTO_PERCENTUAL, "Valor (R$)": DESCONTO_VALOR}
_LABEL_POR_TIPO = {None: "Sem desconto", DESCONTO_PERCENTUAL: "Percentual (%)", DESCONTO_VALOR: "Valor (R$)"}


def _form_novo() -> None:
    styles.titulo_secao("Novo cabeleireiro")
    with st.form("novo_cab", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        telefone = c2.text_input("WhatsApp (com DDD)", placeholder="+55 11 99999-9999")
        bio = st.text_area("Bio (opcional)", height=70)
        if st.form_submit_button("Cadastrar", type="primary"):
            if not nome.strip():
                st.error("Informe o nome.")
                return
            with sessao() as db:
                repo_cab.criar(db, nome=nome, telefone=(telefone or None), bio=(bio or None))
            st.success(f"Cabeleireiro '{nome}' cadastrado.")
            st.rerun()


def _editar_dados(prof) -> None:
    with st.form(f"edit_cab_{prof.id}"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome", value=prof.nome, key=f"cn_{prof.id}")
        telefone = c2.text_input("WhatsApp", value=prof.telefone or "", key=f"ct_{prof.id}")
        bio = st.text_area("Bio", value=prof.bio or "", key=f"cb_{prof.id}", height=70)
        ativo = st.checkbox("Ativo", value=bool(prof.ativo), key=f"ca_{prof.id}")
        col1, col2 = st.columns(2)
        salvar = col1.form_submit_button("Salvar dados", type="primary")
        remover = col2.form_submit_button("Remover (desativar)")
    if salvar:
        with sessao() as db:
            repo_cab.atualizar(db, prof.id, nome=nome, telefone=telefone, bio=bio, ativo=ativo)
        st.success("Dados atualizados.")
        st.rerun()
    if remover:
        with sessao() as db:
            repo_cab.remover(db, prof.id)
        st.success("Cabeleireiro desativado.")
        st.rerun()


def _gerir_horarios(prof) -> None:
    st.markdown("**Horarios de trabalho**")
    with sessao() as db:
        horarios = repo_cab.listar_horarios(db, prof.id)
    if horarios:
        for h in horarios:
            col1, col2 = st.columns([4, 1])
            col1.write(f"{_DIAS[h.dia_semana]}: {h.hora_inicio.strftime('%H:%M')} – {h.hora_fim.strftime('%H:%M')}")
            if col2.button("Remover", key=f"rmh_{h.id}"):
                with sessao() as db:
                    repo_cab.remover_horario(db, h.id)
                st.rerun()
    else:
        st.caption("Sem horarios definidos (cliente nao vera slots).")

    with st.form(f"add_horario_{prof.id}", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        dia = c1.selectbox("Dia", options=list(range(7)), format_func=lambda i: _DIAS[i], key=f"hd_{prof.id}")
        ini = c2.time_input("Inicio", value=time(9, 0), key=f"hi_{prof.id}")
        fim = c3.time_input("Fim", value=time(18, 0), key=f"hf_{prof.id}")
        c4.markdown("&nbsp;")
        if c4.form_submit_button("Adicionar"):
            if ini >= fim:
                st.error("Inicio deve ser antes do fim.")
            else:
                with sessao() as db:
                    repo_cab.adicionar_horario(db, prof.id, dia_semana=int(dia), hora_inicio=ini, hora_fim=fim)
                st.rerun()


def _gerir_bloqueios(prof) -> None:
    st.markdown("**Bloqueios de agenda (ferias/folga)**")
    st.caption("Dias bloqueados somem dos horarios oferecidos aos clientes.")
    bloqueio_ui.gerenciar_bloqueios(prof.id, key_prefix=f"gcab_blq_{prof.id}")


def _gerir_descontos(prof) -> None:
    st.markdown("**Servicos e descontos**")
    with sessao() as db:
        servicos = repo_serv.listar(db)  # ativos
        vinculos = {v.servico_id: v for v in repo_serv.listar_vinculos_do_cabeleireiro(db, prof.id, apenas_ativos=False)}

    if not servicos:
        st.caption("Cadastre servicos primeiro (pagina Servicos).")
        return

    with st.form(f"descontos_{prof.id}"):
        escolhas = {}
        for s in servicos:
            v = vinculos.get(s.id)
            oferece_default = bool(v and v.ativo)
            tipo_default = _LABEL_POR_TIPO.get(v.desconto_tipo if v else None, "Sem desconto")
            valor_default = float(v.desconto_valor) if v else 0.0

            c0, c1, c2, c3 = st.columns([2, 2, 1.5, 2])
            oferece = c0.checkbox(s.nome, value=oferece_default, key=f"of_{prof.id}_{s.id}")
            tipo_label = c1.selectbox("Desconto", list(_OPC_DESCONTO.keys()),
                                      index=list(_OPC_DESCONTO).index(tipo_default),
                                      key=f"dt_{prof.id}_{s.id}", label_visibility="collapsed")
            valor = c2.number_input("Valor", min_value=0.0, value=valor_default, step=1.0,
                                    key=f"dv_{prof.id}_{s.id}", label_visibility="collapsed")
            tipo = _OPC_DESCONTO[tipo_label]
            calc = precificacao.calcular_preco(s.preco_base, tipo, Decimal(str(valor)))
            c3.markdown(f"<div style='padding-top:6px'>{styles.moeda_br(calc.preco_base)} → "
                        f"<b>{styles.moeda_br(calc.preco_final)}</b></div>",
                        unsafe_allow_html=True)
            escolhas[s.id] = (oferece, tipo, Decimal(str(valor)))

        if st.form_submit_button("Salvar servicos e descontos", type="primary"):
            with sessao() as db:
                for servico_id, (oferece, tipo, valor) in escolhas.items():
                    if oferece:
                        repo_serv.definir_vinculo(db, cabeleireiro_id=prof.id, servico_id=servico_id,
                                                  desconto_tipo=tipo, desconto_valor=valor, ativo=True)
                    else:
                        repo_serv.remover_vinculo(db, prof.id, servico_id)
            st.success("Servicos e descontos atualizados.")
            st.rerun()


def _gerir_login(prof) -> None:
    st.markdown("**Login do cabeleireiro**")
    with sessao() as db:
        conta = repo_cli.buscar_por_cabeleireiro(db, prof.id)
    if conta:
        st.caption(f"Login ativo: {conta.email} (deixe a senha em branco para manter).")
    else:
        st.caption("Sem login. Defina e-mail e senha para o cabeleireiro acessar o painel dele.")

    with st.form(f"login_cab_{prof.id}"):
        email = st.text_input("E-mail de acesso", value=(conta.email if conta else ""), key=f"le_{prof.id}")
        senha = st.text_input("Senha" + (" (nova)" if conta else ""), type="password", key=f"ls_{prof.id}")
        if st.form_submit_button("Salvar login", type="primary"):
            if not email.strip():
                st.error("Informe o e-mail.")
            elif senha and len(senha) < _MIN_SENHA:
                st.error(f"A senha deve ter ao menos {_MIN_SENHA} caracteres.")
            elif not conta and not senha:
                st.error("Defina uma senha para criar o login.")
            else:
                try:
                    with sessao() as db:
                        auth.definir_login_cabeleireiro(
                            db, cabeleireiro_id=prof.id, nome=prof.nome, email=email, senha=(senha or None)
                        )
                    st.success("Login do cabeleireiro salvo.")
                    st.rerun()
                except auth.EmailJaCadastrado:
                    st.error("Esse e-mail ja pertence a outra conta.")


def render() -> None:
    styles.aplicar_estilo_base()
    guards.require_gestor()
    st.markdown("## ✂️ Cabeleireiros")
    _form_novo()

    styles.titulo_secao("Cabeleireiros cadastrados")
    with sessao() as db:
        profs = repo_cab.listar(db, incluir_inativos=True)
    if not profs:
        st.caption("Nenhum cabeleireiro cadastrado.")
        return

    for prof in profs:
        status = "🟢" if prof.ativo else "⚪"
        with st.expander(f"{status} {prof.nome}"):
            _editar_dados(prof)
            st.divider()
            _gerir_login(prof)
            st.divider()
            _gerir_horarios(prof)
            st.divider()
            _gerir_bloqueios(prof)
            st.divider()
            _gerir_descontos(prof)
