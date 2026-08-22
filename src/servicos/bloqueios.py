# ---------------------------------------------------------------------------
# servicos/bloqueios.py — CAMADA DE NEGOCIO: bloqueio de agenda (ferias/folga).
#
# Converte a escolha do usuario (intervalo de DATAS, dia inteiro) no intervalo
# de datetime que o resto do sistema entende (inicio 00:00, fim exclusivo =
# 00:00 do dia seguinte ao ultimo dia bloqueado) e delega ao repositorio.
#
# A integracao com a disponibilidade fica em servicos/agenda.py (bloqueio entra
# como "ocupado") e o bloqueio de reservas em servicos/reservas.py.
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from src.db.models import BloqueioAgenda
from src.repositorios import bloqueios as repo_bloqueios


class PeriodoInvalido(Exception):
    """Intervalo de bloqueio invalido (fim antes do inicio)."""


def criar_bloqueio(
    db: Session,
    *,
    cabeleireiro_id: int,
    data_inicio: date,
    data_fim: date,
    motivo: Optional[str] = None,
) -> BloqueioAgenda:
    """Cria um bloqueio de dia(s) inteiro(s) para o cabeleireiro.

    `data_fim` e' inclusiva (o ultimo dia fica integralmente bloqueado): o
    intervalo gravado vai de 00:00 de `data_inicio` ate 00:00 do dia seguinte a
    `data_fim` (fim exclusivo).
    """
    if data_fim < data_inicio:
        raise PeriodoInvalido((data_inicio, data_fim))
    inicio = datetime.combine(data_inicio, time.min)
    fim = datetime.combine(data_fim + timedelta(days=1), time.min)
    return repo_bloqueios.criar(
        db, cabeleireiro_id=cabeleireiro_id, inicio=inicio, fim=fim, motivo=motivo
    )


def remover_bloqueio(db: Session, bloqueio_id: int) -> None:
    repo_bloqueios.remover(db, bloqueio_id)


def listar(db: Session, cabeleireiro_id: int, apenas_futuros: bool = True) -> List[BloqueioAgenda]:
    return repo_bloqueios.listar_por_cabeleireiro(db, cabeleireiro_id, apenas_futuros=apenas_futuros)
