"""Constantes regulatorias compartilhadas entre rules_pre, rules_post e
calculations, para evitar duplicacao/acoplamento entre os modulos."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

DATA_INICIO_2021 = date(2021, 1, 1)
LIMIAR_INDIVIDUALIZACAO = Decimal("1000.00")
LIMIAR_RISCO_NAO_COBERTO = Decimal("10000000.00")
LIMIAR_EMISSAO_VALOR_TOTAL_RISCO = Decimal("10000000.00")

# Mesmo esquema de resolucao de caminho usado em src/xml_writer.py: em
# --onefile, os dados ficam em sys._MEIPASS; fora do bundle, __file__ aponta
# para a arvore de codigo-fonte original.
if getattr(sys, "frozen", False):
    _BASE_DIR = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    _BASE_DIR = Path(__file__).resolve().parent.parent

_CAMINHO_COSIF = _BASE_DIR / "assets" / "lista_COSIF_validas.txt"
_CAMINHO_CONGLOMERADOS = _BASE_DIR / "assets" / "lista_codigos_conglomerados.txt"


def _carregar_contas_cosif_validas() -> frozenset[str]:
    linhas = _CAMINHO_COSIF.read_text(encoding="utf-8").splitlines()
    return frozenset(linha.strip() for linha in linhas if linha.strip())


def _carregar_codigos_conglomerados_validos() -> frozenset[str]:
    linhas = _CAMINHO_CONGLOMERADOS.read_text(encoding="utf-8").splitlines()
    return frozenset(linha.strip() for linha in linhas if linha.strip())


CONTAS_COSIF_VALIDAS: frozenset[str] = _carregar_contas_cosif_validas()
CODIGOS_CONGLOMERADOS_VALIDOS: frozenset[str] = _carregar_codigos_conglomerados_validos()
