# ---------------------------------------------------------------------------
# base.py — Base declarativa do ORM.
#
# Responsabilidade: expor a classe `Base` que todos os modelos ORM herdam.
# Usa o estilo classico `declarative_base()`, compativel tanto com SQLAlchemy
# 1.4 (ambiente local atual) quanto com 2.0 (deploy). Fica separada do engine
# para evitar import circular (models -> base; engine importa models so na hora
# de criar/migrar).
# ---------------------------------------------------------------------------
from __future__ import annotations

from sqlalchemy.orm import declarative_base

Base = declarative_base()

