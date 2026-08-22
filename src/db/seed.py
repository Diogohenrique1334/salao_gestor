# ---------------------------------------------------------------------------
# db/seed.py — povoamento inicial (idempotente).
#
# Cria: conta do gestor (de settings), servicos de exemplo e um cabeleireiro
# com horarios de trabalho e um desconto especifico. Rodar APOS as migrations:
#     python -m src.db.seed
# Pode rodar varias vezes sem duplicar (verifica existencia antes de inserir).
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import time
from decimal import Decimal

from src.config.settings import get_settings
from src.constantes import DESCONTO_PERCENTUAL, PAPEL_GESTOR
from src.db.engine import sessao
from src.repositorios import cabeleireiros as repo_cab
from src.repositorios import clientes as repo_cli
from src.repositorios import servicos as repo_serv
from src.servicos.auth import hash_senha


SENHA_INSEGURA = "admin123"  # default de settings.py — nunca deve chegar em producao


def _seed_gestor(db) -> None:
    cfg = get_settings().gestor
    if repo_cli.buscar_por_email(db, cfg.email):
        print(f"[seed] gestor ja existe: {cfg.email}")
        return
    if cfg.senha == SENHA_INSEGURA:
        print(
            "[seed] *** ATENCAO: criando o gestor com a senha PADRAO. "
            "Defina GESTOR_SENHA (deploy) ou [gestor].senha (dev) antes de entregar. ***"
        )
    repo_cli.criar(
        db,
        nome="Gestor do Salao",
        email=cfg.email,
        senha_hash=hash_senha(cfg.senha),
        papel=PAPEL_GESTOR,
    )
    print(f"[seed] gestor criado: {cfg.email}")


def _seed_servicos(db) -> dict:
    existentes = {s.nome: s for s in repo_serv.listar(db, incluir_inativos=True)}
    desejados = [
        ("Corte", 30, Decimal("40.00")),
        ("Barba", 20, Decimal("25.00")),
        ("Coloracao", 90, Decimal("120.00")),
    ]
    resultado = {}
    for nome, dur, preco in desejados:
        if nome in existentes:
            resultado[nome] = existentes[nome]
            continue
        resultado[nome] = repo_serv.criar(db, nome=nome, duracao_min=dur, preco_base=preco)
        print(f"[seed] servico criado: {nome}")
    return resultado


def _seed_cabeleireiro(db, servicos: dict) -> None:
    if any(c.nome == "Joao Silva" for c in repo_cab.listar(db, incluir_inativos=True)):
        print("[seed] cabeleireiro de exemplo ja existe")
        return
    prof = repo_cab.criar(db, nome="Joao Silva", telefone="+5511999999999", bio="Cortes classicos e barba.")
    # Horarios: segunda(0) a sexta(4), 09:00-18:00
    for dia in range(0, 5):
        repo_cab.adicionar_horario(
            db, prof.id, dia_semana=dia, hora_inicio=time(9, 0), hora_fim=time(18, 0)
        )
    # Vinculos com desconto especifico: 10% no Corte; demais sem desconto
    repo_serv.definir_vinculo(
        db,
        cabeleireiro_id=prof.id,
        servico_id=servicos["Corte"].id,
        desconto_tipo=DESCONTO_PERCENTUAL,
        desconto_valor=Decimal("10"),
    )
    for nome in ("Barba", "Coloracao"):
        repo_serv.definir_vinculo(
            db,
            cabeleireiro_id=prof.id,
            servico_id=servicos[nome].id,
            desconto_tipo=None,
            desconto_valor=Decimal("0"),
        )
    print("[seed] cabeleireiro de exemplo criado: Joao Silva (10% no Corte)")


def main() -> None:
    if get_settings().session_secret_inseguro:
        print(
            "[seed] *** ATENCAO: SESSION_SECRET esta no valor PADRAO do repositorio. "
            "Com ele, qualquer pessoa forja o cookie de sessao de qualquer usuario "
            "(inclusive o gestor). Gere um: python -m scripts.gerar_segredo ***"
        )
    with sessao() as db:
        _seed_gestor(db)
        servicos = _seed_servicos(db)
        _seed_cabeleireiro(db, servicos)
    print("[seed] concluido.")


if __name__ == "__main__":
    main()
