"""Orquestracao do fluxo completo de conversao (Fase 9).

Ver docs/plano_conversor_dro_5050_simples.md secao 4.
"""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from src.builders import (
    agrupar_linhas_por_evento,
    construir_mapa_contas,
    construir_mapa_sistemas,
    consolidar_eventos,
    montar_evento,
    normalizar_linha_base,
)
from src.calculations import classificar_evento
from src.models import (
    ETAPA_GERACAO_XML,
    ETAPA_GRAVACAO_ARQUIVO,
    ETAPA_XSD,
    Ocorrencia,
    ResultadoConversao,
    TIPO_ERRO_IMPEDITIVO,
    TIPO_FALHA_TECNICA,
)
from src.rules_local import (
    cabecalho_tem_data_base_valida,
    detectar_colisoes_id_evento,
    detectar_ausencia_e_invalidez,
    validar_cabecalho,
    validar_contabilizacao_antes_pre,
    validar_contabilizacao_depois_pre,
    validar_datas_apos_data_base,
    validar_estrutura_evento,
    validar_evento_local,
    validar_referencias_linha,
    validar_sistemas_e_contas_globais,
    validar_totais_evento,
)
from src.reader import (
    ArquivoInvalido,
    PlanilhaInvalida,
    extrair_cabecalho,
    ler_planilha,
)
from src.report_writer import gerar_relatorio
from src.rule_pos import (
    validar_consolidado,
    validar_evento as validar_evento_pos,
)
from src.rules_pre import (
    validar_contabilizacao_pre,
    validar_codigo_conglomerado_unicad,
    validar_contas_referenciadas,
    validar_evento as validar_evento_pre,
    validar_evento_apenas_risco,
    validar_provisao_avaliacao_na,
    validar_provisao_avaliacao_im,
    validar_referencias_linha_pre,
    validar_sistema_referenciado,
    validar_unicidade_do_documento,
)
from src.xml_writer import construir_xml, salvar_xml
from src.xsd_validator import (
    ErroTecnicoXSD,
    validar_xml_contra_xsd,
)

STATUS_APROVADO = "APROVADO"
STATUS_REPROVADO = "REPROVADO"
STATUS_FALHA_TECNICA = "FALHA TÉCNICA"
STATUS_NAO_EXECUTADO = "NÃO EXECUTADO"
DATA_BASE_INDISPONIVEL = "SEM_DATA_BASE"


def _ocorrencia_falha_tecnica(
    codigo: str,
    descricao: str,
    detalhe: str,
    *,
    etapa: str,
) -> Ocorrencia:
    return Ocorrencia(
        etapa=etapa,
        tipo=TIPO_FALHA_TECNICA,
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
    id_evento_por_linha = {
        linha.numero_linha: linha.valor("idEvento")
        for linha in linhas_normalizadas
    }
    ocorrencias_locais_por_evento: dict[str, list[Ocorrencia]] = {}

    def registrar_ocorrencias_locais(
        novas_ocorrencias: list[Ocorrencia],
    ) -> None:
        ocorrencias.extend(novas_ocorrencias)
        for ocorrencia in novas_ocorrencias:
            ids_afetados: list[str] = []
            if ocorrencia.id_evento is not None:
                ids_afetados.append(str(ocorrencia.id_evento))
            for numero_linha in ocorrencia.linhas:
                id_afetado = id_evento_por_linha.get(numero_linha)
                if id_afetado is not None and str(id_afetado) not in ids_afetados:
                    ids_afetados.append(str(id_afetado))
            for id_afetado in ids_afetados:
                ocorrencias_locais_por_evento.setdefault(id_afetado, []).append(
                    ocorrencia
                )

    for linha in linhas_normalizadas:
        id_evento = linha.valor("idEvento")
        registrar_ocorrencias_locais(
            detectar_ausencia_e_invalidez(
                linha.campos, linha.numero_linha, id_evento
            )
        )

    for linha in linhas_normalizadas:
        registrar_ocorrencias_locais(validar_referencias_linha(linha))
    registrar_ocorrencias_locais(
        validar_sistemas_e_contas_globais(linhas_normalizadas)
    )
    registrar_ocorrencias_locais(
        detectar_colisoes_id_evento(linhas_normalizadas)
    )

    sistemas = construir_mapa_sistemas(linhas_normalizadas)
    contas = construir_mapa_contas(linhas_normalizadas)

    grupos = agrupar_linhas_por_evento(linhas_normalizadas)
    eventos = {}
    eventos_bloqueados_consolidacao: set[str] = set()
    for id_evento, linhas_do_evento in grupos.items():
        evento = montar_evento(id_evento, linhas_do_evento)
        eventos[id_evento] = evento
        inicio_ocorrencias_evento = len(ocorrencias)

        ocorrencias_montagem = validar_estrutura_evento(evento)
        if evento.consistente:
            for contabilizacao in evento.contabilizacoes:
                ocorrencias_montagem.extend(
                    validar_contabilizacao_antes_pre(id_evento, contabilizacao)
                )
                ocorrencias_montagem.extend(
                    validar_contabilizacao_depois_pre(id_evento, contabilizacao)
                )
            ocorrencias_montagem.extend(validar_totais_evento(evento))
        ocorrencias.extend(ocorrencias_montagem)

        ocorrencias_locais_evento = [
            *ocorrencias_locais_por_evento.get(id_evento, ()),
            *ocorrencias_montagem,
        ]

        # DRO001301 e DRO001302 precisam enxergar as linhas originais, mesmo
        # quando outra falha local torna a estrutura inadequada as demais regras.
        if evento.consistente:
            ocorrencias.extend(validar_provisao_avaliacao_na(evento))
            ocorrencia_provisao = validar_provisao_avaliacao_im(evento)
            if ocorrencia_provisao is not None:
                ocorrencias.append(ocorrencia_provisao)
            ocorrencia_apenas_risco = validar_evento_apenas_risco(evento)
            if ocorrencia_apenas_risco is not None:
                ocorrencias.append(ocorrencia_apenas_risco)

        resultado_local = validar_evento_local(
            evento, ocorrencias_locais_evento
        )
        ocorrencias.extend(resultado_local.ocorrencias)
        if resultado_local.bloqueia_consolidacao:
            eventos_bloqueados_consolidacao.add(id_evento)

        if (
            not evento.consistente
            or resultado_local.bloqueia_regras_regulatorias
        ):
            if any(
                ocorrencia.tipo == TIPO_ERRO_IMPEDITIVO
                for ocorrencia in ocorrencias[inicio_ocorrencias_evento:]
            ):
                eventos_bloqueados_consolidacao.add(id_evento)
            continue

        for linha in evento.linhas:
            ocorrencias.extend(validar_referencias_linha_pre(linha))
        data_ocorrencia = evento.valor_evento("dataOcorrencia")
        for contabilizacao in evento.contabilizacoes:
            ocorrencias.extend(
                validar_contabilizacao_pre(
                    id_evento, contabilizacao, data_ocorrencia
                )
            )
        ocorrencias.extend(validar_evento_pre(evento))
        ocorrencias.extend(validar_evento_pos(evento))
        ocorrencia_sistema = validar_sistema_referenciado(evento, sistemas)
        if ocorrencia_sistema is not None:
            ocorrencias.append(ocorrencia_sistema)
        ocorrencias.extend(validar_contas_referenciadas(evento, contas))
        if data_base_valida:
            ocorrencias.extend(validar_datas_apos_data_base(evento, data_base))

        if any(
            ocorrencia.tipo == TIPO_ERRO_IMPEDITIVO
            for ocorrencia in ocorrencias[inicio_ocorrencias_evento:]
        ):
            eventos_bloqueados_consolidacao.add(id_evento)

    ocorrencias.extend(validar_unicidade_do_documento(eventos))

    consolidados = {}
    if data_base_valida:
        eventos_para_consolidar = {
            id_evento: evento
            for id_evento, evento in eventos.items()
            if id_evento not in eventos_bloqueados_consolidacao
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
                    etapa=ETAPA_GERACAO_XML,
                )
            )

        if documento_xml is not None:
            try:
                ocorrencias_xsd = validar_xml_contra_xsd(documento_xml)
            except ErroTecnicoXSD as erro:
                status_xsd = STATUS_FALHA_TECNICA
                ocorrencias.append(
                    _ocorrencia_falha_tecnica(
                        "XSD-TEC-001",
                        "Não foi possível carregar ou compilar o XSD 06/2025.",
                        str(erro),
                    etapa=ETAPA_XSD,
                    )
                )
            else:
                if ocorrencias_xsd:
                    status_xsd = STATUS_REPROVADO
                    ocorrencias.extend(ocorrencias_xsd)
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
                                etapa=ETAPA_GRAVACAO_ARQUIVO,
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
