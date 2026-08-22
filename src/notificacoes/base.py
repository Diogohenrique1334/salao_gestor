# ---------------------------------------------------------------------------
# notificacoes/base.py — contratos da camada de notificacao.
#
# Define os tipos compartilhados (Destinatario, Mensagem) e a interface
# Notificador (Strategy). Cada canal (console/email/whatsapp) implementa
# `disponivel` (sabe se pode enviar) e `enviar`.
# ---------------------------------------------------------------------------
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class Destinatario:
    nome: str
    email: Optional[str] = None
    telefone: Optional[str] = None  # E.164 p/ WhatsApp


@dataclass(frozen=True)
class Mensagem:
    """Conteudo a enviar. `corpo`/`assunto` servem email e console; os campos
    de template servem o WhatsApp Cloud API (mensagem fora da janela de 24h)."""
    assunto: str
    corpo: str
    template_whatsapp: Optional[str] = None
    template_params: List[str] = field(default_factory=list)


class Notificador(ABC):
    canal: str = "?"

    @abstractmethod
    def disponivel(self, dest: Destinatario) -> bool:
        """True se este canal esta configurado e o destinatario tem o contato."""

    @abstractmethod
    def enviar(self, dest: Destinatario, msg: Mensagem) -> bool:
        """Envia; retorna True em sucesso. Nao deve levantar excecao."""
