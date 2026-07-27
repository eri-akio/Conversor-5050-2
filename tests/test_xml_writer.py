"""Testes da Fase 7: construcao do XML e validacao XSD
(src/xml_writer.py)."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from src.calculations import (
    construir_mapa_contas,
    construir_mapa_sistemas,
    montar_evento,
    normalizar_linha_base,
)
from src.reader import BASE_COLUNAS
from src.rules_post import consolidar_eventos
from src.rules_pre import classificar_evento
from src.xml_writer import (
    construir_xml,
    salvar_xml,
    serializar_xml,
    validar_contra_xsd,
)

CABECALHO_VALIDO = {
    "codigoDocumento": "5050",
    "dataBase": "2025-06",
    "codigoConglomerado": "C1234567",
    "cnpj": "12345678",
    "tipoRemessa": "I",
    "opcaoPorProvisaoAcumulada": "S",
}

CAMPOS_EVENTO_PADRAO = {
    "categoriaNivel1": "1",
    "categoriaNivel2": "11",
    "tipoAvaliacao": "NA",
    "unidadeNegocio": "1",
    "dataOcorrencia": "2025-06-10",
    "dataDescoberta": "2025-06-10",
    "naturezaContingencia": "NA",
    "codSistemaOrigem": "SIS1",
    "nomeSistema": "Sistema Um",
    "codigoEventoOrigem": "COD1",
    "riscoAssociado": "NA",
    "ligadoRiscoSocioAmbiental": "N",
    "ligadoRiscoCibernetico": "N",
    "idBacen": "Z0000001",
}


def _linha(numero_linha: int, **sobrescritas: object):
    valores_por_coluna = dict(CAMPOS_EVENTO_PADRAO)
    valores_por_coluna.update(sobrescritas)
    valores = tuple(valores_por_coluna.get(coluna) for coluna in BASE_COLUNAS)
    return normalizar_linha_base(numero_linha, BASE_COLUNAS, valores)


def _montar_documento_valido():
    linhas_individualizado = [
        _linha(
            2,
            idEvento="EVT1",
            categoriaNivel1="1",
            categoriaNivel2="11",
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva="1000.00",
            valorProvisao=0,
            valorRecuperacao=0,
            contaBalAnaliticoDebito="123456",
            nomeContaDebito="Conta Debito",
            contaCosifDebito="12345678",
        )
    ]
    linhas_consolidavel = [
        _linha(
            3,
            idEvento="EVT2",
            categoriaNivel1="2",
            categoriaNivel2="21",
            dataContabilizacao="2025-06-16",
            valorPerdaEfetiva="10.00",
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]

    evento_individualizado, _ = montar_evento("EVT1", linhas_individualizado)
    evento_consolidavel, _ = montar_evento("EVT2", linhas_consolidavel)

    assert classificar_evento(evento_individualizado) is True
    assert classificar_evento(evento_consolidavel) is False

    eventos = {"EVT1": evento_individualizado, "EVT2": evento_consolidavel}
    consolidados = consolidar_eventos(eventos, "2025-06")

    todas_as_linhas = linhas_individualizado + linhas_consolidavel
    sistemas = construir_mapa_sistemas(todas_as_linhas)
    contas = construir_mapa_contas(todas_as_linhas)

    documento = construir_xml(
        cabecalho=CABECALHO_VALIDO,
        eventos_individualizados=[evento_individualizado],
        eventos_consolidados=consolidados,
        sistemas=sistemas,
        contas=contas,
    )
    return documento


def test_documento_completo_e_valido_no_xsd_06_2025() -> None:
    documento = _montar_documento_valido()

    erros = validar_contra_xsd(documento)

    assert erros == []


def test_atributos_opcionais_ausentes_sao_omitidos() -> None:
    documento = _montar_documento_valido()

    evento_xml = documento.find("eventosIndividualizados/evento")

    assert evento_xml.get("negocioDescontinuado") is None


def test_valor_total_risco_omitido_para_avaliacao_na() -> None:
    documento = _montar_documento_valido()

    evento_xml = documento.find("eventosIndividualizados/evento")

    assert evento_xml.get("valorTotalRisco") is None


def test_decimais_tem_sempre_duas_casas() -> None:
    documento = _montar_documento_valido()

    evento_xml = documento.find("eventosIndividualizados/evento")

    assert evento_xml.get("totalPerdaEfetiva") == "1000.00"
    assert evento_xml.get("totalProvisao") == "0.00"


def test_documento_sem_conta_valida_falha_no_xsd() -> None:
    linhas = [
        _linha(
            2,
            idEvento="EVT1",
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva="1000.00",
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento, _ = montar_evento("EVT1", linhas)
    consolidados = consolidar_eventos({}, "2025-06")
    sistemas = construir_mapa_sistemas(linhas)
    contas = construir_mapa_contas(linhas)  # vazio: nenhuma conta informada

    documento = construir_xml(
        cabecalho=CABECALHO_VALIDO,
        eventos_individualizados=[evento],
        eventos_consolidados=consolidados,
        sistemas=sistemas,
        contas=contas,
    )

    erros = validar_contra_xsd(documento)

    assert erros != []


def test_serializar_xml_produz_bytes_com_declaracao_utf8() -> None:
    documento = _montar_documento_valido()

    conteudo = serializar_xml(documento)

    assert conteudo.startswith(b"<?xml version='1.0' encoding='UTF-8'?>")


def test_salvar_xml_nao_sobrescreve_arquivo_existente(tmp_path: Path) -> None:
    documento = _montar_documento_valido()
    caminho = tmp_path / "DRO_5050_2025-06.xml"
    caminho.write_bytes(b"conteudo previo")

    with pytest.raises(FileExistsError):
        salvar_xml(documento, caminho)

    assert caminho.read_bytes() == b"conteudo previo"


def test_campos_de_dominio_fechado_saem_maiusculos_no_xml() -> None:
    """Planilha -> normalizacao -> XML: confirma que o valor normalizado
    (maiusculo), nao o original em minusculo, e o que chega no XML para os
    8 campos de dominio fechado da Base; idEvento, codSistemaOrigem e
    idBacen preservam a escrita original (secao de identidade/referencia,
    fora do escopo de maiusculizacao)."""

    linhas_individualizado = [
        _linha(
            2,
            idEvento="EventoAbc01",
            categoriaNivel1="1",
            categoriaNivel2="11",
            tipoAvaliacao="i",
            naturezaContingencia="tri",
            codSistemaOrigem="SisOrig01",
            riscoAssociado="na",
            ligadoRiscoSocioAmbiental="s",
            ligadoRiscoCibernetico="n",
            negocioDescontinuado="n",
            idBacen="z1234567 - Banco Teste",
            probabilidadePerda="pr - provável",
            valorRisco=100,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva="1000.00",
            valorProvisao=0,
            valorRecuperacao=-50,
            fonteRecuperacao="o",
            contaBalAnaliticoDebito="123456",
            nomeContaDebito="Conta Debito",
            contaCosifDebito="12345678",
        )
    ]
    # Segundo evento so para satisfazer o XSD (exige ao menos 1
    # eventoConsolidado); nao faz parte do que este teste verifica.
    linhas_consolidavel = [
        _linha(
            3,
            idEvento="EVT2",
            categoriaNivel1="2",
            categoriaNivel2="21",
            dataContabilizacao="2025-06-16",
            valorPerdaEfetiva="10.00",
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]

    evento, ocorrencias = montar_evento("EventoAbc01", linhas_individualizado)
    assert ocorrencias == []
    evento_consolidavel, _ = montar_evento("EVT2", linhas_consolidavel)
    assert classificar_evento(evento_consolidavel) is False
    consolidados = consolidar_eventos({"EVT2": evento_consolidavel}, "2025-06")

    todas_as_linhas = linhas_individualizado + linhas_consolidavel
    sistemas = construir_mapa_sistemas(todas_as_linhas)
    contas = construir_mapa_contas(todas_as_linhas)
    documento = construir_xml(
        cabecalho=CABECALHO_VALIDO,
        eventos_individualizados=[evento],
        eventos_consolidados=consolidados,
        sistemas=sistemas,
        contas=contas,
    )

    assert validar_contra_xsd(documento) == []

    evento_xml = documento.find("eventosIndividualizados/evento")
    assert evento_xml.get("tipoAvaliacao") == "I"
    assert evento_xml.get("naturezaContingencia") == "TRI"
    assert evento_xml.get("riscoAssociado") == "NA"
    assert evento_xml.get("ligadoRiscoSocioAmbiental") == "S"
    assert evento_xml.get("ligadoRiscoCibernetico") == "N"
    assert evento_xml.get("negocioDescontinuado") == "N"

    prob_el = evento_xml.find("probabilidadesPerdas/probabilidadePerda")
    assert prob_el.get("probabilidade") == "PR"

    contabilizacao_el = evento_xml.find("contabilizacoes/contabilizacao")
    assert contabilizacao_el.get("fonteRecuperacao") == "O"

    # Identidade/referencia: escrita original preservada, nao maiusculizada.
    assert evento_xml.get("idEvento") == "EventoAbc01"
    assert evento_xml.get("codSistemaOrigem") == "SisOrig01"
    assert evento_xml.get("idBacen") == "z1234567"


def test_salvar_xml_grava_arquivo_novo(tmp_path: Path) -> None:
    documento = _montar_documento_valido()
    caminho = tmp_path / "DRO_5050_2025-06.xml"

    salvar_xml(documento, caminho)

    assert caminho.exists()
    conteudo = caminho.read_bytes()
    assert b"<documento" in conteudo


def test_salvar_xml_nao_deixa_arquivo_temporario_apos_sucesso(
    tmp_path: Path,
) -> None:
    """#5: escrita atomica via arquivo temporario + Path.replace() -- o
    .tmp nao deve sobrar depois de uma gravacao bem-sucedida."""

    documento = _montar_documento_valido()
    caminho = tmp_path / "DRO_5050_2025-06.xml"

    salvar_xml(documento, caminho)

    assert not caminho.with_name(caminho.name + ".tmp").exists()


def test_salvar_xml_remove_temporario_quando_a_gravacao_falha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#5: se a etapa final (rename atomico) falhar, o .tmp e removido em
    vez de ficar como lixo -- e o nome final nunca chega a existir."""

    documento = _montar_documento_valido()
    caminho = tmp_path / "DRO_5050_2025-06.xml"

    def _replace_com_falha(self: Path, destino: Path) -> None:
        raise OSError("falha simulada de gravação")

    monkeypatch.setattr(Path, "replace", _replace_com_falha)

    with pytest.raises(OSError):
        salvar_xml(documento, caminho)

    assert not caminho.exists()
    assert not caminho.with_name(caminho.name + ".tmp").exists()
