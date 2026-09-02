# ---------------------------------------------------------------------------
# ui/paginas/agendar.py — fluxo de agendamento do cliente.
#
# Passos: escolher cabeleireiro -> servico (mostra preco JA com desconto) ->
# dia -> slot livre -> confirmar. A criacao usa servicos.reservas (regra +
# trava de conflito) e servicos.agenda (slots livres).
# ---------------------------------------------------------------------------
from __future__ import annotations

import streamlit as st

from src.db.engine import sessao
from src.notificacoes import eventos
from src.repositorios import agendamentos as repo_ag
from src.repositorios import cabeleireiros as repo_cab
from src.repositorios import servicos as repo_serv
from src.servicos import agenda, precificacao, reservas
from src.ui.componentes import guards, styles


_CHAVE_CONFIRMADO = "agendamento_confirmado"


def _aviso_telefone(usuario: dict) -> None:
    if not usuario.get("telefone"):
        st.caption("ℹ️ Voce ainda nao cadastrou WhatsApp, a confirmacao por WhatsApp "
                   "depende disso (atualize em 'Meus agendamentos' futuramente).")


def _tela_confirmacao(dados: dict) -> None:
    """Tela dedicada de sucesso — substitui o balao/toast por uma mudanca de tela."""
    st.markdown("## ✅ Agendamento confirmado!")
    st.markdown('<div class="bloco-card">', unsafe_allow_html=True)
    st.markdown(
        f"### {dados['servico']}\n"
        f"**Profissional:** {dados['prof']}  \n"
        f"**Quando:** {dados['inicio'].strftime('%d/%m/%Y às %H:%M')}  \n"
        f"**Valor:** {styles.moeda_br(dados['preco'])}",
    )
    st.markdown("</div>", unsafe_allow_html=True)
    if dados.get("canais"):
        st.caption(f"Enviamos a confirmacao por: {', '.join(dados['canais'])}.")
    st.info("Você pode ver, remarcar ou cancelar em **Meus agendamentos** (no menu ao lado).")
    if st.button("Agendar outro horário", type="primary", use_container_width=True):
        del st.session_state[_CHAVE_CONFIRMADO]
        st.rerun()


def render() -> None:
    styles.aplicar_estilo_base()
    usuario = guards.require_login()

    # se acabou de confirmar, mostra a tela de sucesso e PARA aqui
    if _CHAVE_CONFIRMADO in st.session_state:
        _tela_confirmacao(st.session_state[_CHAVE_CONFIRMADO])
        return

    st.markdown("## 🗓️ Agendar")
    _aviso_telefone(usuario)

    # 1) Cabeleireiro
    with sessao() as db:
        profs = repo_cab.listar(db)  # ativos
    if not profs:
        st.warning("Nenhum cabeleireiro disponivel no momento.")
        return
    styles.titulo_secao("1. Escolha o cabeleireiro")
    prof = st.selectbox("Cabeleireiro", profs, format_func=lambda p: p.nome)

    # 2) Servico oferecido por ele (com preco/desconto)
    with sessao() as db:
        vinculos = repo_serv.listar_vinculos_do_cabeleireiro(db, prof.id, apenas_ativos=True)
        servicos = []
        for v in vinculos:
            s = repo_serv.buscar_por_id(db, v.servico_id)
            if s and s.ativo:
                calc = precificacao.calcular_preco(s.preco_base, v.desconto_tipo, v.desconto_valor)
                servicos.append((s, calc))
    if not servicos:
        st.warning("Este cabeleireiro ainda nao tem servicos configurados.")
        return

    styles.titulo_secao("2. Escolha o servico")

    def _label(item):
        s, calc = item
        preco = styles.moeda_br(calc.preco_final)
        if calc.desconto > 0:
            return f"{s.nome} — {preco} (de {styles.moeda_br(calc.preco_base)}) · {s.duracao_min} min"
        return f"{s.nome} — {preco} · {s.duracao_min} min"

    servico, calc = st.selectbox("Servico", servicos, format_func=_label)
    if calc.desconto > 0:
        st.markdown(
            styles.badge(f"Desconto: {styles.moeda_br(calc.desconto)}",
                         styles.COR_DESTAQUE, styles.COR_SOBRE_DESTAQUE),
            unsafe_allow_html=True,
        )

    # 3) Dia (apenas dias que realmente tem vaga p/ este cabeleireiro+servico)
    styles.titulo_secao("3. Escolha o dia")
    with sessao() as db:
        dias = agenda.proximos_dias_disponiveis(
            db, cabeleireiro_id=prof.id, servico_id=servico.id, max_dias=30
        )
    if not dias:
        st.info("Este cabeleireiro nao tem horarios livres nos proximos dias.")
        return
    dia = st.selectbox("Dia", dias, format_func=styles.formatar_data_br)

    # 4) Slots livres
    styles.titulo_secao("4. Escolha o horario")
    with sessao() as db:
        slots = agenda.horarios_disponiveis(db, cabeleireiro_id=prof.id, dia=dia, servico_id=servico.id)
    if not slots:
        st.info("Sem horarios livres nesse dia.")
        return
    slot = st.selectbox("Horario", slots, format_func=lambda dt: dt.strftime("%H:%M"))

    # 5) Confirmar
    st.divider()
    resumo = (f"**{servico.nome}** com **{prof.nome}** em "
              f"**{slot.strftime('%d/%m/%Y às %H:%M')}** — total **{styles.moeda_br(calc.preco_final)}**")
    st.markdown(resumo)
    if st.button("Confirmar agendamento", type="primary", use_container_width=True):
        try:
            with sessao() as db:
                ag = reservas.criar_reserva(
                    db, cliente_id=usuario["id"], cabeleireiro_id=prof.id,
                    servico_id=servico.id, inicio=slot,
                )
                canais = eventos.enviar_confirmacao(db, ag)
                repo_ag.marcar_canal_confirmacao(db, ag.id, ",".join(canais))
            # guarda os dados e troca para a tela de confirmacao (sem balao)
            st.session_state[_CHAVE_CONFIRMADO] = {
                "servico": servico.nome, "prof": prof.nome,
                "inicio": slot, "preco": calc.preco_final, "canais": canais,
            }
            st.rerun()
        except reservas.SlotIndisponivel:
            st.error("Ops, esse horario acabou de ser ocupado. Escolha outro.")
        except reservas.HorarioBloqueado:
            st.error("Este cabeleireiro bloqueou a agenda nesse periodo. Escolha outro dia.")
        except reservas.ServicoNaoOferecido:
            st.error("Este servico nao esta mais disponivel com este cabeleireiro.")
