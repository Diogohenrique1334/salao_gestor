# ---------------------------------------------------------------------------
# ui/componentes/styles.py - identidade visual (Barbearia Recortes).
#
# Paleta extraida do logo da marca (assets/logo.png):
#   amarelo #F7DF01 (destaque) · preto (fundo) · branco (texto)
#
# Fornece: CSS global (cards escuros, headings com barra amarela, KPI boxes,
# botoes com contraste correto) e helpers de render (logo, badges, KPI).
#
# CONTRASTE: o amarelo da marca e' MUITO claro (luminancia ~0.87). Texto branco
# sobre ele fica ilegivel - todo elemento preenchido de amarelo usa texto PRETO.
# Por isso o CSS sobrescreve o botao primario do Streamlit, que vem branco.
# ---------------------------------------------------------------------------
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Optional

import streamlit as st
from streamlit.components.v1 import html as componentes_html

from src.constantes import (
    STATUS_CANCELADO,
    STATUS_CONCLUIDO,
    STATUS_CONFIRMADO,
    STATUS_NO_SHOW,
    STATUS_REAGENDADO,
)

# ----- paleta da marca -----------------------------------------------------
COR_DESTAQUE = "#F7DF01"      # amarelo Recortes
COR_DESTAQUE_ESCURA = "#C9B500"  # hover/estados pressionados
COR_SOBRE_DESTAQUE = "#111111"   # texto por cima do amarelo (nunca branco)
COR_FUNDO = "#0d0d0f"
COR_CARD = "#17171a"
COR_BORDA = "#2a2a2f"
COR_TEXTO = "#f0f0f0"
COR_TEXTO_FRACO = "#9a9aa2"

# raiz do projeto -> assets/ (funciona sob `streamlit run` e em CLI)
_RAIZ = Path(__file__).resolve().parents[3]
CAMINHO_LOGO = _RAIZ / "assets" / "logo.png"

_CSS = f"""
<style>
  /* ----- superficies ----- */
  .bloco-card {{
      background: {COR_CARD};
      border: 1px solid {COR_BORDA};
      border-radius: 14px;
      padding: 18px 20px;
      margin-bottom: 16px;
  }}
  .bloco-card:hover {{ border-color: #3a3a42; }}

  /* ----- heading de secao (barra amarela) ----- */
  .titulo-secao {{
      display: flex; align-items: center; gap: 10px;
      font-size: 1.15rem; font-weight: 700; color: {COR_TEXTO};
      margin: 6px 0 14px 0; letter-spacing: .2px;
  }}
  .titulo-secao::before {{
      content: ""; display: inline-block;
      width: 4px; height: 22px; border-radius: 3px;
      background: {COR_DESTAQUE};
  }}

  /* ----- KPI ----- */
  .kpi-box {{
      background: {COR_CARD};
      border: 1px solid {COR_BORDA};
      border-left: 4px solid {COR_DESTAQUE};
      border-radius: 12px;
      padding: 14px 16px;
  }}
  .kpi-box .kpi-label {{ font-size: .8rem; color: {COR_TEXTO_FRACO}; margin: 0; }}
  .kpi-box .kpi-valor {{ font-size: 1.6rem; font-weight: 700; color: #fff; margin: 2px 0 0 0; }}

  /* ----- badges ----- */
  .badge {{
      display:inline-block; padding:2px 10px; border-radius:999px;
      font-size:.75rem; font-weight:600; white-space:nowrap;
  }}

  /* ----- cabecalho da marca ----- */
  .marca {{
      display:flex; align-items:center; gap:14px; margin: 4px 0 18px 0;
  }}
  .marca .marca-nome {{
      font-size:1.6rem; font-weight:800; color:{COR_TEXTO}; line-height:1.1;
      letter-spacing:.3px; margin:0;
  }}
  .marca .marca-sub {{
      font-size:.85rem; color:{COR_DESTAQUE}; margin:2px 0 0 0;
      text-transform:uppercase; letter-spacing:2px; font-weight:600;
  }}

  /* ----- botao primario: texto PRETO sobre o amarelo -----
     O seletor vai por data-testid com prefixo porque o Streamlit usa kinds
     distintos p/ botao solto e submit de form ("primary" vs
     "primaryFormSubmit"); o prefixo cobre os dois. As classes st-emotion-*
     sao geradas por build e NAO servem de ancora. */
  button[data-testid^="stBaseButton-primary"] {{
      background: {COR_DESTAQUE} !important;
      color: {COR_SOBRE_DESTAQUE} !important;
      border: none !important;
      font-weight: 700 !important;
  }}
  button[data-testid^="stBaseButton-primary"]:hover,
  button[data-testid^="stBaseButton-primary"]:focus {{
      background: {COR_DESTAQUE_ESCURA} !important;
      color: {COR_SOBRE_DESTAQUE} !important;
  }}
  button[data-testid^="stBaseButton-primary"] * {{ color: {COR_SOBRE_DESTAQUE} !important; }}

  /* botao secundario: contorno discreto que acende no hover */
  button[data-testid^="stBaseButton-secondary"] {{
      border: 1px solid {COR_BORDA} !important;
      color: {COR_TEXTO} !important;
  }}
  button[data-testid^="stBaseButton-secondary"]:hover {{
      border-color: {COR_DESTAQUE} !important;
      color: {COR_DESTAQUE} !important;
  }}

  /* checkbox marcado tambem fica amarelo: o "check" precisa ser escuro */
  [data-testid="stCheckbox"] svg {{ color: {COR_SOBRE_DESTAQUE} !important; fill: {COR_SOBRE_DESTAQUE} !important; }}

  /* ----- lista de servicos (st.radio) -----
     O cliente escolhia o servico num menu fechado de 11 itens, cinco deles
     comecando com "Corte" - e marcava errado. Agora e' lista aberta: nome
     grande e em destaque, preco/duracao na legenda. Os seletores vao por
     data-testid (estavel); as classes st-emotion-* sao geradas por build. */
  [data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] p {{
      font-size: 1.06rem !important;
      font-weight: 700 !important;
      color: {COR_TEXTO} !important;
      line-height: 1.3;
  }}
  [data-testid="stRadio"] label {{ padding: 5px 0; }}
  [data-testid="stRadio"] [data-testid="stCaptionContainer"] p {{
      font-size: .88rem !important;
      color: {COR_TEXTO_FRACO} !important;
  }}

  /* ----- agenda do dia: hora em destaque, nome maior ----- */
  .ag-hora {{
      font-size: 1.22rem; font-weight: 800; color: {COR_DESTAQUE};
      line-height: 1.1; letter-spacing: .01em;
  }}
  .ag-quem {{ font-size: 1.02rem; font-weight: 600; color: #fff; margin-top: 3px; }}
  .ag-det  {{ font-size: .86rem; color: {COR_TEXTO_FRACO}; margin-top: 3px; }}

  /* item de menu ativo na sidebar acompanha a marca */
  [data-testid="stSidebarNav"] a[aria-current="page"] {{
      border-left: 3px solid {COR_DESTAQUE};
  }}
</style>
"""


def _declarar_idioma_pt() -> None:
    """Marca o documento como pt-BR e desliga a traducao automatica do navegador.

    Por que: o Streamlit serve a pagina sem declarar idioma. O Chrome entao
    chuta — e com os rotulos em portugues SEM acento ("Servico", "Horario") ele
    chutava errado e "traduzia" a tela, estragando o conteudo: "Sex" virava
    "Sexo", "Registrar atendimento" virava "Registrador" e "13:30" virava
    "13h30". Declarando o idioma, ele para de tentar.

    Precisa ser via componente: st.markdown(unsafe_allow_html=True) nao executa
    <script>. O iframe tem a mesma origem, entao alcanca window.parent.
    """
    componentes_html(
        """
        <script>
          const doc = window.parent.document;
          doc.documentElement.lang = "pt-BR";
          doc.documentElement.setAttribute("translate", "no");
          doc.documentElement.classList.add("notranslate");
          let meta = doc.querySelector('meta[name="google"]');
          if (!meta) {
            meta = doc.createElement("meta");
            meta.setAttribute("name", "google");
            doc.head.appendChild(meta);
          }
          meta.setAttribute("content", "notranslate");
        </script>
        """,
        height=0,
    )


def aplicar_estilo_base() -> None:
    """Injeta o CSS global. Chamar uma vez no inicio de cada pagina."""
    _declarar_idioma_pt()
    st.markdown(_CSS, unsafe_allow_html=True)


def logo_sidebar() -> None:
    """Coloca o logo da barbearia no topo da sidebar (chamar no app.py)."""
    if CAMINHO_LOGO.exists():
        st.logo(str(CAMINHO_LOGO), size="large")


def cabecalho_marca(titulo: str, subtitulo: Optional[str] = None) -> None:
    """Cabecalho de pagina com o logo ao lado do nome - usado na tela de entrada."""
    col_logo, col_texto = st.columns([1, 5], vertical_alignment="center")
    with col_logo:
        if CAMINHO_LOGO.exists():
            st.image(str(CAMINHO_LOGO), width=88)
    with col_texto:
        sub = f'<p class="marca-sub">{subtitulo}</p>' if subtitulo else ""
        st.markdown(
            f'<div class="marca"><div><p class="marca-nome">{titulo}</p>{sub}</div></div>',
            unsafe_allow_html=True,
        )


def titulo_secao(texto: str) -> None:
    """Heading de secao com barra lateral amarela."""
    st.markdown(f'<div class="titulo-secao">{texto}</div>', unsafe_allow_html=True)


def kpi_box(label: str, valor: str, cor: Optional[str] = None) -> None:
    """Renderiza um KPI em box estilizado (em vez de st.metric cru)."""
    borda = cor or COR_DESTAQUE
    st.markdown(
        f"""
        <div class="kpi-box" style="border-left-color:{borda}">
            <p class="kpi-label">{label}</p>
            <p class="kpi-valor">{valor}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(texto: str, cor_fundo: str, cor_texto: str = "#fff") -> str:
    """Retorna HTML de um badge colorido (use com st.markdown unsafe_allow_html)."""
    return f'<span class="badge" style="background:{cor_fundo};color:{cor_texto}">{texto}</span>'


# Cor + rotulo de cada status. Mantem o SIGNIFICADO (verde=ok, vermelho=problema)
# em tons dessaturados, para o amarelo da marca seguir sendo o unico destaque
# forte da tela. "Confirmado" usa o amarelo por ser o estado que pede atencao.
_BADGE_STATUS = {
    STATUS_CONFIRMADO: (COR_DESTAQUE, "Confirmado", COR_SOBRE_DESTAQUE),
    STATUS_REAGENDADO: ("#8a7a0d", "Reagendado", "#fff"),
    STATUS_CONCLUIDO: ("#1f4d2b", "Concluido", "#fff"),
    STATUS_CANCELADO: ("#5a2020", "Cancelado", "#fff"),
    STATUS_NO_SHOW: ("#5a3520", "Faltou", "#fff"),
}


def badge_status(status: str) -> str:
    """HTML do badge para um status de agendamento (cor/rotulo padronizados)."""
    cor, rotulo, cor_texto = _BADGE_STATUS.get(status, ("#33343c", status, "#fff"))
    return badge(rotulo, cor, cor_texto)


def cor_status(status: str) -> str:
    """Cor de um status. FONTE UNICA - graficos usam isto para que o donut do
    dashboard e os badges das listas falem a mesma linguagem visual."""
    return _BADGE_STATUS.get(status, ("#33343c", "", ""))[0]


def rotulo_status(status: str) -> str:
    """Rotulo legivel de um status (mesma fonte do badge)."""
    return _BADGE_STATUS.get(status, ("", status, ""))[1]


_DIAS_PT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]


def formatar_data_br(d) -> str:
    """Formata uma date como 'Seg, 22/06/2026' (sem depender de locale)."""
    return f"{_DIAS_PT[d.weekday()]}, {d.strftime('%d/%m/%Y')}"


def moeda_br(valor) -> str:
    """Formata como 'R$ 1.234,50' (padrao BR, sem depender de locale).

    O default do Python ('R$ 25.00') le como erro para o cliente brasileiro.
    """
    texto = f"{Decimal(valor):,.2f}"                       # 1,234.50 (padrao en)
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"
