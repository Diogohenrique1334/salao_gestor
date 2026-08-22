# ---------------------------------------------------------------------------
# notificacoes/console.py — canal de DEV: apenas registra a mensagem no log.
#
# Sempre disponivel. Garante que o fluxo funciona de ponta a ponta mesmo sem
# credenciais de e-mail/WhatsApp configuradas.
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging

from src.constantes import CANAL_CONSOLE
from src.notificacoes.base import Destinatario, Mensagem, Notificador

_log = logging.getLogger("notificacoes")


class ConsoleNotificador(Notificador):
    canal = CANAL_CONSOLE

    def disponivel(self, dest: Destinatario) -> bool:
        return True

    def enviar(self, dest: Destinatario, msg: Mensagem) -> bool:
        _log.info(
            "[CONSOLE] para=%s <%s / %s>\n  ASSUNTO: %s\n  CORPO: %s",
            dest.nome, dest.email, dest.telefone, msg.assunto, msg.corpo.replace("\n", " | "),
        )
        print(f"\n--- NOTIFICACAO (console) ---\nPara: {dest.nome}\n{msg.assunto}\n{msg.corpo}\n-----------------------------\n")
        return True
