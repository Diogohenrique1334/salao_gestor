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

from src.constantes import NOMES_DIAS_SEMANA
from src.db.engine import sessao
from src.repositorios import servicos as repo_serv
from src.servicos import agenda
from src.ui.componentes import guards, styles


def _resumo_dias(servico) -> str:
    """Texto curto dos dias permitidos, p/ o cabecalho da lista."""
    dias = agenda.dias_permitidos(servico)
    if len(dias) == 7:
        return "todos os dias"
    if dias == {0, 1, 2, 3, 4}:
        return "só dias uteis"
    return ", ".join(NOMES_DIAS_SEMANA[i][:3] for i in sorted(dias))


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
        with st.expander(f"{s.ordem}. {s.nome} - {styles.moeda_br(s.preco_base)} · "
                         f"{s.duracao_min} min · {_resumo_dias(s)} · {status}"):
            with st.form(f"edit_servico_{s.id}"):
                c1, c2, c3 = st.columns([2, 1, 1])
                nome = c1.text_input("Nome", value=s.nome, key=f"n_{s.id}")
                duracao = c2.number_input("Duracao (min)", min_value=5, max_value=480,
                                          value=int(s.duracao_min), step=5, key=f"d_{s.id}")
                preco = c3.number_input("Preco-base (R$)", min_value=0.0, value=float(s.preco_base),
                                        step=5.0, format="%.2f", key=f"p_{s.id}")

                c4, c5 = st.columns([1, 3])
                ordem = c4.number_input("Ordem na lista", min_value=1, max_value=999,
                                        value=int(s.ordem), step=1, key=f"o_{s.id}",
                                        help="Menor aparece antes na tela do cliente.")
                dias_sel = c5.multiselect(
                    "Dias em que pode ser marcado",
                    options=list(range(7)),
                    default=sorted(agenda.dias_permitidos(s)),
                    format_func=lambda i: NOMES_DIAS_SEMANA[i],
                    key=f"ds_{s.id}",
                    help="Ex.: o Mensal so em dia util. Vale para marcacao NOVA; "
                         "os agendamentos que ja existem continuam valendo.",
                )

                ativo = st.checkbox("Ativo", value=bool(s.ativo), key=f"a_{s.id}")
                col_salvar, col_remover = st.columns([1, 1])
                salvar = col_salvar.form_submit_button("Salvar", type="primary")
                remover = col_remover.form_submit_button("Desativar")
            if salvar:
                if not dias_sel:
                    # zero dias deixaria o servico inagendavel de um jeito que
                    # nao aparece em lugar nenhum; desativar e' explicito
                    st.error("Marque ao menos um dia. Para suspender o servico, "
                             "use **Desativar**.")
                else:
                    with sessao() as db:
                        repo_serv.atualizar(
                            db, s.id, nome=nome, duracao_min=int(duracao),
                            preco_base=Decimal(str(preco)), ativo=ativo,
                            ordem=int(ordem),
                            dias_semana=",".join(str(i) for i in sorted(dias_sel)),
                        )
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
