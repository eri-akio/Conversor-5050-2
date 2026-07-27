"""Orquestracao do fluxo completo de conversao (Fase 9).

Ver docs/plano_conversor_dro_5050_simples.md secao 4.
"""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from src.calculations import (
    CODIGOS_FORMATO_QUE_SUPRIMEM_REGRAS,
    agrupar_linhas_por_evento,
    construir_mapa_contas,
    construir_mapa_sistemas,
    detectar_colisoes_id_evento,
    montar_evento,
    normalizar_linha_base,
    validar_sistemas_e_contas,
)
from src.models import (
    ETAPA_XSD,
    Ocorrencia,
    ResultadoConversao,
    TIPO_ERRO_IMPEDITIVO,
)
from src.normalizers import detectar_ausencia_e_invalidez
from src.reader import (
    ArquivoInvalido,
    PlanilhaInvalida,
    extrair_cabecalho,
    ler_planilha,
)
from src.report_writer import gerar_relatorio
from src.rules_post import (
    consolidar_eventos,
    validar_consolidado,
    validar_datas_apos_data_base,
)
from src.rules_post import validar_evento as validar_evento_pos
from src.rules_pre import (
    cabecalho_tem_data_base_valida,
    classificar_evento,
    validar_cabecalho,
    validar_codigo_conglomerado_unicad,
    validar_contas_referenciadas,
    validar_evento,
    validar_formatos_e_dominios_evento,
    validar_sistema_referenciado,
    validar_unicidade_do_documento,
)
from src.xml_writer import construir_xml, salvar_xml, validar_contra_xsd

STATUS_APROVADO = "APROVADO"
STATUS_REPROVADO = "REPROVADO"
STATUS_FALHA_TECNICA = "FALHA TÉCNICA"
STATUS_NAO_EXECUTADO = "NÃO EXECUTADO"
DATA_BASE_INDISPONIVEL = "SEM_DATA_BASE"


def _ocorrencia_falha_tecnica(codigo: str, descricao: str, detalhe: str) -> Ocorrencia:
    return Ocorrencia(
        etapa=ETAPA_XSD,
        tipo=TIPO_ERRO_IMPEDITIVO,
        codigo=codigo,
        descricao=descricao,
        detalhe=detalhe,
    )


def _proximo_caminho_disponivel(caminho: Path) -> Path:
    """Se o caminho já existe, acrescenta _1, _2... antes da extensão, em
    vez de sobrescrever (secao 22: arquivos existentes não são
    sobrescritos silenciosamente)."""

    if not caminho.exists():
        return caminho
    contador = 1
    while True:
        candidato = caminho.with_name(
            f"{caminho.stem}_{contador}{caminho.suffix}"
        )
        if not candidato.exists():
            return candidato
        contador += 1


def _proximos_caminhos_de_saida(
    pasta_saida: Path, data_base: str
) -> tuple[Path, Path]:
    """Caminhos do XML e do relatório para esta execução, incrementando
    juntos (_1, _2...) quando já existir um resultado com o mesmo nome, de
    forma que XML e relatório de uma mesma execução fiquem com o mesmo
    sufixo."""

    contador = 0
    while True:
        sufixo = "" if contador == 0 else f"_{contador}"
        caminho_xml = pasta_saida / f"DRO_5050_{data_base}{sufixo}.xml"
        caminho_relatorio = (
            pasta_saida / f"Relatorio_DRO_5050_{data_base}{sufixo}.xlsx"
        )
        if not caminho_xml.exists() and not caminho_relatorio.exists():
            return caminho_xml, caminho_relatorio
        contador += 1


def processar(
    caminho_planilha: Path, pasta_saida: Path
) -> ResultadoConversao:
    """Executa o fluxo completo (secao 4) e devolve o resultado.

    O relatorio e sempre gravado quando tecnicamente possivel (secao 22);
    so nao e gerado quando o arquivo de entrada nem sequer pode ser aberto
    (FALHA TECNICA)."""

    pasta_saida.mkdir(parents=True, exist_ok=True)

    try:
        planilha = ler_planilha(caminho_planilha)
    except ArquivoInvalido as erro:
        return ResultadoConversao(
            status_local=STATUS_FALHA_TECNICA,
            status_xsd=STATUS_NAO_EXECUTADO,
            ocorrencias=(),
            caminho_xml=None,
            caminho_relatorio=None,
            mensagem=str(erro),
        )
    except PlanilhaInvalida as erro:
        ocorrencias = (erro.ocorrencia,)
        caminho_relatorio = _proximo_caminho_disponivel(
            pasta_saida
            / f"Relatorio_DRO_5050_{DATA_BASE_INDISPONIVEL}.xlsx"
        )
        gerar_relatorio(
            caminho_relatorio,
            status_local=STATUS_REPROVADO,
            status_xsd=STATUS_NAO_EXECUTADO,
            ocorrencias=list(ocorrencias),
        )
        return ResultadoConversao(
            status_local=STATUS_REPROVADO,
            status_xsd=STATUS_NAO_EXECUTADO,
            ocorrencias=ocorrencias,
            caminho_xml=None,
            caminho_relatorio=caminho_relatorio,
            mensagem=erro.ocorrencia.detalhe,
        )

    cabecalho = extrair_cabecalho(planilha)
    ocorrencias: list[Ocorrencia] = []

    ocorrencias.extend(validar_cabecalho(cabecalho))
    resultado_unicad = validar_codigo_conglomerado_unicad(cabecalho)
    if resultado_unicad is not None:
        ocorrencias.append(resultado_unicad)
    data_base_valida = cabecalho_tem_data_base_valida(cabecalho)
    data_base = cabecalho["dataBase"].valor if data_base_valida else None

    linhas_normalizadas = [
        normalizar_linha_base(
            indice + 2, planilha.cabecalhos_base, linha
        )
        for indice, linha in enumerate(planilha.linhas_base())
    ]

    for linha in linhas_normalizadas:
        id_evento = linha.valor("idEvento")
        ocorrencias.extend(
            detectar_ausencia_e_invalidez(
                linha.campos, linha.numero_linha, id_evento
            )
        )

    ocorrencias.extend(validar_sistemas_e_contas(linhas_normalizadas))
    ocorrencias.extend(detectar_colisoes_id_evento(linhas_normalizadas))

    sistemas = construir_mapa_sistemas(linhas_normalizadas)
    contas = construir_mapa_contas(linhas_normalizadas)

    grupos = agrupar_linhas_por_evento(linhas_normalizadas)
    eventos = {}
    eventos_com_erro_formato: set[str] = set()
    for id_evento, linhas_do_evento in grupos.items():
        evento, ocorrencias_evento = montar_evento(id_evento, linhas_do_evento)
        eventos[id_evento] = evento
        ocorrencias.extend(ocorrencias_evento)

        erro_formato_na_montagem = any(
            o.codigo in CODIGOS_FORMATO_QUE_SUPRIMEM_REGRAS
            for o in ocorrencias_evento
        )

        if evento.consistente:
            ocorrencias_formato = validar_formatos_e_dominios_evento(evento)
            ocorrencias.extend(ocorrencias_formato)

            tem_erro_formato = erro_formato_na_montagem or bool(ocorrencias_formato)

            if not tem_erro_formato:
                ocorrencias.extend(validar_evento(evento))
                ocorrencias.extend(validar_evento_pos(evento))
                ocorrencia_sistema = validar_sistema_referenciado(evento, sistemas)
                if ocorrencia_sistema is not None:
                    ocorrencias.append(ocorrencia_sistema)
                ocorrencias.extend(validar_contas_referenciadas(evento, contas))
                if data_base_valida:
                    ocorrencias.extend(
                        validar_datas_apos_data_base(evento, data_base)
                    )
            else:
                eventos_com_erro_formato.add(id_evento)

    ocorrencias.extend(validar_unicidade_do_documento(eventos))

    consolidados = {}
    if data_base_valida:
        eventos_para_consolidar = {
            id_evento: evento
            for id_evento, evento in eventos.items()
            if id_evento not in eventos_com_erro_formato
        }
        consolidados = consolidar_eventos(eventos_para_consolidar, data_base)
        for consolidado in consolidados.values():
            ocorrencias.extend(validar_consolidado(consolidado))

    status_local = (
        STATUS_REPROVADO
        if any(o.tipo == TIPO_ERRO_IMPEDITIVO for o in ocorrencias)
        else STATUS_APROVADO
    )

    caminho_xml, caminho_relatorio = _proximos_caminhos_de_saida(
        pasta_saida, data_base if data_base_valida else DATA_BASE_INDISPONIVEL
    )

    status_xsd = STATUS_NAO_EXECUTADO
    documento_xml = None
    if status_local == STATUS_APROVADO:
        eventos_individualizados = [
            evento
            for evento in eventos.values()
            if classificar_evento(evento)
        ]

        try:
            documento_xml = construir_xml(
                cabecalho={nome: campo.valor for nome, campo in cabecalho.items()},
                eventos_individualizados=eventos_individualizados,
                eventos_consolidados=consolidados,
                sistemas=sistemas,
                contas=contas,
            )
        except (OSError, etree.LxmlError) as erro:
            status_xsd = STATUS_FALHA_TECNICA
            ocorrencias.append(
                _ocorrencia_falha_tecnica(
                    "XML-TEC-001",
                    "Não foi possível construir o XML.",
                    str(erro),
                )
            )

        if documento_xml is not None:
            try:
                erros_xsd = validar_contra_xsd(documento_xml)
            except (OSError, etree.LxmlError) as erro:
                status_xsd = STATUS_FALHA_TECNICA
                ocorrencias.append(
                    _ocorrencia_falha_tecnica(
                        "XSD-TEC-001",
                        "Não foi possível carregar ou compilar o XSD 06/2025.",
                        str(erro),
                    )
                )
            else:
                if erros_xsd:
                    status_xsd = STATUS_REPROVADO
                    ocorrencias.extend(
                        Ocorrencia(
                            etapa=ETAPA_XSD,
                            tipo=TIPO_ERRO_IMPEDITIVO,
                            codigo="XSD-001",
                            descricao="XML incompatível com o XSD 06/2025.",
                            detalhe=erro,
                        )
                        for erro in erros_xsd
                    )
                else:
                    try:
                        salvar_xml(documento_xml, caminho_xml)
                    except OSError as erro:
                        status_xsd = STATUS_FALHA_TECNICA
                        ocorrencias.append(
                            _ocorrencia_falha_tecnica(
                                "ARQ-TEC-001",
                                "Não foi possível gravar o arquivo XML final.",
                                str(erro),
                            )
                        )
                    else:
                        status_xsd = STATUS_APROVADO

    try:
        gerar_relatorio(
            caminho_relatorio,
            status_local=status_local,
            status_xsd=status_xsd,
            ocorrencias=ocorrencias,
        )
    except OSError:
        caminho_relatorio = None

    aprovado = status_local == STATUS_APROVADO and status_xsd == STATUS_APROVADO
    if caminho_relatorio is None:
        mensagem = (
            f"Conversão concluída (local={status_local}, xsd={status_xsd}), "
            "mas o relatório não pôde ser gravado."
        )
    elif aprovado:
        mensagem = "Conversão aprovada."
    else:
        mensagem = (
            f"Conversão não aprovada (local={status_local}, xsd={status_xsd})."
        )

    return ResultadoConversao(
        status_local=status_local,
        status_xsd=status_xsd,
        ocorrencias=tuple(ocorrencias),
        caminho_xml=caminho_xml if aprovado else None,
        caminho_relatorio=caminho_relatorio,
        mensagem=mensagem,
    )


def convert(caminho_planilha: Path, pasta_saida: Path | None = None) -> None:
    """Modo terminal (secao 4/22)."""

    destino = pasta_saida if pasta_saida is not None else Path.cwd() / "output"
    resultado = processar(caminho_planilha, destino)

    print(f"Validação local: {resultado.status_local}")
    print(f"Validação XSD: {resultado.status_xsd}")
    print(resultado.mensagem)
    if resultado.caminho_relatorio is not None:
        print(f"Relatório: {resultado.caminho_relatorio}")
    if resultado.caminho_xml is not None:
        print(f"XML: {resultado.caminho_xml}")
