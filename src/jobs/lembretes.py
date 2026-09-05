# ---------------------------------------------------------------------------
# jobs/lembretes.py — rotina diaria de comunicacao (CLI idempotente).
#
# Faz DUAS coisas numa unica execucao matinal:
#   1) LEMBRETE ao cliente (dia-alvo = hoje + N dias, default amanha):
#      seleciona agendamentos ATIVOS que ainda NAO tiveram lembrete, dispara e
#      marca lembrete_enviado_em. Rodar duas vezes nao reenvia (idempotente).
#   2) RESUMO DA AGENDA DE HOJE a cada profissional ativo — substitui mandar
#      e-mail a cada novo agendamento (que viraria ruido e seria ignorado).
#      Profissional SEM atendimento no dia nao recebe nada: um "voce nao tem
#      nada hoje" diario treina a pessoa a ignorar o e-mail.
#
# Nao idempotente na parte (2): rodar duas vezes manda o resumo duas vezes.
# E' de proposito — nao ha estado a guardar e o custo (e-mail) e' zero.
#
# Desacoplado do app: pode ser chamado por qualquer agendador.
#   python -m src.jobs.lembretes              # lembretes de amanha + agenda de hoje
#   python -m src.jobs.lembretes --dias 1     # idem
#   python -m src.jobs.lembretes --dry-run    # so lista, nao envia/marca
#   python -m src.jobs.lembretes --so-lembretes   # pula o resumo dos profissionais
#
# ATENCAO ao fuso: as datas sao hora LOCAL naive. O runner do GitHub Actions
# roda em UTC -> o workflow fixa TZ=America/Sao_Paulo. Sem isso, a janela do
# dia sai deslocada em 3h.
# ---------------------------------------------------------------------------
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta
from typing import Tuple

from src.config.settings import aplicar_timezone
from src.db.engine import sessao
from src.notificacoes import eventos
from src.repositorios import agendamentos as repo_ag
from src.repositorios import cabeleireiros as repo_cab


def enviar_lembretes(dias: int = 1, dry_run: bool = False) -> int:
    """Lembretes do dia (hoje + `dias`) aos clientes. Retorna quantos foram enviados."""
    alvo = date.today() + timedelta(days=dias)
    inicio = datetime.combine(alvo, time.min)
    fim = inicio + timedelta(days=1)

    enviados = 0
    with sessao() as db:
        pendentes = repo_ag.pendentes_de_lembrete(db, inicio, fim)
        print(f"[lembretes] alvo={alvo} | pendentes={len(pendentes)}")
        for ag in pendentes:
            quando = ag.inicio.strftime("%d/%m %H:%M")
            if dry_run:
                print(f"  [dry-run] agendamento #{ag.id} em {quando}")
                continue
            canais = eventos.enviar_lembrete(db, ag)
            repo_ag.marcar_lembrete_enviado(db, ag.id)
            enviados += 1
            print(f"  enviado #{ag.id} em {quando} via {','.join(canais)}")
    return enviados


def enviar_agendas(dry_run: bool = False) -> int:
    """Resumo da agenda de HOJE a cada profissional ativo. Retorna quantos resumos sairam."""
    hoje = date.today()
    enviados = 0
    with sessao() as db:
        profissionais = repo_cab.listar(db)
        print(f"[agenda-do-dia] {hoje} | profissionais ativos={len(profissionais)}")
        dia_ini = datetime.combine(hoje, time.min)
        dia_fim = dia_ini + timedelta(days=1)
        for prof in profissionais:
            # agenda vazia nao gera e-mail (ver notificacoes.eventos); no dry-run
            # consultamos antes para o relatorio refletir o que realmente sairia
            if dry_run:
                qtd = len(repo_ag.listar_por_cabeleireiro_no_dia(db, prof.id, dia_ini, dia_fim))
                marca = f"{qtd} atendimento(s)" if qtd else "agenda vazia - NAO envia"
                print(f"  [dry-run] {prof.nome}: {marca}")
                continue
            canais = eventos.enviar_agenda_do_dia(db, prof.id, hoje)
            if not canais:
                print(f"  {prof.nome}: agenda vazia - nao enviado")
                continue
            enviados += 1
            print(f"  resumo p/ {prof.nome} via {','.join(canais)}")
    return enviados


def run(dias: int = 1, dry_run: bool = False, so_lembretes: bool = False) -> Tuple[int, int]:
    """Executa a rotina diaria. Retorna (lembretes_enviados, resumos_enviados)."""
    lembretes = enviar_lembretes(dias=dias, dry_run=dry_run)
    resumos = 0 if so_lembretes else enviar_agendas(dry_run=dry_run)
    print(f"[job] concluido | lembretes={lembretes} resumos={resumos}")
    return lembretes, resumos


def main() -> None:
    # runner do GitHub Actions roda em UTC; fixa o fuso antes de montar a janela
    # do dia (mesma convencao de agendamento.inicio) — ver settings.aplicar_timezone
    aplicar_timezone()
    parser = argparse.ArgumentParser(description="Rotina diaria: lembretes + agenda dos profissionais.")
    parser.add_argument("--dias", type=int, default=1, help="quantos dias a frente (default 1=amanha)")
    parser.add_argument("--dry-run", action="store_true", help="lista sem enviar/marcar")
    parser.add_argument("--so-lembretes", action="store_true", help="pula o resumo dos profissionais")
    args = parser.parse_args()
    run(dias=args.dias, dry_run=args.dry_run, so_lembretes=args.so_lembretes)


if __name__ == "__main__":
    main()
