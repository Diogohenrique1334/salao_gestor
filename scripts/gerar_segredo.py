# ---------------------------------------------------------------------------
# scripts/gerar_segredo.py — gera segredos aleatorios para o deploy.
#
#   python -m scripts.gerar_segredo
#
# Imprime um SESSION_SECRET e uma senha de gestor, ja no formato de env var
# (Render) e de secrets.toml (dev). Nada e' gravado em disco: copie e cole.
#
# Por que isto existe: o default `dev-secret` assina o cookie de sessao. Quem
# conhece esse valor — ele esta no repositorio — forja o token de qualquer
# usuario, inclusive o gestor. Trocar antes de expor o app na internet nao e'
# opcional.
# ---------------------------------------------------------------------------
from __future__ import annotations

import secrets


def gerar_segredo(n_bytes: int = 48) -> str:
    """String aleatoria segura, urlsafe (sem caracteres que quebram TOML/env)."""
    return secrets.token_urlsafe(n_bytes)


def gerar_senha(n_bytes: int = 12) -> str:
    """Senha curta o bastante para ser digitada, longa o bastante para servir."""
    return secrets.token_urlsafe(n_bytes)


def main() -> None:
    session_secret = gerar_segredo()
    senha_gestor = gerar_senha()

    print("=" * 70)
    print("PARA O DEPLOY (env vars no painel do Render):")
    print("=" * 70)
    print(f"SESSION_SECRET={session_secret}")
    print(f"GESTOR_SENHA={senha_gestor}")
    print()
    print("=" * 70)
    print("PARA DEV (.streamlit/secrets.toml):")
    print("=" * 70)
    print(f'session_secret = "{session_secret}"')
    print()
    print("[gestor]")
    print('email = "gestor@salao.com"')
    print(f'senha = "{senha_gestor}"')
    print()
    print("Obs.: trocar o SESSION_SECRET invalida os cookies existentes —")
    print("todo mundo logado precisa entrar de novo. Faca isso ANTES de entregar.")
    print("A senha do gestor so vale para uma conta NOVA; se o gestor ja existe")
    print("no banco, o seed nao sobrescreve a senha.")


if __name__ == "__main__":
    main()
