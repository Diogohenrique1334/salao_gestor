# ---------------------------------------------------------------------------
# ui/componentes/ocupacao_ui.py - grade de ocupacao dos proximos dias (CLICAVEL).
#
# Componente compartilhado entre a pagina Ocupacao (gestor, com seletor de
# cabeleireiro) e o painel do CABELEIREIRO (fixo no proprio perfil). Cada dia
# vira um card com Nº de agendamentos + barra de preenchimento e um botao que
# seleciona o dia — quem chama decide o que fazer com o dia escolhido
# (tipicamente abrir a agenda daquele dia).
#
# Os dados vem de servicos.agenda.ocupacao_por_dia (capacidade = trabalho -
# almoco; ocupado = soma da duracao dos agendamentos ativos).
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import date
from typing import List, Optional

import streamlit as st

from src.db.engine import sessao
from src.servicos import agenda
from src.ui.componentes import styles

_DIAS_CURTOS = ["SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM"]
_POR_LINHA = 7  # uma semana por linha

_CSS = f"""
<style>
  .ocup-card {{
      background:{styles.COR_CARD}; border:1px solid {styles.COR_BORDA};
      border-radius:12px; padding:10px 10px 12px; text-align:center;
      margin-bottom:6px;
      /* altura fixa p/ os botoes "Ver" alinharem entre os cards da linha */
      min-height:151px; display:flex; flex-direction:column; justify-content:center;
  }}
  .ocup-card.hoje {{ border-color:{styles.COR_DESTAQUE}; }}
  .ocup-card.sel {{ border-color:{styles.COR_DESTAQUE}; background:#20200e; }}
  .ocup-dia {{ font-size:.68rem; letter-spacing:.12em; color:{styles.COR_TEXTO_FRACO}; font-weight:600; }}
  .ocup-data {{ font-size:.92rem; color:{styles.COR_TEXTO}; font-weight:600; margin-bottom:6px; }}
  .ocup-num {{ font-size:1.7rem; font-weight:800; color:#fff; line-height:1; }}
  .ocup-label {{ font-size:.66rem; color:{styles.COR_TEXTO_FRACO}; margin-bottom:8px; }}
  .ocup-bar {{ height:7px; border-radius:999px; background:{styles.COR_BORDA}; overflow:hidden; }}
  .ocup-fill {{ height:100%; background:{styles.COR_DESTAQUE}; border-radius:999px; }}
  .ocup-pct {{ font-size:.68rem; color:{styles.COR_TEXTO_FRACO}; margin-top:4px; }}
  .ocup-fechado {{ color:{styles.COR_TEXTO_FRACO}; font-size:.85rem; padding:12px 0; }}
</style>
"""


def _html_card(item: dict, selecionado: bool) -> str:
    d = item["data"]
    classes = "ocup-card"
    if selecionado:
        classes += " sel"
    elif d == date.today():
        classes += " hoje"
    topo = (f'<div class="ocup-dia">{_DIAS_CURTOS[d.weekday()]}</div>'
            f'<div class="ocup-data">{d.strftime("%d/%m")}</div>')
    if not item["aberto"]:
        return f'<div class="{classes}">{topo}<div class="ocup-fechado">Fechado</div></div>'
    pct = item["pct"] or 0
    return (
        f'<div class="{classes}">{topo}'
        f'<div class="ocup-num">{item["qtd"]}</div>'
        f'<div class="ocup-label">agendamento{"s" if item["qtd"] != 1 else ""}</div>'
        f'<div class="ocup-bar"><div class="ocup-fill" style="width:{min(pct,100)}%"></div></div>'
        f'<div class="ocup-pct">{pct}% ocupado</div>'
        f'</div>'
    )


def grade_ocupacao(
    *, cabeleireiro_id: Optional[int], dias: int = 14, key_prefix: str = "ocup"
) -> Optional[date]:
    """Renderiza a grade dos proximos `dias` e devolve o dia SELECIONADO (ou None).

    cabeleireiro_id=None soma todos os profissionais ativos (visao do gestor).
    O dia escolhido fica em session_state[f"{key_prefix}_sel"], entao sobrevive
    aos reruns ate o usuario clicar em outro (ou em "Fechar").
    """
    st.markdown(_CSS, unsafe_allow_html=True)
    chave_sel = f"{key_prefix}_sel"

    with sessao() as db:
        ocup = agenda.ocupacao_por_dia(db, cabeleireiro_id=cabeleireiro_id, dias=int(dias))

    if not any(i["aberto"] for i in ocup):
        st.info("Nenhum horario de trabalho cadastrado — sem horarios, nao ha ocupacao a mostrar.")
        return None

    selecionado: Optional[date] = st.session_state.get(chave_sel)

    for inicio in range(0, len(ocup), _POR_LINHA):
        faixa: List[dict] = ocup[inicio:inicio + _POR_LINHA]
        colunas = st.columns(_POR_LINHA)
        for col, item in zip(colunas, faixa):
            d = item["data"]
            with col:
                st.markdown(_html_card(item, selecionado == d), unsafe_allow_html=True)
                marcado = selecionado == d
                if st.button("Ver" if not marcado else "Vendo",
                             key=f"{key_prefix}_btn_{d.isoformat()}",
                             use_container_width=True,
                             type="primary" if marcado else "secondary"):
                    st.session_state[chave_sel] = d
                    st.rerun()

    st.caption("A barra mostra o quanto do dia ja esta preenchido (tempo agendado ÷ "
               "tempo de trabalho). Toque em **Ver** para abrir a agenda do dia.")
    return st.session_state.get(chave_sel)


def limpar_selecao(key_prefix: str = "ocup") -> None:
    """Remove o dia selecionado (usado pelo botao 'Fechar agenda do dia')."""
    st.session_state.pop(f"{key_prefix}_sel", None)
