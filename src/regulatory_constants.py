"""Constantes regulatorias compartilhadas entre rules_pre, rules_post e
calculations, para evitar duplicacao/acoplamento entre os modulos."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

DATA_INICIO_2021 = date(2021, 1, 1)
LIMIAR_INDIVIDUALIZACAO = Decimal("1000.00")
LIMIAR_RISCO_NAO_COBERTO = Decimal("10000000.00")
LIMIAR_EMISSAO_VALOR_TOTAL_RISCO = Decimal("10000000.00")
