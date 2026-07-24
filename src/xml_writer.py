"""Construcao do XML e validacao contra o XSD 06/2025 (Fase 7).

Ver docs/plano_conversor_dro_5050_simples.md secao 20.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

from lxml import etree

from src.models import Contabilizacao, EventoAgrupado, EventoConsolidado

# Quando empacotado com PyInstaller (--onefile), os arquivos de dados sao
# extraidos para uma pasta temporaria exposta em sys._MEIPASS; __file__ nao
# aponta mais para a arvore de codigo-fonte original. Em execucao normal
# (nao empacotada), sys.frozen nao existe e cai no calculo relativo usual.
if getattr(sys, "frozen", False):
    _BASE_DIR = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    _BASE_DIR = Path(__file__).resolve().parent.parent

RESOURCES_DIR = _BASE_DIR / "assets" / "fonte"
XSD_PATH = RESOURCES_DIR / "dro_5050_2025_06.xsd"


def _formatar_decimal(valor: Decimal) -> str:
    return f"{valor:.2f}"


def construir_xml(
    *,
    cabecalho: dict[str, object],
    eventos_individualizados: list[EventoAgrupado],
    eventos_consolidados: dict[str, EventoConsolidado],
    sistemas: dict[str, str],
    contas: dict[str, str],
) -> "etree._Element":
    documento = etree.Element("documento")
    documento.set("codigoDocumento", str(cabecalho["codigoDocumento"]))
    documento.set("dataBase", str(cabecalho["dataBase"]))
    documento.set("codigoConglomerado", str(cabecalho["codigoConglomerado"]))
    documento.set("cnpj", str(cabecalho["cnpj"]))
    documento.set("tipoRemessa", str(cabecalho["tipoRemessa"]))
    documento.set(
        "opcaoPorProvisaoAcumulada",
        str(cabecalho["opcaoPorProvisaoAcumulada"]),
    )

    eventos_el = etree.SubElement(documento, "eventosIndividualizados")
    for evento in eventos_individualizados:
        _adicionar_evento(eventos_el, evento)

    consolidados_el = etree.SubElement(documento, "eventosConsolidados")
    for consolidado in eventos_consolidados.values():
        _adicionar_evento_consolidado(consolidados_el, consolidado)

    sistemas_el = etree.SubElement(documento, "sistemasOrigem")
    for codigo, nome in sistemas.items():
        sistema_el = etree.SubElement(sistemas_el, "sistema")
        sistema_el.set("codigoSistema", codigo)
        sistema_el.set("nomeSistema", nome)

    contas_el = etree.SubElement(documento, "contasSubtitulosInternos")
    for codigo, nome in contas.items():
        conta_el = etree.SubElement(contas_el, "conta")
        conta_el.set("codigoConta", codigo)
        conta_el.set("nomeConta", nome)

    return documento


def _adicionar_evento(pai: "etree._Element", evento: EventoAgrupado) -> None:
    evento_el = etree.SubElement(pai, "evento")
    evento_el.set("idEvento", evento.id_evento)
    evento_el.set(
        "categoriaNivel1", str(evento.valor_evento("categoriaNivel1"))
    )

    categoria2 = evento.valor_evento("categoriaNivel2")
    if categoria2 is not None:
        evento_el.set("categoriaNivel2", str(categoria2))

    evento_el.set("tipoAvaliacao", str(evento.valor_evento("tipoAvaliacao")))
    evento_el.set(
        "unidadeNegocio", str(evento.valor_evento("unidadeNegocio"))
    )

    descoberta = evento.valor_evento("dataDescoberta")
    if descoberta is not None:
        evento_el.set("dataDescoberta", descoberta.isoformat())

    evento_el.set(
        "dataOcorrencia", evento.valor_evento("dataOcorrencia").isoformat()
    )
    evento_el.set(
        "totalPerdaEfetiva", _formatar_decimal(evento.total_perda_efetiva)
    )
    evento_el.set("totalProvisao", _formatar_decimal(evento.total_provisao))
    evento_el.set(
        "totalRecuperado", _formatar_decimal(evento.total_recuperado)
    )
    if evento.valor_total_risco is not None:
        evento_el.set(
            "valorTotalRisco", _formatar_decimal(evento.valor_total_risco)
        )

    evento_el.set(
        "naturezaContingencia",
        str(evento.valor_evento("naturezaContingencia")),
    )
    evento_el.set(
        "codSistemaOrigem", str(evento.valor_evento("codSistemaOrigem"))
    )
    evento_el.set(
        "codigoEventoOrigem", str(evento.valor_evento("codigoEventoOrigem"))
    )

    for campo_evento, campo_xml in (
        ("descricaoEvento", "descricaoEvento"),
        ("riscoAssociado", "riscoAssociado"),
        ("ligadoRiscoSocioAmbiental", "ligadoRiscoSocioAmbiental"),
        ("ligadoRiscoCibernetico", "ligadoRiscoCibernetico"),
        ("negocioDescontinuado", "negocioDescontinuado"),
    ):
        valor = evento.valor_evento(campo_evento)
        if valor is not None:
            evento_el.set(campo_xml, str(valor))

    evento_el.set("idBacen", str(evento.valor_evento("idBacen")))

    if evento.probabilidades:
        probs_el = etree.SubElement(evento_el, "probabilidadesPerdas")
        for probabilidade in evento.probabilidades:
            prob_el = etree.SubElement(probs_el, "probabilidadePerda")
            prob_el.set("probabilidade", probabilidade.codigo)
            prob_el.set(
                "valorRisco", _formatar_decimal(probabilidade.valor_risco)
            )

    if evento.contabilizacoes:
        contabilizacoes_el = etree.SubElement(evento_el, "contabilizacoes")
        for contabilizacao in evento.contabilizacoes:
            _adicionar_contabilizacao(contabilizacoes_el, contabilizacao)


def _adicionar_contabilizacao(
    pai: "etree._Element", contabilizacao: Contabilizacao
) -> None:
    el = etree.SubElement(pai, "contabilizacao")
    el.set(
        "dataContabilizacao",
        contabilizacao.data_contabilizacao.isoformat(),
    )
    if contabilizacao.conta_debito is not None:
        el.set("contaBalAnaliticoDebito", str(contabilizacao.conta_debito))
    if contabilizacao.conta_credito is not None:
        el.set("contaBalAnaliticoCredito", str(contabilizacao.conta_credito))
    if contabilizacao.conta_cosif_debito is not None:
        el.set("contaCosifDebito", str(contabilizacao.conta_cosif_debito))
    if contabilizacao.conta_cosif_credito is not None:
        el.set("contaCosifCredito", str(contabilizacao.conta_cosif_credito))

    el.set(
        "valorPerdaEfetiva",
        _formatar_decimal(contabilizacao.valor_perda_efetiva),
    )
    if contabilizacao.valor_provisao is not None:
        el.set(
            "valorProvisao",
            _formatar_decimal(contabilizacao.valor_provisao),
        )
    if contabilizacao.valor_recuperacao is not None:
        el.set(
            "valorRecuperacao",
            _formatar_decimal(contabilizacao.valor_recuperacao),
        )
    if contabilizacao.fonte_recuperacao is not None:
        el.set("fonteRecuperacao", str(contabilizacao.fonte_recuperacao))


def _adicionar_evento_consolidado(
    pai: "etree._Element", consolidado: EventoConsolidado
) -> None:
    el = etree.SubElement(pai, "eventoConsolidado")
    el.set("categoriaNivel1Consol", consolidado.categoria_nivel1)
    el.set("numEventosTotalConsol", str(consolidado.num_eventos_total))
    el.set(
        "numEventosSemestreConsol", str(consolidado.num_eventos_semestre)
    )
    el.set(
        "perdaEfetivaTotalConsol",
        _formatar_decimal(consolidado.perda_efetiva_total),
    )
    el.set(
        "perdaEfetivaSemestreConsol",
        _formatar_decimal(consolidado.perda_efetiva_semestre),
    )
    el.set(
        "provisaoTotalConsol", _formatar_decimal(consolidado.provisao_total)
    )
    el.set(
        "provisaoSemestreConsol",
        _formatar_decimal(consolidado.provisao_semestre),
    )


def serializar_xml(documento: "etree._Element") -> bytes:
    return etree.tostring(
        documento,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    )


def salvar_xml(documento: "etree._Element", caminho: Path) -> None:
    """Grava o XML de forma atomica: escreve num arquivo temporario e so
    substitui o nome final com Path.replace() (rename atomico do SO)
    depois que a escrita inteira tiver sucesso -- uma falha no meio da
    gravacao (disco cheio etc.) nunca deixa um arquivo parcial no nome
    final. O temporario e removido se a escrita falhar."""

    if caminho.exists():
        raise FileExistsError(
            f"Arquivo já existe, não será sobrescrito: {caminho}"
        )
    caminho_temporario = caminho.with_name(caminho.name + ".tmp")
    try:
        caminho_temporario.write_bytes(serializar_xml(documento))
        caminho_temporario.replace(caminho)
    except OSError:
        caminho_temporario.unlink(missing_ok=True)
        raise


def validar_contra_xsd(documento: "etree._Element") -> list[str]:
    """Retorna as mensagens de erro; lista vazia quando o XML e valido."""

    schema_doc = etree.parse(str(XSD_PATH))
    schema = etree.XMLSchema(schema_doc)
    if schema.validate(documento):
        return []
    return [str(erro) for erro in schema.error_log]
