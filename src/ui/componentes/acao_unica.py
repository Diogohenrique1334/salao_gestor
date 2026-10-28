# ---------------------------------------------------------------------------
# ui/componentes/acao_unica.py - botao que CONGELA enquanto a acao roda.
#
# POR QUE EXISTE
# --------------
# Agendar, cancelar e reagendar fazem trabalho lento (banco + e-mail). O botao
# do Streamlit continua clicavel durante esse tempo: o cliente nao ve nada
# acontecer, toca de novo, e cada toque vira um rerun com o botao em True.
# Em producao isso gerou reserva repetida e e-mail de cancelamento duplicado.
#
# Ignorar o clique extra (trava em session_state) resolve o estrago mas nao o
# sintoma: a tela segue parecendo que nao respondeu. Aqui o botao fica
# DESABILITADO na tela enquanto trabalha, que e' o que o usuario precisa ver.
#
# COMO FUNCIONA - um ciclo de tres runs
#   run 1: botao habilitado. O clique marca "ocupado" e pede rerun na hora,
#          ANTES de qualquer trabalho - por isso a marca nunca se perde.
#   run 2: o botao e' desenhado JA DESABILITADO (o usuario ve travado) e a
#          funcao devolve True. O chamador executa o trabalho lento aqui;
#          como o botao foi desenhado antes, ele chega na tela primeiro.
#   run 3: o chamador chamou liberar() e tudo volta ao normal.
#
# CONTRATO: quem recebe True DEVE chamar liberar() no fim, em `finally` - sem
# isso o botao fica travado para sempre naquela sessao.
# ---------------------------------------------------------------------------
from __future__ import annotations

from typing import Optional

import streamlit as st

_PREFIXO = "_acao_"


def _chave(nome: str) -> str:
    return f"{_PREFIXO}{nome}"


def ocupado(nome: str) -> bool:
    """True se a acao `nome` esta em andamento."""
    return bool(st.session_state.get(_chave(nome)))


def liberar(nome: str) -> None:
    """Destrava o botao. Chamar SEMPRE no fim da acao (inclusive em erro)."""
    st.session_state.pop(_chave(nome), None)


def botao(
    rotulo: str,
    *,
    nome: str,
    rotulo_ocupado: Optional[str] = None,
    **kwargs,
) -> bool:
    """Botao de acao unica. True no run em que a acao deve EXECUTAR.

    `nome` identifica a acao e precisa ser unico na pagina (ex.: inclua o id
    do agendamento). `kwargs` vai direto para st.button (type, use_container_width...).
    """
    chave = _chave(nome)
    travado = bool(st.session_state.get(chave))

    clicou = st.button(
        (rotulo_ocupado or "Aguarde...") if travado else rotulo,
        key=f"btn_{nome}",
        disabled=travado,
        **kwargs,
    )

    if clicou:
        # Marca e devolve o controle ao Streamlit IMEDIATAMENTE. O trabalho
        # lento nao pode acontecer neste run: e' justamente enquanto ele roda
        # que os cliques extras entram na fila.
        st.session_state[chave] = True
        st.rerun()

    return travado
