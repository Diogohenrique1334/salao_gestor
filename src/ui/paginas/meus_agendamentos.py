# ---------------------------------------------------------------------------
# ui/paginas/meus_agendamentos.py — autoatendimento do cliente.
#
# Lista os agendamentos do cliente, permite CANCELAR e REAGENDAR (com novo
# slot livre) e atualizar o WhatsApp. Usa servicos.reservas (regras) +
# servicos.agenda (slots) + notificacoes.eventos (avisos).
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import datetime

import streamlit as st

from src.constantes import STATUS_ATIVOS, STATUS_CONCLUIDO
from src.db.engine import sessao
from src.repositorios import agendamentos as repo_ag
from src.repositorios import cabeleireiros as repo_cab
from src.repositorios import clientes as repo_cli
from src.repositorios import nps as repo_nps
from src.repositorios import servicos as repo_serv
from src.servicos import agenda, agendamento_fluxo, nps, reservas
from src.ui.componentes import acao_unica, guards, styles


def _atualizar_whatsapp(usuario: dict) -> None:
    styles.titulo_secao("Meu WhatsApp")
    with st.form("form_tel"):
        tel = st.text_input("WhatsApp (com DDD)", value=usuario.get("telefone") or "",
                            placeholder="+55 11 99999-9999")
        if st.form_submit_button("Salvar WhatsApp"):
            with sessao() as db:
                repo_cli.atualizar_telefone(db, usuario["id"], tel)
            st.session_state["usuario"]["telefone"] = tel.strip() or None
            st.success("WhatsApp atualizado.")
            st.rerun()


def _bloco_reagendar(usuario: dict, ag) -> None:
    with sessao() as db:
        dias = agenda.proximos_dias_disponiveis(
            db, cabeleireiro_id=ag.cabeleireiro_id, servico_id=ag.servico_id, max_dias=30
        )
    if not dias:
        st.info("Sem dias com horario livre para este cabeleireiro.")
        return
    novo_dia = st.selectbox("Novo dia", dias, format_func=styles.formatar_data_br, key=f"rd_{ag.id}")
    with sessao() as db:
        slots = agenda.horarios_disponiveis(
            db, cabeleireiro_id=ag.cabeleireiro_id, dia=novo_dia, servico_id=ag.servico_id
        )
    if not slots:
        st.info("Sem horarios livres nesse dia.")
        return
    novo_slot = st.selectbox("Novo horario", slots, format_func=lambda dt: dt.strftime("%H:%M"),
                             key=f"rs_{ag.id}")
    nome_acao = f"reagendar_{ag.id}"
    if acao_unica.botao("Confirmar reagendamento", nome=nome_acao,
                        rotulo_ocupado="Remarcando...", type="primary"):
        ok = False
        try:
            # o evento de REMARCACAO (de->para) e' proprio: reaproveitar a
            # confirmacao faria o cliente ler "agendamento confirmado" sem
            # perceber que o horario mudou. Avisa o profissional tambem.
            agendamento_fluxo.reagendar_e_notificar(
                agendamento_id=ag.id, cliente_id=usuario["id"], novo_inicio=novo_slot
            )
            ok = True
        except reservas.SlotIndisponivel:
            st.error("Esse horario acabou de ser ocupado. Tente outro.")
        except reservas.HorarioBloqueado:
            st.error("A agenda esta bloqueada nesse periodo. Escolha outro dia.")
        except reservas.NaoAutorizado:
            st.error("Voce nao pode remarcar este agendamento.")
        except Exception:  # noqa: BLE001 - nunca deixar o botao travado
            st.error("Nao conseguimos remarcar agora. Tente novamente em instantes.")
        finally:
            acao_unica.liberar(nome_acao)
        if ok:
            st.toast("Reagendado com sucesso!")
            st.rerun()


def _bloco_nps(usuario: dict, ag, resposta) -> None:
    """Coleta/exibe o NPS de um atendimento concluido."""
    if resposta is not None:
        st.caption(f"⭐ Voce avaliou este atendimento: nota {resposta.nota}/10.")
        return
    with st.expander("Avaliar atendimento"):
        with st.form(f"nps_{ag.id}"):
            nota = st.slider("De 0 a 10, o quanto recomendaria?", 0, 10, 8, key=f"npsn_{ag.id}")
            comentario = st.text_area("Comentario (opcional)", key=f"npsc_{ag.id}", height=70)
            if st.form_submit_button("Enviar avaliacao", type="primary"):
                try:
                    with sessao() as db:
                        nps.registrar(db, agendamento_id=ag.id, cliente_id=usuario["id"],
                                      nota=int(nota), comentario=(comentario or None))
                    st.success("Obrigado pela avaliacao!")
                    st.rerun()
                except nps.NpsDuplicado:
                    st.warning("Este atendimento ja foi avaliado.")
                except nps.NpsInvalido:
                    st.error("Nao foi possivel registrar a avaliacao.")


def _card_agendamento(usuario: dict, ag, resposta_nps=None) -> None:
    with sessao() as db:
        prof = repo_cab.buscar_por_id(db, ag.cabeleireiro_id)
        servico = repo_serv.buscar_por_id(db, ag.servico_id)
    futuro = ag.inicio >= datetime.now()
    editavel = ag.status in STATUS_ATIVOS and futuro

    st.markdown('<div class="bloco-card">', unsafe_allow_html=True)
    st.markdown(
        f"**{servico.nome if servico else '-'}** com **{prof.nome if prof else '-'}**  "
        f"{styles.badge_status(ag.status)}<br>"
        f"🗓️ {ag.inicio.strftime('%d/%m/%Y às %H:%M')} · 💰 {styles.moeda_br(ag.preco_aplicado)}",
        unsafe_allow_html=True,
    )
    if editavel:
        col1, col2 = st.columns([1, 1])
        nome_acao = f"cancelar_{ag.id}"
        with col1:
            if acao_unica.botao("Cancelar", nome=nome_acao, rotulo_ocupado="Cancelando..."):
                ok = False
                try:
                    agendamento_fluxo.cancelar_e_notificar(
                        agendamento_id=ag.id, cliente_id=usuario["id"]
                    )
                    ok = True
                except reservas.CancelamentoInvalido:
                    st.warning("Este agendamento nao esta mais ativo.")
                except reservas.NaoAutorizado:
                    st.error("Voce nao pode cancelar este agendamento.")
                except Exception:  # noqa: BLE001 - nunca deixar o botao travado
                    st.error("Nao conseguimos cancelar agora. Tente novamente em instantes.")
                finally:
                    acao_unica.liberar(nome_acao)
                if ok:
                    st.toast("Agendamento cancelado.")
                    st.rerun()
        with col2.expander("Reagendar"):
            _bloco_reagendar(usuario, ag)
    elif ag.status == STATUS_CONCLUIDO:
        _bloco_nps(usuario, ag, resposta_nps)
    st.markdown("</div>", unsafe_allow_html=True)


def render() -> None:
    styles.aplicar_estilo_base()
    usuario = guards.require_login()
    st.markdown("## 📋 Meus agendamentos")

    _atualizar_whatsapp(usuario)

    styles.titulo_secao("Agendamentos")
    with sessao() as db:
        ags = repo_ag.listar_por_cliente(db, usuario["id"])
        respostas = {r.agendamento_id: r for r in repo_nps.listar_por_cliente(db, usuario["id"])}
    if not ags:
        st.caption("Voce ainda nao tem agendamentos. Use a pagina **Agendar**.")
        return
    for ag in ags:
        _card_agendamento(usuario, ag, resposta_nps=respostas.get(ag.id))
