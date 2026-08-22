# ---------------------------------------------------------------------------
# Dockerfile — imagem do app Streamlit (deploy futuro, ex.: Render Web Service).
#
# Sem dependencias externas fora do PyPI (graficos self-contained).
# Credenciais (DATABASE_URL, SMTP_*, WHATSAPP_*) vao por ENV VARS no provedor,
# nao em secrets.toml.
#
# TIMEZONE (critico): agendamento.inicio/fim sao hora LOCAL naive comparada com
# datetime.now(). A imagem base roda em UTC -> sem TZ, todo o app fica 3h
# deslocado em producao (slots, "agenda de hoje", janela do job de lembretes).
# Por isso tzdata + TZ abaixo. Ver src/config/settings.py:TIMEZONE_PADRAO.
# ---------------------------------------------------------------------------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8501 \
    TZ=America/Sao_Paulo

WORKDIR /app

# deps de build do psycopg2 + tzdata (a imagem slim nao traz o banco de fusos)
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

# Render injeta $PORT; usa-o se presente.
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true"]
