# ---------------------------------------------------------------------------
# notificacoes/whatsapp.py — canal WhatsApp via Meta Cloud API (Graph).
#
# Envia mensagem de TEMPLATE (necessario fora da janela de 24h). Disponivel
# so se o token/phone_number_id estiverem configurados e a mensagem tiver
# template + destinatario com telefone. Falhas sao logadas e retornam False.
#
# Doc: POST https://graph.facebook.com/v20.0/<PHONE_NUMBER_ID>/messages
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging

import requests

from src.config.settings import get_settings
from src.constantes import CANAL_WHATSAPP
from src.notificacoes.base import Destinatario, Mensagem, Notificador

_log = logging.getLogger("notificacoes")
_API = "https://graph.facebook.com/v20.0"


def _so_digitos(telefone: str) -> str:
    return "".join(ch for ch in telefone if ch.isdigit())


class WhatsappNotificador(Notificador):
    canal = CANAL_WHATSAPP

    def disponivel(self, dest: Destinatario) -> bool:
        wpp = get_settings().whatsapp
        return bool(wpp.configurado and dest.telefone)

    def enviar(self, dest: Destinatario, msg: Mensagem) -> bool:
        if not msg.template_whatsapp:
            # sem template aprovado nao da p/ enviar fora da janela de 24h
            _log.info("[WHATSAPP] mensagem sem template; ignorada (use console/email)")
            return False
        wpp = get_settings().whatsapp
        url = f"{_API}/{wpp.phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {wpp.token}", "Content-Type": "application/json"}
        componentes = []
        if msg.template_params:
            componentes = [{
                "type": "body",
                "parameters": [{"type": "text", "text": p} for p in msg.template_params],
            }]
        payload = {
            "messaging_product": "whatsapp",
            "to": _so_digitos(dest.telefone),
            "type": "template",
            "template": {
                "name": msg.template_whatsapp,
                "language": {"code": wpp.idioma_template},
                "components": componentes,
            },
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=20)
            if resp.status_code // 100 == 2:
                _log.info("[WHATSAPP] enviado para %s", dest.telefone)
                return True
            _log.warning("[WHATSAPP] falha %s: %s", resp.status_code, resp.text[:300])
            return False
        except Exception as exc:  # noqa: BLE001
            _log.warning("[WHATSAPP] erro p/ %s: %s", dest.telefone, exc)
            return False
