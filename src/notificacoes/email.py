# ---------------------------------------------------------------------------
# notificacoes/email.py — canal de e-mail via SMTP do Gmail (app password).
#
# Disponivel apenas se o SMTP estiver configurado (settings.smtp) e o
# destinatario tiver e-mail. Falhas sao logadas e retornam False (nunca
# levantam), para nao derrubar o fluxo de agendamento.
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from src.config.settings import get_settings
from src.constantes import CANAL_EMAIL
from src.notificacoes.base import Destinatario, Mensagem, Notificador

_log = logging.getLogger("notificacoes")


class EmailNotificador(Notificador):
    canal = CANAL_EMAIL

    def disponivel(self, dest: Destinatario) -> bool:
        return bool(get_settings().smtp.configurado and dest.email)

    def enviar(self, dest: Destinatario, msg: Mensagem) -> bool:
        cfg = get_settings().smtp
        try:
            mime = MIMEText(msg.corpo, "plain", "utf-8")
            mime["Subject"] = msg.assunto
            mime["From"] = cfg.remetente or cfg.user
            mime["To"] = dest.email
            with smtplib.SMTP(cfg.host, cfg.port, timeout=20) as servidor:
                servidor.starttls()
                servidor.login(cfg.user, cfg.password)
                servidor.sendmail(cfg.user, [dest.email], mime.as_string())
            _log.info("[EMAIL] enviado para %s", dest.email)
            return True
        except Exception as exc:  # noqa: BLE001
            _log.warning("[EMAIL] falha p/ %s: %s", dest.email, exc)
            return False
