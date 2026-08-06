"""Validacao do XML contra o XSD 06/2025.

Este modulo concentra a localizacao, carga e execucao do schema. O escritor
XML permanece responsavel apenas por construir, serializar e gravar o XML.
"""

from __future__ import annotations

import sys
from pathlib import Path

from lxml import etree

from src.models import (
    ETAPA_XSD,
    Ocorrencia,
    TIPO_ERRO_IMPEDITIVO,
)

if getattr(sys, "frozen", False):
    _BASE_DIR = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    _BASE_DIR = Path(__file__).resolve().parent.parent

RESOURCES_DIR = _BASE_DIR / "assets" / "fonte"
XSD_PATH = RESOURCES_DIR / "dro_5050_2025_06.xsd"


class ErroTecnicoXSD(RuntimeError):
    """Falha ao localizar, ler ou compilar o XSD oficial."""

    def __init__(
        self,
        mensagem: str,
        *,
        caminho_xsd: Path | None = None,
        causa: Exception | None = None,
    ) -> None:
        super().__init__(mensagem)
        self.caminho_xsd = caminho_xsd
        self.causa = causa


def validar_xml_contra_xsd(
    documento: "etree._Element",
) -> tuple[Ocorrencia, ...]:
    """Valida o XML e traduz rejeicoes do schema para XSD-001."""

    try:
        schema_doc = etree.parse(str(XSD_PATH))
        schema = etree.XMLSchema(schema_doc)
    except (OSError, etree.LxmlError) as exc:
        raise ErroTecnicoXSD(
            str(exc), caminho_xsd=XSD_PATH, causa=exc
        ) from exc
    if schema.validate(documento):
        return ()
    return tuple(
        Ocorrencia(
            etapa=ETAPA_XSD,
            tipo=TIPO_ERRO_IMPEDITIVO,
            codigo="XSD-001",
            descricao="XML incompat\u00edvel com o XSD 06/2025.",
            detalhe=str(erro),
        )
        for erro in schema.error_log
    )
