# ---------------------------------------------------------------------------
# ui/paginas/gestor_ocupacao.py - visao panoramica de ocupacao (gestor).
#
# Mostra os proximos dias em grade, cada um com o Nº de agendamentos e uma
# barra de preenchimento (ocupado / capacidade). O gestor tem a nocao do
# movimento sem precisar clicar dia a dia. Seletor por cabeleireiro (ou todos).
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import date

import streamlit as st

from src.db.engine import sessao
from src.repositorios import cabeleireiros as repo_cab
from src.servicos import agenda
from src.ui.componentes import guards, styles

_DIAS_CURTOS = ["SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM"]

_CSS = f"""
<style>
  .ocup-grade {{
      display:grid; grid-template-columns:repeat(auto-fill,minmax(120px,1fr));
      gap:12px; margin-top:8px;
  }}
  .ocup-card {{
      background:{styles.COR_CARD}; border:1px solid {styles.COR_BORDA};
      border-radius:12px; padding:12px 14px; text-align:center;
  }}
  .ocup-card.hoje {{ border-color:{styles.COR_DESTAQUE}; }}
  .ocup-dia {{ font-size:.72rem; letter-spacing:.12em; color:{styles.COR_TEXTO_FRACO}; font-weight:600; }}
  .ocup-data {{ font-size:.95rem; color:{styles.COR_TEXTO}; font-weight:600; margin-bottom:8px; }}
  .ocup-num {{ font-size:2rem; font-weight:800; color:#fff; line-height:1; }}
  .ocup-label {{ font-size:.72rem; color:{styles.COR_TEXTO_FRACO}; margin-bottom:10px; }}
  .ocup-bar {{ height:8px; border-radius:999px; background:{styles.COR_BORDA}; overflow:hidden; }}
  .ocup-fill {{ height:100%; background:{styles.COR_DESTAQUE}; border-radius:999px; }}
  .ocup-pct {{ font-size:.72rem; color:{styles.COR_TEXTO_FRACO}; margin-top:4px; }}
  .ocup-fechado {{ color:{styles.COR_TEXTO_FRACO}; font-size:.9rem; padding:14px 0; }}
</style>
"""


def _card(item: dict) -> str:
    d = item["data"]
    dia = _DIAS_CURTOS[d.weekday()]
    hoje_cls = " hoje" if d == date.today() else ""
    cab = f'<div class="ocup-dia">{dia}</div><div class="ocup-data">{d.strftime("%d/%m")}</div>'
    if not item["aberto"]:
        return f'<div class="ocup-card{hoje_cls}">{cab}<div class="ocup-fechado">Fechado</div></div>'
    pct = item["pct"] or 0
    return (
        f'<div class="ocup-card{hoje_cls}">{cab}'
        f'<div class="ocup-num">{item["qtd"]}</div>'
        f'<div class="ocup-label">agendamento{"s" if item["qtd"] != 1 else ""}</div>'
        f'<div class="ocup-bar"><div class="ocup-fill" style="width:{min(pct,100)}%"></div></div>'
        f'<div class="ocup-pct">{pct}% ocupado</div>'
        f'</div>'
    )


def render() -> None:
    styles.aplicar_estilo_base()
    guards.require_gestor()
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown("## 📅 Ocupacao dos proximos dias")

    with sessao() as db:
        profs = repo_cab.listar(db)
    opcoes = {"Todos os cabeleireiros": None}
    opcoes.update({p.nome: p.id for p in profs})

    c1, c2 = st.columns([2, 2])
    escolha = c1.selectbox("Cabeleireiro", list(opcoes.keys()))
    dias = c2.segmented_control("Periodo", [7, 14, 30], default=14,
                                format_func=lambda n: f"{n} dias") or 14

    with sessao() as db:
        ocup = agenda.ocupacao_por_dia(db, cabeleireiro_id=opcoes[escolha], dias=int(dias))

    if not any(i["aberto"] for i in ocup):
        st.info("Nenhum horario de trabalho cadastrado — cadastre em **Cabeleireiros** "
                "para ver a ocupacao.")
        return

    cards = "".join(_card(i) for i in ocup)
    st.markdown(f'<div class="ocup-grade">{cards}</div>', unsafe_allow_html=True)
    st.caption("A barra mostra o quanto do dia ja esta preenchido (tempo agendado ÷ "
               "tempo de trabalho). Dias fechados nao tem horario de trabalho.")
