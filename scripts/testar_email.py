# ---------------------------------------------------------------------------
# scripts/testar_email.py - diagnostico do envio de e-mail (SMTP).
#
#   python -m scripts.testar_email [destino@exemplo.com]
#
# Sem destino, envia para o proprio usuario do SMTP (voce recebe o teste).
#
# Roda em 3 etapas, parando na primeira que falhar, com diagnostico do erro:
#   1) Configuracao presente? (host/porta/usuario/senha/remetente)
#   2) Conexao + STARTTLS + login no servidor
#   3) Envio REAL pela mesma pilha que o app usa (notificacoes.EmailNotificador)
#
# Existe porque o EmailNotificador engole excecoes de proposito (uma falha de
# e-mail nao pode derrubar um agendamento) — aqui a excecao aparece.
# ---------------------------------------------------------------------------
from __future__ import annotations

import smtplib
import socket
import ssl
import sys
from datetime import datetime

from src.config.settings import get_settings
from src.notificacoes.base import Destinatario, Mensagem
from src.notificacoes.email import EmailNotificador


def _diagnostico(exc: Exception) -> str:
    """Traduz a excecao do SMTP para uma acao concreta."""
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return ("LOGIN RECUSADO. No Gmail isto quase sempre e' um destes:\n"
                "   - voce usou a senha NORMAL da conta em vez da 'app password' de 16 digitos\n"
                "   - a verificacao em 2 etapas nao esta ligada (sem ela nao existe app password)\n"
                "   - a app password foi revogada; gere outra")
    if isinstance(exc, (socket.gaierror,)):
        return "HOST NAO RESOLVIDO. Confira smtp.host (Gmail = smtp.gmail.com)."
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return ("TIMEOUT ao conectar. Confira a porta (Gmail = 587 com STARTTLS) "
                "ou se a rede/firewall bloqueia saida SMTP.")
    if isinstance(exc, smtplib.SMTPNotSupportedError):
        return "O servidor nao aceitou STARTTLS nessa porta. Use 587."
    if isinstance(exc, ssl.SSLError):
        return "Erro de TLS. Na porta 465 o protocolo e' SSL direto; este app usa 587/STARTTLS."
    return f"{type(exc).__name__}: {exc}"


def main() -> None:
    cfg = get_settings().smtp
    destino = sys.argv[1] if len(sys.argv) > 1 else cfg.user

    print("=" * 68)
    print("1) CONFIGURACAO")
    print("=" * 68)
    faltando = [nome for nome, val in
                (("host", cfg.host), ("user", cfg.user), ("password", cfg.password))
                if not val]
    print(f"   host      : {cfg.host or '(vazio)'}")
    print(f"   porta     : {cfg.port}")
    print(f"   usuario   : {cfg.user or '(vazio)'}")
    print(f"   senha     : {'(preenchida, %d chars)' % len(cfg.password) if cfg.password else '(VAZIA)'}")
    print(f"   remetente : {cfg.remetente or '(vazio - usara o usuario)'}")
    if faltando:
        print(f"\n   [X] FALTA preencher: {', '.join(faltando)}")
        print("   Preencha o bloco [smtp] em .streamlit/secrets.toml e rode de novo.")
        sys.exit(1)
    if cfg.password and len(cfg.password.replace(" ", "")) != 16:
        print("\n   [!] Aviso: a app password do Gmail tem 16 caracteres. "
              "A sua tem %d — confira se nao colou a senha normal da conta."
              % len(cfg.password.replace(" ", "")))
    print("   [OK] configuracao presente.")

    print()
    print("=" * 68)
    print("2) CONEXAO + LOGIN")
    print("=" * 68)
    try:
        with smtplib.SMTP(cfg.host, cfg.port, timeout=20) as srv:
            srv.starttls()
            srv.login(cfg.user, cfg.password)
        print("   [OK] conectou, STARTTLS e login aceitos.")
    except Exception as exc:  # noqa: BLE001
        print("   [X] FALHOU\n")
        print("   " + _diagnostico(exc).replace("\n", "\n   "))
        sys.exit(1)

    print()
    print("=" * 68)
    print(f"3) ENVIO REAL -> {destino}")
    print("=" * 68)
    agora = datetime.now().strftime("%d/%m/%Y as %H:%M")
    msg = Mensagem(
        assunto=f"Teste de e-mail - {get_settings().salao.nome}",
        corpo=(f"Se voce esta lendo isto, o envio de e-mail do app esta FUNCIONANDO.\n\n"
               f"Enviado em {agora}.\n\n"
               f"A partir de agora o app consegue mandar confirmacao de agendamento, "
               f"lembrete de 1 dia antes e avisos de cancelamento."),
    )
    ok = EmailNotificador().enviar(Destinatario(nome="Teste", email=destino), msg)
    if ok:
        print(f"   [OK] E-MAIL ENVIADO. Confira a caixa de {destino}")
        print("        (veja tambem o spam na primeira vez).")
    else:
        print("   [X] o envio retornou falha — rode com logging para ver o motivo:")
        print("       python -c \"import logging;logging.basicConfig(level=logging.DEBUG)\" ...")
        sys.exit(1)


if __name__ == "__main__":
    main()
