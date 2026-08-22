# ---------------------------------------------------------------------------
# ui/paginas/gestor_servicos.py — CRUD de servicos (preco-base e duracao).
#
# O gestor cadastra/edita/desativa servicos. O preco-base definido aqui e' a
# referencia sobre a qual os descontos por cabeleireiro sao aplicados
# (ver gestor_cabeleireiros.py + servicos/precificacao.py).
# ---------------------------------------------------------------------------
from __future__ import annotations

from decimal import Decimal

import streamlit as st

from src.db.engine import sessao
from src.repositorios import servicos as repo_serv
from src.ui.componentes import guards, styles


def _form_novo() -> None:
    styles.titulo_secao("Novo servico")
    with st.form("novo_servico", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        nome = c1.text_input("Nome", placeholder="Ex.: Corte degrade")
        duracao = c2.number_input("Duracao (min)", min_value=5, max_value=480, value=30, step=5)
        preco = c3.number_input("Preco-base (R$)", min_value=0.0, value=40.0, step=5.0, format="%.2f")
        if st.form_submit_button("Cadastrar servico", type="primary"):
            if not nome.strip():
                st.error("Informe o nome do servico.")
                return
            with sessao() as db:
                repo_serv.criar(db, nome=nome, duracao_min=int(duracao), preco_base=Decimal(str(preco)))
            st.success(f"Servico '{nome}' cadastrado.")
            st.rerun()


def _lista_servicos() -> None:
    styles.titulo_secao("Servicos cadastrados")
    with sessao() as db:
        servs = repo_serv.listar(db, incluir_inativos=True)

    if not servs:
        st.caption("Nenhum servico cadastrado ainda.")
        return

    for s in servs:
        status = "🟢 ativo" if s.ativo else "⚪ inativo"
        with st.expander(f"{s.nome} — {styles.moeda_br(s.preco_base)} · {s.duracao_min} min · {status}"):
            with st.form(f"edit_servico_{s.id}"):
                c1, c2, c3 = st.columns([2, 1, 1])
                nome = c1.text_input("Nome", value=s.nome, key=f"n_{s.id}")
                duracao = c2.number_input("Duracao (min)", min_value=5, max_value=480,
                                          value=int(s.duracao_min), step=5, key=f"d_{s.id}")
                preco = c3.number_input("Preco-base (R$)", min_value=0.0, value=float(s.preco_base),
                                        step=5.0, format="%.2f", key=f"p_{s.id}")
                ativo = st.checkbox("Ativo", value=bool(s.ativo), key=f"a_{s.id}")
                col_salvar, col_remover = st.columns([1, 1])
                salvar = col_salvar.form_submit_button("Salvar", type="primary")
                remover = col_remover.form_submit_button("Desativar")
            if salvar:
                with sessao() as db:
                    repo_serv.atualizar(db, s.id, nome=nome, duracao_min=int(duracao),
                                        preco_base=Decimal(str(preco)), ativo=ativo)
                st.success("Servico atualizado.")
                st.rerun()
            if remover:
                with sessao() as db:
                    repo_serv.remover(db, s.id)
                st.success("Servico desativado.")
                st.rerun()


def render() -> None:
    styles.aplicar_estilo_base()
    guards.require_gestor()
    st.markdown("## 🧾 Servicos")
    _form_novo()
    _lista_servicos()
