# ---------------------------------------------------------------------------
# settings.py — CAMADA DE CONFIGURACAO
#
# Responsabilidade: ler credenciais/parametros de um unico lugar e entregar
# objetos tipados ao resto do app. Funciona tanto sob `streamlit run` quanto
# em scripts/CLI (ex.: jobs de lembrete).
#
# Ordem de resolucao de cada valor:
#   1) variavel de ambiente (ideal p/ deploy: Render, GitHub Actions)
#   2) .streamlit/secrets.toml (ideal p/ dev local)
#   3) default (quando houver)
#
# Saida: get_settings() -> AppSettings (cacheado).
# ---------------------------------------------------------------------------
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Optional

# Fuso em que o salao opera. As datas de agendamento sao hora LOCAL naive (ver
# CLAUDE.md), entao o PROCESSO precisa rodar neste fuso. aplicar_timezone()
# escreve este valor no TZ do processo (cobre Streamlit Cloud/qualquer host);
# no Docker (Render) o Dockerfile ja fixa TZ+tzdata de forma redundante.
TIMEZONE_PADRAO = "America/Sao_Paulo"

# Valor publico usado como fallback em dev. Ele assina o cookie de sessao —
# em producao, quem conhece este valor FORJA o token de qualquer usuario
# (inclusive o gestor). Gere um proprio: python -m scripts.gerar_segredo
SESSION_SECRET_PADRAO = "dev-secret"


# FOTOGRAFIA do ambiente, tirada na importacao do modulo.
#
# Motivo: ao ser lido, o `st.secrets` EXPORTA as chaves de TOPO do secrets.toml
# para dentro de os.environ, sobrescrevendo variaveis de ambiente de verdade.
# Como get_settings() resolve `database_url` antes de `session_secret`, o
# os.environ chegava contaminado e o secrets.toml vencia a env var — o inverso
# da precedencia documentada acima.
#
# LIMITE CONHECIDO: sob `streamlit run`, o proprio Streamlit carrega os secrets
# no bootstrap do servidor, ANTES deste modulo ser importado — entao a
# fotografia ja nasce contaminada e, para chaves de TOPO presentes nos dois
# lugares, o secrets.toml continua vencendo. Isso NAO afeta producao (Render
# roda so com env vars, sem secrets.toml) nem os jobs CLI. Em dev, para testar
# um override por env var, remova a chave do secrets.toml.
_ENV_REAL = dict(os.environ)


def _secrets() -> dict:
    """Le .streamlit/secrets.toml de forma tolerante (sem exigir Streamlit)."""
    try:
        import streamlit as st  # import tardio: CLI nao precisa do Streamlit
        # st.secrets se comporta como dict; converte para dict puro.
        return dict(st.secrets)
    except Exception:
        return {}


def _get(env_name: str, *path: str, default: Optional[Any] = None) -> Optional[Any]:
    """Resolve um valor por env var (env_name) ou caminho no secrets.toml.

    O caminho e' percorrido por indexacao direta (nao por isinstance(dict)):
    st.secrets devolve o topo como dict, mas cada SECAO aninhada vem como um
    AttrDict do Streamlit, que nao e' `dict`. Testar o tipo fazia toda seção
    ([gestor], [smtp], [whatsapp], [salao]) cair silenciosamente no default.
    """
    if env_name in _ENV_REAL:            # env var de verdade (ver _ENV_REAL)
        return _ENV_REAL[env_name]
    node: Any = _secrets()
    for key in path:
        try:
            node = node[key]
        except (KeyError, IndexError, TypeError):
            return default
    return node if node is not None else default


@dataclass(frozen=True)
class SalaoSettings:
    """Identidade do salao: aparece nas mensagens ao cliente e no titulo do app.

    Sem isto os e-mails saem com placeholder ("Salao XYZ") — e' o primeiro
    valor a configurar ao entregar o app para um salao novo.
    """

    nome: str
    timezone: str = TIMEZONE_PADRAO


@dataclass(frozen=True)
class GestorSettings:
    email: str
    senha: str


@dataclass(frozen=True)
class SmtpSettings:
    host: str
    port: int
    user: str
    password: str
    remetente: str

    @property
    def configurado(self) -> bool:
        return bool(self.host and self.user and self.password)


@dataclass(frozen=True)
class WhatsappSettings:
    token: str
    phone_number_id: str
    template_confirmacao: str
    template_lembrete: str
    idioma_template: str

    @property
    def configurado(self) -> bool:
        return bool(self.token and self.phone_number_id)


@dataclass(frozen=True)
class AppSettings:
    database_url: str
    session_secret: str
    salao: SalaoSettings
    gestor: GestorSettings
    smtp: SmtpSettings
    whatsapp: WhatsappSettings

    @property
    def db_configurado(self) -> bool:
        return bool(self.database_url)

    @property
    def session_secret_inseguro(self) -> bool:
        """True se o cookie de sessao esta assinado com o segredo publico.

        Nesse estado qualquer pessoa forja o token de qualquer usuario. Checado
        no boot (app.py) e no seed para nao passar batido no deploy.
        """
        return self.session_secret == SESSION_SECRET_PADRAO


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Monta e cacheia as configuracoes do app."""
    return AppSettings(
        database_url=_get("DATABASE_URL", "database_url", default="") or "",
        session_secret=(
            _get("SESSION_SECRET", "session_secret", default=SESSION_SECRET_PADRAO)
            or SESSION_SECRET_PADRAO
        ),
        salao=SalaoSettings(
            nome=_get("SALAO_NOME", "salao", "nome", default="Salao") or "Salao",
            # Fuso em que o SALAO opera — chave dedicada, NAO a env generica `TZ`
            # (que o host define, quase sempre UTC). aplicar_timezone() e' quem
            # ESCREVE esse valor no TZ do processo.
            timezone=_get("SALAO_TIMEZONE", "salao", "timezone", default=TIMEZONE_PADRAO) or TIMEZONE_PADRAO,
        ),
        gestor=GestorSettings(
            email=_get("GESTOR_EMAIL", "gestor", "email", default="renan@recortes.com") or "",
            senha=_get("GESTOR_SENHA", "gestor", "senha", default="123456") or "",
        ),
        smtp=SmtpSettings(
            host=_get("SMTP_HOST", "smtp", "host", default="") or "",
            port=int(_get("SMTP_PORT", "smtp", "port", default=587) or 587),
            user=_get("SMTP_USER", "smtp", "user", default="") or "",
            password=_get("SMTP_PASSWORD", "smtp", "password", default="") or "",
            remetente=_get("SMTP_REMETENTE", "smtp", "remetente", default="") or "",
        ),
        whatsapp=WhatsappSettings(
            token=_get("WHATSAPP_TOKEN", "whatsapp", "token", default="") or "",
            phone_number_id=_get("WHATSAPP_PHONE_NUMBER_ID", "whatsapp", "phone_number_id", default="") or "",
            template_confirmacao=_get("WHATSAPP_TEMPLATE_CONFIRMACAO", "whatsapp", "template_confirmacao", default="confirmacao_agendamento") or "",
            template_lembrete=_get("WHATSAPP_TEMPLATE_LEMBRETE", "whatsapp", "template_lembrete", default="lembrete_agendamento") or "",
            idioma_template=_get("WHATSAPP_IDIOMA_TEMPLATE", "whatsapp", "idioma_template", default="pt_BR") or "pt_BR",
        ),
    )


def aplicar_timezone() -> None:
    """Fixa o fuso do PROCESSO no timezone do salao (idempotente).

    As datas de agendamento sao hora local naive comparadas com datetime.now(),
    entao o processo TEM que rodar no fuso do salao. Em Docker (Render) isso vem
    do Dockerfile (TZ + tzdata). Mas hosts como o Streamlit Cloud rodam em UTC e
    NAO usam o Dockerfile — sem isto o app fica 3h deslocado sem dar erro.
    Chamar no boot (app.py) e nos jobs, antes de qualquer datetime.now().

    time.tzset() so existe em Unix; no Windows (dev) e' no-op — a hora local do
    SO ja vale, entao nao ha regressao no ambiente local.
    """
    tz = get_settings().salao.timezone
    if not tz:
        return
    os.environ["TZ"] = tz
    if hasattr(time, "tzset"):
        time.tzset()
