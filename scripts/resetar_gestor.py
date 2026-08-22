# ---------------------------------------------------------------------------
# scripts/resetar_gestor.py — define/atualiza a conta do gestor no banco.
#
#   python -m scripts.resetar_gestor
#
# Por que existe: o login e' autenticado contra o BANCO, nao contra o
# secrets.toml. O [gestor] do secrets so serve de molde para o seed CRIAR o
# gestor na primeira vez — o seed e' idempotente e nunca sobrescreve a senha de
# um gestor ja existente. Entao mudar [gestor] no secrets.toml e reiniciar o
# app NAO muda o login. Este script escreve no banco de fato.
#
# Tambem serve de RESET DE EMERGENCIA: como nao ha ninguem acima do gestor para
# reseta-lo pela UI, se ele esquecer a senha (e o SMTP nao entregar o codigo),
# e' rodando isto que se recupera o acesso.
#
# Le o alvo de [gestor] no secrets.toml (email + senha). Se ja existe um gestor
# com OUTRO email, atualiza email E senha desse gestor (nao cria um segundo).
# ---------------------------------------------------------------------------
from __future__ import annotations

from src.config.settings import get_settings
from src.constantes import PAPEL_GESTOR
from src.db.engine import sessao
from src.repositorios import clientes as repo
from src.servicos.auth import hash_senha


def main() -> None:
    cfg = get_settings().gestor
    alvo_email = cfg.email.strip().lower()

    with sessao() as db:
        gestores = repo.listar(db, papel=PAPEL_GESTOR)

        # 1) ja existe conta com o email-alvo? troca so a senha.
        por_email = repo.buscar_por_email(db, alvo_email)
        if por_email is not None and por_email.papel == PAPEL_GESTOR:
            repo.definir_senha(db, por_email.id, hash_senha(cfg.senha))
            print(f"[reset-gestor] senha atualizada para {alvo_email} (id={por_email.id}).")
            return

        # 2) existe UM gestor com outro email? atualiza email + senha dele.
        if len(gestores) == 1:
            g = gestores[0]
            antigo = g.email
            g.email = alvo_email
            g.senha_hash = hash_senha(cfg.senha)
            db.flush()
            print(f"[reset-gestor] gestor id={g.id} migrado: {antigo!r} -> {alvo_email!r}, senha trocada.")
            return

        # 3) nenhum gestor: cria.
        if not gestores:
            novo = repo.criar(
                db, nome="Gestor do Salao", email=alvo_email,
                senha_hash=hash_senha(cfg.senha), papel=PAPEL_GESTOR,
            )
            print(f"[reset-gestor] gestor criado: {alvo_email} (id={novo.id}).")
            return

        # 4) varios gestores com emails diferentes do alvo: ambiguo, nao adivinha.
        print("[reset-gestor] ha varios gestores e nenhum com o email-alvo. "
              "Ajuste manualmente qual deve receber o novo email/senha:")
        for g in gestores:
            print(f"    id={g.id} email={g.email!r}")


if __name__ == "__main__":
    main()
