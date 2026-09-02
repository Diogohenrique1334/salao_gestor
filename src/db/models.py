# ---------------------------------------------------------------------------
# models.py — MODELOS ORM (estilo classico, compativel SQLAlchemy 1.4 e 2.0)
#
# Entidades e relacoes do dominio do salao:
#   Cliente 1--N Agendamento N--1 Cabeleireiro
#   Servico 1--N Agendamento
#   Cabeleireiro N--N Servico  (via CabeleireiroServico, que carrega o DESCONTO)
#   Cabeleireiro 1--N HorarioTrabalho (base para gerar slots)
#
# Regra-chave: o desconto especifico de cada cabeleireiro por servico vive em
# CabeleireiroServico (desconto_tipo + desconto_valor), amarrado ao preco_base
# do Servico. O calculo do preco final fica em servicos/precificacao.py.
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.constantes import PAPEL_CLIENTE, STATUS_CONFIRMADO
from src.db.base import Base


class Cliente(Base):
    """Usuario do app. `papel` distingue cliente comum de gestor (admin)."""

    __tablename__ = "cliente"

    id = Column(Integer, primary_key=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(180), nullable=False, unique=True, index=True)
    senha_hash = Column(String(200), nullable=False)
    telefone = Column(String(20), nullable=True)  # E.164 p/ WhatsApp (pode faltar no cadastro)
    data_nascimento = Column(Date, nullable=True)  # base p/ acao de aniversario (nullable: contas antigas/walk-in)
    papel = Column(String(20), nullable=False, default=PAPEL_CLIENTE)
    # conta com papel 'cabeleireiro' aponta para o perfil profissional
    cabeleireiro_id = Column(Integer, ForeignKey("cabeleireiro.id"), nullable=True)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)

    # reset de senha self-service (codigo enviado por e-mail, com validade)
    reset_codigo_hash = Column(String(200), nullable=True)
    reset_expira_em = Column(DateTime, nullable=True)

    agendamentos = relationship("Agendamento", back_populates="cliente")


class Cabeleireiro(Base):
    """Profissional do salao (cadastravel pelo gestor)."""

    __tablename__ = "cabeleireiro"

    id = Column(Integer, primary_key=True)
    nome = Column(String(120), nullable=False)
    telefone = Column(String(20), nullable=True)
    bio = Column(Text, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    # Almoco RECORRENTE (hora local): vale para TODO dia de trabalho, sem
    # precisar bloquear dia a dia. Entra como intervalo "ocupado" no calculo de
    # slots (ver servicos/agenda.py). None/None = sem almoco definido.
    almoco_inicio = Column(Time, nullable=True)
    almoco_fim = Column(Time, nullable=True)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)

    servicos = relationship(
        "CabeleireiroServico", back_populates="cabeleireiro", cascade="all, delete-orphan"
    )
    horarios = relationship(
        "HorarioTrabalho", back_populates="cabeleireiro", cascade="all, delete-orphan"
    )
    bloqueios = relationship(
        "BloqueioAgenda", back_populates="cabeleireiro", cascade="all, delete-orphan"
    )
    agendamentos = relationship("Agendamento", back_populates="cabeleireiro")


class Servico(Base):
    """Servico ofertado (corte, barba, coloracao...) com preco-base e duracao."""

    __tablename__ = "servico"

    id = Column(Integer, primary_key=True)
    nome = Column(String(120), nullable=False)
    duracao_min = Column(Integer, nullable=False, default=30)
    preco_base = Column(Numeric(10, 2), nullable=False, default=0)
    ativo = Column(Boolean, nullable=False, default=True)

    cabeleireiros = relationship(
        "CabeleireiroServico", back_populates="servico", cascade="all, delete-orphan"
    )


class CabeleireiroServico(Base):
    """Vinculo N:N cabeleireiro<->servico, portador do DESCONTO especifico.

    desconto_tipo: 'percentual' (desconto_valor em %) ou 'valor' (em R$).
    desconto_valor: 0 = sem desconto.
    """

    __tablename__ = "cabeleireiro_servico"
    __table_args__ = (
        UniqueConstraint("cabeleireiro_id", "servico_id", name="uq_cabeleireiro_servico"),
    )

    id = Column(Integer, primary_key=True)
    cabeleireiro_id = Column(Integer, ForeignKey("cabeleireiro.id", ondelete="CASCADE"), nullable=False)
    servico_id = Column(Integer, ForeignKey("servico.id", ondelete="CASCADE"), nullable=False)
    desconto_tipo = Column(String(20), nullable=True)         # None = sem desconto
    desconto_valor = Column(Numeric(10, 2), nullable=False, default=0)
    ativo = Column(Boolean, nullable=False, default=True)

    cabeleireiro = relationship("Cabeleireiro", back_populates="servicos")
    servico = relationship("Servico", back_populates="cabeleireiros")


class HorarioTrabalho(Base):
    """Janela de trabalho de um cabeleireiro num dia da semana (base p/ slots)."""

    __tablename__ = "horario_trabalho"

    id = Column(Integer, primary_key=True)
    cabeleireiro_id = Column(Integer, ForeignKey("cabeleireiro.id", ondelete="CASCADE"), nullable=False)
    dia_semana = Column(Integer, nullable=False)  # 0=segunda ... 6=domingo (datetime.weekday())
    hora_inicio = Column(Time, nullable=False)
    hora_fim = Column(Time, nullable=False)

    cabeleireiro = relationship("Cabeleireiro", back_populates="horarios")


class BloqueioAgenda(Base):
    """Periodo em que o cabeleireiro NAO atende (ferias/folga).

    `inicio`/`fim` sao hora LOCAL naive (mesma convencao de agendamento.inicio),
    com `fim` exclusivo. Entra como intervalo "ocupado" no calculo de slots e
    barra novas reservas no periodo. Nao cancela agendamentos pre-existentes.
    """

    __tablename__ = "bloqueio_agenda"

    id = Column(Integer, primary_key=True)
    cabeleireiro_id = Column(Integer, ForeignKey("cabeleireiro.id", ondelete="CASCADE"), nullable=False)
    inicio = Column(DateTime, nullable=False, index=True)
    fim = Column(DateTime, nullable=False)
    motivo = Column(String(120), nullable=True)  # ex.: "Ferias", "Folga"
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)

    cabeleireiro = relationship("Cabeleireiro", back_populates="bloqueios")


class Agendamento(Base):
    """Reserva de um cliente com um cabeleireiro para um servico num horario."""

    __tablename__ = "agendamento"

    id = Column(Integer, primary_key=True)
    # cliente_id e' opcional: agendamento avulso (walk-in) cadastrado pelo gestor
    # nao tem conta -> usa nome_avulso/telefone_avulso.
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=True)
    nome_avulso = Column(String(120), nullable=True)
    telefone_avulso = Column(String(20), nullable=True)
    cabeleireiro_id = Column(Integer, ForeignKey("cabeleireiro.id"), nullable=False)
    servico_id = Column(Integer, ForeignKey("servico.id"), nullable=False)

    inicio = Column(DateTime, nullable=False, index=True)
    fim = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default=STATUS_CONFIRMADO)

    # snapshot do preco no momento da reserva (preco_base - desconto aplicado)
    preco_aplicado = Column(Numeric(10, 2), nullable=False, default=0)
    desconto_aplicado = Column(Numeric(10, 2), nullable=False, default=0)

    canal_confirmacao = Column(String(40), nullable=True)        # ex.: "email,whatsapp"
    lembrete_enviado_em = Column(DateTime, nullable=True)        # idempotencia do job
    confirmado_pelo_cliente_em = Column(DateTime, nullable=True) # roadmap: confirmar presenca
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)

    cliente = relationship("Cliente", back_populates="agendamentos")
    cabeleireiro = relationship("Cabeleireiro", back_populates="agendamentos")
    servico = relationship("Servico")
    nps = relationship(
        "NpsResposta", back_populates="agendamento", uselist=False,
        cascade="all, delete-orphan",
    )


class NpsResposta(Base):
    """Avaliacao NPS (0-10) do cliente sobre um atendimento CONCLUIDO.

    Uma nota por agendamento (UNIQUE). So para agendamento com conta (cliente_id);
    walk-in nao responde in-app. Faixas: promotor 9-10, neutro 7-8, detrator 0-6.
    """

    __tablename__ = "nps_resposta"
    __table_args__ = (
        UniqueConstraint("agendamento_id", name="uq_nps_agendamento"),
    )

    id = Column(Integer, primary_key=True)
    agendamento_id = Column(Integer, ForeignKey("agendamento.id", ondelete="CASCADE"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=False)
    nota = Column(Integer, nullable=False)  # 0 a 10
    comentario = Column(Text, nullable=True)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    agendamento = relationship("Agendamento", back_populates="nps")
