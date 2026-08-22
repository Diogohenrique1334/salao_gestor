# ---------------------------------------------------------------------------
# notificacoes/dispatcher.py — orquestra o envio pelos canais DO EVENTO.
#
# Nao envia mais "por todo canal configurado": consulta politica.canais_de(evento)
# e tenta apenas os canais previstos para aquele evento (ver politica.py). Cada
# notificador ainda decide se esta disponivel (credencial + contato do
# destinatario), e sempre registra no console p/ rastreio.
#
# Tolerante a falha: o que falhar nao interrompe os demais. Retorna a lista de
# canais que tiveram sucesso (p/ gravar em agendamento.canal_confirmacao). Se
# nada real saiu, retorna ['console'].
# ---------------------------------------------------------------------------
from __future__ import annotations

from typing import Callable, Dict, List

from src.constantes import CANAL_CONSOLE, CANAL_EMAIL, CANAL_WHATSAPP
from src.notificacoes import politica
from src.notificacoes.base import Destinatario, Mensagem, Notificador
from src.notificacoes.console import ConsoleNotificador
from src.notificacoes.email import EmailNotificador
from src.notificacoes.whatsapp import WhatsappNotificador

# Registro canal -> fabrica do notificador. Um canal listado na politica mas
# ausente aqui (ex.: CANAL_SMS, ainda nao implementado) e' simplesmente ignorado.
_NOTIFICADORES: Dict[str, Callable[[], Notificador]] = {
    CANAL_EMAIL: EmailNotificador,
    CANAL_WHATSAPP: WhatsappNotificador,
}


def enviar(dest: Destinatario, msg: Mensagem, evento: str) -> List[str]:
    """Envia `msg` a `dest` pelos canais que a politica define para `evento`."""
    enviados: List[str] = []
    for canal in politica.canais_de(evento):
        fabrica = _NOTIFICADORES.get(canal)
        if fabrica is None:
            continue  # canal previsto na politica, sem implementacao ainda
        notif = fabrica()
        if notif.disponivel(dest) and notif.enviar(dest, msg):
            enviados.append(notif.canal)

    # rastreio (sempre): em dev substitui os canais reais; em prod vira log
    ConsoleNotificador().enviar(dest, msg)

    if not enviados:
        enviados.append(CANAL_CONSOLE)
    return enviados
