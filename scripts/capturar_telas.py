# ---------------------------------------------------------------------------
# capturar_telas.py — sobe o app e tira screenshot das telas (dev/visual).
#
# Uso:  python capturar_telas.py [porta] [pasta_saida]
#
# Loga como GESTOR, navega pelas paginas (url_path definido em app.py) e salva
# um PNG por tela. A sessao sobrevive a navegacao por URL gracas ao cookie
# assinado de guards.py.
# ---------------------------------------------------------------------------
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PORTA = int(sys.argv[1]) if len(sys.argv) > 1 else 8599
SAIDA = Path(sys.argv[2] if len(sys.argv) > 2 else "telas")
BASE = f"http://localhost:{PORTA}"

EMAIL = "gestor@salao.com"
SENHA = "admin123"

# (nome do arquivo, ROTULO do link na sidebar) — titles definidos em app.py
TELAS_GESTOR = [
    ("gestor-dashboard", "Dashboard"),
    ("gestor-atendimento", "Atendimento avulso"),
    ("gestor-cabeleireiros", "Cabeleireiros"),
    ("gestor-servicos", "Servicos"),
    ("gestor-clientes", "Clientes"),
]


def _esperar_streamlit(page, extra_ms: int = 0) -> None:
    """Streamlit renderiza via websocket; espera a app parar de desenhar.

    O cold start (primeira carga) e o pos-login precisam de mais folga: o cookie
    de sessao e' gravado por um componente async — navegar antes disso derruba a
    sessao e a proxima pagina responde "Page not found".
    """
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000 + extra_ms)


def _tirar(page, nome: str) -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / f"{nome}.png"
    page.screenshot(path=str(destino), full_page=True)
    print(f"  [ok] {destino}")


def main() -> None:
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        page = navegador.new_page(viewport={"width": 1440, "height": 900})

        print(f"[telas] abrindo {BASE}")
        page.goto(BASE)
        _esperar_streamlit(page, extra_ms=4000)   # cold start do Streamlit
        _tirar(page, "01-login")

        # cadastro (deslogado)
        page.goto(f"{BASE}/cadastro")
        _esperar_streamlit(page)
        _tirar(page, "02-cadastro")

        # login como gestor
        print("[telas] logando como gestor")
        page.goto(BASE)
        _esperar_streamlit(page)
        page.get_by_placeholder("voce@email.com").fill(EMAIL)
        page.locator('input[type="password"]').first.fill(SENHA)
        page.get_by_role("button", name="Entrar").click()
        _esperar_streamlit(page, extra_ms=4000)   # deixa o cookie ser gravado

        # so segue se a sessao realmente abriu (senao as telas saem "Page not found")
        if "Dashboard" not in page.inner_text("body"):
            print("  [!] login falhou — sessao nao abriu")
            _tirar(page, "ERRO-login")
            navegador.close()
            return
        print("  [ok] sessao aberta")

        # Navega CLICANDO no menu lateral. Link direto por URL tambem funciona
        # (a sessao volta pelo cookie), mas clicar nao recarrega a pagina e
        # deixa a captura mais rapida e estavel.
        for i, (nome, rotulo) in enumerate(TELAS_GESTOR, start=3):
            try:
                page.get_by_role("link", name=rotulo, exact=False).first.click()
            except Exception as exc:
                print(f"  [!] nao achei o link '{rotulo}': {type(exc).__name__}")
                continue
            _esperar_streamlit(page)
            _tirar(page, f"{i:02d}-{nome}")

        navegador.close()
        print("[telas] concluido.")


if __name__ == "__main__":
    main()
