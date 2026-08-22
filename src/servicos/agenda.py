# ---------------------------------------------------------------------------
# servicos/agenda.py - CAMADA DE NEGOCIO: disponibilidade e slots.
#
# Duas partes:
#   1) slots_livres(...)  -> funcao PURA (sem banco): dado as janelas de
#      trabalho do dia, a duracao do servico e os intervalos ocupados, devolve
#      os horarios de inicio disponiveis. Facil de testar.
#   2) horarios_disponiveis(db, ...) -> usa repositorios p/ montar os insumos
#      (horario_trabalho do dia + agendamentos ativos) e chama slots_livres.
# ---------------------------------------------------------------------------
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Sequence, Tuple

from sqlalchemy.orm import Session

from src.repositorios import agendamentos as repo_ag
from src.repositorios import bloqueios as repo_bloqueios
from src.repositorios import cabeleireiros as repo_cab
from src.repositorios import servicos as repo_serv

# Granularidade da grade de horarios (de quanto em quanto tempo um slot comeca)
PASSO_PADRAO_MIN = 15


def _sobrepoe(inicio: datetime, fim: datetime, ocupados: Sequence[Tuple[datetime, datetime]]) -> bool:
    for o_ini, o_fim in ocupados:
        if inicio < o_fim and fim > o_ini:
            return True
    return False


def slots_livres(
    janelas: Sequence[Tuple[datetime, datetime]],
    duracao_min: int,
    ocupados: Sequence[Tuple[datetime, datetime]],
    *,
    passo_min: int = PASSO_PADRAO_MIN,
    agora: datetime = None,
) -> List[datetime]:
    """Retorna inicios de slot livres dentro das janelas de trabalho.

    - janelas: lista de (inicio, fim) de trabalho no dia
    - duracao_min: duracao do servico
    - ocupados: intervalos ja reservados (inicio, fim)
    - passo_min: de quanto em quanto tempo um slot pode comecar
    - agora: descarta slots no passado (default datetime.now())
    """
    if agora is None:
        agora = datetime.now()
    duracao = timedelta(minutes=duracao_min)
    passo = timedelta(minutes=passo_min)

    livres: List[datetime] = []
    for janela_ini, janela_fim in janelas:
        atual = janela_ini
        while atual + duracao <= janela_fim:
            fim = atual + duracao
            if atual >= agora and not _sobrepoe(atual, fim, ocupados):
                livres.append(atual)
            atual += passo
    return livres


def _janelas_do_dia(db: Session, cabeleireiro_id: int, dia: date) -> List[Tuple[datetime, datetime]]:
    """Janelas de trabalho (inicio, fim) do cabeleireiro no dia da semana."""
    dia_semana = dia.weekday()  # 0=segunda ... 6=domingo
    return [
        (datetime.combine(dia, h.hora_inicio), datetime.combine(dia, h.hora_fim))
        for h in repo_cab.listar_horarios(db, cabeleireiro_id)
        if h.dia_semana == dia_semana
    ]


def _clip_no_dia(
    intervalos: Sequence[Tuple[datetime, datetime]], dia: date
) -> List[Tuple[datetime, datetime]]:
    """Recorta os intervalos que tocam o dia para dentro de [00:00, 24:00) do dia.

    Funcao PURA: usada no calculo batcheado p/ fatiar agendamentos/bloqueios ja
    carregados, sem novas consultas.
    """
    dia_ini = datetime.combine(dia, time.min)
    dia_fim = dia_ini + timedelta(days=1)
    return [
        (max(ini, dia_ini), min(fim, dia_fim))
        for ini, fim in intervalos
        if ini < dia_fim and fim > dia_ini
    ]


def _ocupados_do_dia(db: Session, cabeleireiro_id: int, dia: date) -> List[Tuple[datetime, datetime]]:
    """Intervalos (inicio, fim) indisponiveis no dia: agendamentos ativos + bloqueios.

    Bloqueios (ferias/folga) entram como ocupado, entao slots_livres/blocos_livres
    ja os excluem sem mudar a funcao pura.
    """
    dia_ini = datetime.combine(dia, time.min)
    dia_fim = dia_ini + timedelta(days=1)
    ocupados = [
        (a.inicio, a.fim)
        for a in repo_ag.listar_por_cabeleireiro_no_dia(db, cabeleireiro_id, dia_ini, dia_fim)
    ]
    ocupados.extend(repo_bloqueios.intervalos_no_dia(db, cabeleireiro_id, dia))
    return ocupados


def horarios_disponiveis(
    db: Session, *, cabeleireiro_id: int, dia: date, servico_id: int, passo_min: int = PASSO_PADRAO_MIN
) -> List[datetime]:
    """Slots livres de um cabeleireiro para um servico num dia (consulta o banco)."""
    servico = repo_serv.buscar_por_id(db, servico_id)
    if servico is None or not servico.ativo:
        return []
    janelas = _janelas_do_dia(db, cabeleireiro_id, dia)
    if not janelas:
        return []
    ocupados = _ocupados_do_dia(db, cabeleireiro_id, dia)
    return slots_livres(janelas, int(servico.duracao_min), ocupados, passo_min=passo_min)


def blocos_livres(db: Session, *, cabeleireiro_id: int, dia: date) -> List[Tuple[datetime, datetime]]:
    """Blocos de tempo livres no dia (janelas de trabalho - ocupados).

    Independe de servico/duracao: responde "quais faixas estao vagas hoje".
    """
    janelas = _janelas_do_dia(db, cabeleireiro_id, dia)
    if not janelas:
        return []
    ocupados = sorted(_ocupados_do_dia(db, cabeleireiro_id, dia))
    livres: List[Tuple[datetime, datetime]] = []
    for janela_ini, janela_fim in janelas:
        cursor = janela_ini
        for o_ini, o_fim in ocupados:
            if o_fim <= cursor or o_ini >= janela_fim:
                continue
            ini_corte = max(o_ini, janela_ini)
            if ini_corte > cursor:
                livres.append((cursor, ini_corte))
            cursor = max(cursor, min(o_fim, janela_fim))
        if cursor < janela_fim:
            livres.append((cursor, janela_fim))
    return livres


def proximos_dias_disponiveis(
    db: Session,
    *,
    cabeleireiro_id: int,
    servico_id: int,
    horizonte_dias: int = 60,
    max_dias: int = 30,
    passo_min: int = PASSO_PADRAO_MIN,
) -> List[date]:
    """Lista os proximos dias (ate `max_dias`) que tem ao menos um slot livre.

    Varre de hoje ate `horizonte_dias` a frente e so inclui os dias com vaga,
    para a UI mostrar apenas datas agendaveis (em vez de um calendario aberto).

    Otimizado: os insumos do horizonte inteiro (servico, horarios de trabalho,
    agendamentos ativos e bloqueios) sao carregados em 4 consultas FIXAS; o loop
    por dia roda em memoria via slots_livres. (Antes era N+1: ~3 queries/dia.)
    """
    servico = repo_serv.buscar_por_id(db, servico_id)
    if servico is None or not servico.ativo:
        return []
    duracao = int(servico.duracao_min)

    hoje = date.today()
    janela_ini = datetime.combine(hoje, time.min)
    janela_fim = datetime.combine(hoje + timedelta(days=horizonte_dias + 1), time.min)

    # 1 query: janelas de trabalho, agrupadas por dia da semana
    horarios_por_ws: Dict[int, List[Tuple[time, time]]] = defaultdict(list)
    for h in repo_cab.listar_horarios(db, cabeleireiro_id):
        horarios_por_ws[h.dia_semana].append((h.hora_inicio, h.hora_fim))
    if not horarios_por_ws:
        return []

    # 1 query: agendamentos ativos do horizonte, agrupados por dia
    ags_por_dia: Dict[date, List[Tuple[datetime, datetime]]] = defaultdict(list)
    for a in repo_ag.listar_por_cabeleireiro_no_dia(db, cabeleireiro_id, janela_ini, janela_fim):
        ags_por_dia[a.inicio.date()].append((a.inicio, a.fim))

    # 1 query: bloqueios do horizonte (mantidos como lista; recortados por dia)
    blocos = [
        (b.inicio, b.fim)
        for b in repo_bloqueios.listar_no_intervalo(db, cabeleireiro_id, janela_ini, janela_fim)
    ]

    agora = datetime.now()
    dias: List[date] = []
    for delta in range(horizonte_dias + 1):
        d = hoje + timedelta(days=delta)
        horarios_do_dia = horarios_por_ws.get(d.weekday())
        if not horarios_do_dia:
            continue
        janelas = [(datetime.combine(d, hi), datetime.combine(d, hf)) for hi, hf in horarios_do_dia]
        ocupados = ags_por_dia.get(d, []) + _clip_no_dia(blocos, d)
        if slots_livres(janelas, duracao, ocupados, passo_min=passo_min, agora=agora):
            dias.append(d)
            if len(dias) >= max_dias:
                break
    return dias
