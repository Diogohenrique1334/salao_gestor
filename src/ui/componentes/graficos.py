# ---------------------------------------------------------------------------
# ui/componentes/graficos.py - graficos do dashboard (ECharts, self-contained).
#
# Os 3 graficos usados pelo app (barras, rosca, linha) sao montados aqui como
# opcoes ECharts e renderizados via streamlit-echarts. Sem dependencia externa:
# o projeto e' autonomo p/ deploy.
#
# Paleta vem da marca (styles): amarelo de destaque + tons de status. Para
# graficos DE STATUS use paleta_status(), que reaproveita as cores dos badges
# (fonte unica em styles) -> donut do dashboard concorda com as listas.
# ---------------------------------------------------------------------------
from __future__ import annotations

from typing import List, Optional

import pandas as pd
from streamlit_echarts import st_echarts

from src.ui.componentes.styles import COR_DESTAQUE, COR_TEXTO_FRACO, cor_status

# Paleta categorica generica, derivada da marca (amarelo -> tons de apoio).
PALETA = [COR_DESTAQUE, "#8a7a0d", "#1f4d2b", "#5a2020", "#5a3520", "#33343c"]

# Grid compacto e tooltip padrao (cards estreitos do dashboard).
_GRID = {"left": "3%", "right": "4%", "bottom": "3%", "top": "12%", "containLabel": True}
_EIXO_LABEL = {"color": COR_TEXTO_FRACO, "fontSize": 10}


def paleta_status(status: List[str]) -> List[str]:
    """Cores dos status na ordem dada (mesma fonte dos badges)."""
    return [cor_status(s) for s in status]


def barras(df: pd.DataFrame, col_categoria: str, col_valor: str, *, key: str, tamanho: str = "320px"):
    """Barras verticais simples com rotulo no topo."""
    options = {
        "tooltip": {"trigger": "axis"},
        "grid": _GRID,
        "xAxis": {
            "type": "category",
            "data": df[col_categoria].astype(str).tolist(),
            "axisLabel": {**_EIXO_LABEL, "rotate": 30},
        },
        "yAxis": {"type": "value", "axisLabel": _EIXO_LABEL},
        "series": [{
            "type": "bar",
            "data": [float(v) for v in df[col_valor].tolist()],
            "itemStyle": {"color": COR_DESTAQUE, "borderRadius": [4, 4, 0, 0]},
            "label": {"show": True, "position": "top", "fontSize": 10, "color": COR_TEXTO_FRACO},
        }],
    }
    return st_echarts(options=options, height=tamanho, key=key)


def rosca(labels: List[str], valores: List[float], *, key: str,
          cores: Optional[List[str]] = None, tamanho: str = "280px"):
    """Donut a partir de listas (labels + valores), legenda embaixo.

    O percentual vai DENTRO da fatia, em branco com contorno escuro: assim fica
    legivel tanto na fatia amarela da marca quanto nas fatias escuras de status.
    """
    cores = cores or PALETA
    data = [
        {"name": str(l), "value": float(v), "itemStyle": {"color": cores[i % len(cores)]}}
        for i, (l, v) in enumerate(zip(labels, valores))
    ]
    options = {
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
        "legend": {
            "bottom": 0, "left": "center", "type": "scroll",
            "textStyle": {"fontSize": 10, "color": COR_TEXTO_FRACO},
            "itemWidth": 12, "itemHeight": 12,
        },
        "series": [{
            "type": "pie",
            "radius": ["42%", "64%"],
            "center": ["50%", "44%"],
            "avoidLabelOverlap": True,
            "data": data,
            "label": {
                "show": True, "position": "inside", "formatter": "{d}%",
                "color": "#ffffff", "fontSize": 10, "fontWeight": "bold",
                # contorno escuro -> legivel na fatia amarela E nas escuras
                "textBorderColor": "#000000", "textBorderWidth": 2,
            },
            "labelLine": {"show": False},
            "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0,0,0,0.5)"}},
        }],
    }
    return st_echarts(options=options, height=tamanho, key=key)


def linha(df: pd.DataFrame, col_x: str, col_y: str, *, key: str, tamanho: str = "320px"):
    """Serie temporal (linha suave com area)."""
    options = {
        "tooltip": {"trigger": "axis"},
        "grid": _GRID,
        "xAxis": {
            "type": "category",
            "data": [str(v) for v in df[col_x].tolist()],
            "axisLabel": _EIXO_LABEL,
        },
        "yAxis": {"type": "value", "axisLabel": _EIXO_LABEL},
        "series": [{
            "type": "line",
            "smooth": True,
            "data": [float(v) for v in df[col_y].tolist()],
            "lineStyle": {"color": COR_DESTAQUE, "width": 3},
            "itemStyle": {"color": COR_DESTAQUE},
            "areaStyle": {"opacity": 0.1, "color": COR_DESTAQUE},
        }],
    }
    return st_echarts(options=options, height=tamanho, key=key)
