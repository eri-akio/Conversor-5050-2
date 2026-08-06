"""Criticas oficiais de pos-processamento do DRO 5050.

Quando este modulo produz uma Ocorrencia, seu codigo pertence exclusivamente
a familia DRO000*. Ele valida eventos e consolidados construidos em builders.py.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.calculations import (
    saldo_acumulado_fica_negativo,
)
from src.models import (
    ETAPA_POS_PROCESSAMENTO,
    EventoAgrupado,
    EventoConsolidado,
    Ocorrencia,
    TIPO_AVISO,
    TIPO_ERRO_IMPEDITIVO,
)
from src.regulatory_constants import DATA_INICIO_2021

MEDIA_MAXIMA = Decimal("1000.00")
LIMIAR_SALDO_NEGATIVO = Decimal("-10.00")


def _erro(
    evento: EventoAgrupado,
    codigo: str,
    descricao: str,
    detalhe: str,
    campos: tuple[str, ...] = (),
    tipo: str = TIPO_ERRO_IMPEDITIVO,
) -> Ocorrencia:
    return Ocorrencia(
        etapa=ETAPA_POS_PROCESSAMENTO,
        tipo=tipo,
        codigo=codigo,
        descricao=descricao,
        detalhe=detalhe,
        linhas=evento.numeros_linha,
        id_evento=evento.id_evento,
        campos=campos,
    )


# ---------------------------------------------------------------------------
# Probabilidades (secao 11/18)
# ---------------------------------------------------------------------------


def validar_pr_com_provisao_zero(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO000004."""

    if (
        evento.valor_evento("tipoAvaliacao") != "I"
        or evento.total_provisao != 0
    ):
        return None
    if any(p.codigo == "PR" for p in evento.probabilidades):
        return _erro(
            evento,
            "DRO000004",
            (
                "Contingências passivas, avaliadas individualmente, com "
                "atribuição de perda provável e sem atribuição de "
                "provisão."
            ),
            "Há probabilidade PR com totalProvisao=0,00.",
            ("probabilidadePerda", "totalProvisao"),
        )
    return None


def validar_po_re_com_risco_zero(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO000005."""

    if evento.valor_evento("tipoAvaliacao") != "I":
        return None
    zeradas = [
        p
        for p in evento.probabilidades
        if p.codigo in ("PO", "RE") and p.valor_risco == 0
    ]
    if zeradas:
        return _erro(
            evento,
            "DRO000005",
            (
                "Contingências passivas, avaliadas individualmente, com "
                "atribuição de perda possível ou remorta e sem "
                "atribuição do valor do risco da contingência."
            ),
            f"Código(s) com valorRisco=0,00: {', '.join(p.codigo for p in zeradas)}.",
            ("probabilidadePerda", "valorRisco"),
        )
    return None


def validar_contingencia_individual_sem_probabilidade(
    evento: EventoAgrupado,
) -> Ocorrencia | None:
    """DRO000003."""

    ocorrencia_data = evento.valor_evento("dataOcorrencia")
    if (
        evento.valor_evento("tipoAvaliacao") != "I"
        or not isinstance(ocorrencia_data, date)
        or ocorrencia_data < DATA_INICIO_2021
    ):
        return None
    if not evento.probabilidades:
        return _erro(
            evento,
            "DRO000003",
            (
                "Contingências passivas ocorridas após 01/01/2021, "
                "avaliadas individualmente, sem detalhamento de "
                "probabilidade de perda."
            ),
            "Nenhuma probabilidade foi informada no evento.",
            ("probabilidadePerda",),
        )
    return None


# ---------------------------------------------------------------------------
# Contabilizacoes (secao 12/18)
# ---------------------------------------------------------------------------


def validar_primeira_contabilizacao_sem_categoria(
    evento: EventoAgrupado,
) -> Ocorrencia | None:
    """DRO000009: usa min(dataContabilizacao), nao dataOcorrencia -- por
    isso pode disparar mesmo quando DRO001212 (que usa dataOcorrencia,
    rules_pre.py) nao acusa nada para o mesmo evento: um evento pode ter
    ocorrido antes de 2021 mas sido contabilizado (lancado) so depois."""

    datas = [
        c.data_contabilizacao
        for c in evento.contabilizacoes
        if c.data_contabilizacao is not None
    ]
    if not datas or min(datas) <= DATA_INICIO_2021:
        return None
    if evento.linhas[0].status("categoriaNivel2").name == "AUSENTE":
        return _erro(
            evento,
            "DRO000009",
            (
                "Eventos posteriores a 01/01/2021 sem atribuição do 2º "
                "Nível de Classificação Basileia II."
            ),
            (
                f"Primeira contabilização em {min(datas)} (dataOcorrencia "
                f"do evento: {evento.valor_evento('dataOcorrencia')}), "
                "categoriaNivel2 ausente."
            ),
            ("categoriaNivel2",),
        )
    return None


def validar_contabilizacao_anterior_a_descoberta(
    evento: EventoAgrupado,
) -> Ocorrencia | None:
    """DRO000010."""

    descoberta = evento.valor_evento("dataDescoberta")
    if descoberta is None:
        return None
    anteriores = [
        c
        for c in evento.contabilizacoes
        if c.data_contabilizacao is not None and c.data_contabilizacao < descoberta
    ]
    if anteriores:
        return _erro(
            evento,
            "DRO000010",
            "Eventos com contabilizações anteriores à data de descoberta.",
            (
                f"dataContabilizacao={min(c.data_contabilizacao for c in anteriores)} "
                f"< dataDescoberta={descoberta}."
            ),
            ("dataContabilizacao", "dataDescoberta"),
        )
    return None


# ---------------------------------------------------------------------------
# Totais do evento (secao 15/18)
# ---------------------------------------------------------------------------


def validar_perda_minima(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO000011."""

    if evento.total_perda_efetiva is not None and evento.total_perda_efetiva < Decimal("-10.00"):
        return _erro(
            evento,
            "DRO000011",
            "Eventos com valor total de perda efetiva com sinal negativo.",
            f"totalPerdaEfetiva={evento.total_perda_efetiva:.2f}.",
            ("totalPerdaEfetiva",),
        )
    return None


def validar_provisao_minima(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO000012."""

    if evento.total_provisao is not None and evento.total_provisao < Decimal("-10.00"):
        return _erro(
            evento,
            "DRO000012",
            "Eventos com valor total de provisão com sinal negativo.",
            f"totalProvisao={evento.total_provisao:.2f}.",
            ("totalProvisao",),
        )
    return None


def validar_recuperacao_maxima(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO000013."""

    if evento.total_recuperado is not None and evento.total_recuperado > 0:
        return _erro(
            evento,
            "DRO000013",
            "Eventos com valor total recuperado com sinal positivo.",
            f"totalRecuperado={evento.total_recuperado:.2f}.",
            ("totalRecuperado",),
        )
    return None


def validar_recuperacao_dentro_do_limite(
    evento: EventoAgrupado,
) -> Ocorrencia | None:
    """DRO000014."""

    if evento.total_recuperado is None:
        return None
    limite = evento.total_perda_efetiva + evento.total_provisao
    if abs(evento.total_recuperado) > limite:
        return _erro(
            evento,
            "DRO000014",
            (
                "Eventos com valor total recuperado, em módulo, superior "
                "ao valor da perda bruta."
            ),
            (
                f"|totalRecuperado|={abs(evento.total_recuperado):.2f} > "
                f"{limite:.2f}."
            ),
            ("totalRecuperado", "totalPerdaEfetiva", "totalProvisao"),
        )
    return None


def validar_totais_batem_com_contabilizacoes(
    evento: EventoAgrupado,
) -> Ocorrencia | None:
    """DRO000015."""

    if evento.total_perda_efetiva is None:
        return None
    soma_perda = sum(
        (c.valor_perda_efetiva for c in evento.contabilizacoes), Decimal("0.00")
    )
    soma_provisao = sum(
        (c.valor_provisao for c in evento.contabilizacoes), Decimal("0.00")
    )
    soma_recuperacao = sum(
        (c.valor_recuperacao for c in evento.contabilizacoes), Decimal("0.00")
    )
    if (
        soma_perda != evento.total_perda_efetiva
        or soma_provisao != evento.total_provisao
        or soma_recuperacao != evento.total_recuperado
    ):
        return _erro(
            evento,
            "DRO000015",
            (
                "Inconsistência entre os totais de Perda Efetiva, "
                "Provisão ou Valor Recuperado e a soma do bloco de "
                "contabilizações."
            ),
            (
                f"Totais={evento.total_perda_efetiva:.2f}/"
                f"{evento.total_provisao:.2f}/{evento.total_recuperado:.2f}, "
                f"soma das contabilizações={soma_perda:.2f}/"
                f"{soma_provisao:.2f}/{soma_recuperacao:.2f}."
            ),
            ("totalPerdaEfetiva", "totalProvisao", "totalRecuperado"),
        )
    return None


def validar_fraude_com_provisao(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO000032 (planilha oficial de criticas de pos-processamento):
    categoriaNivel1 = 1 ou 2 (fraude interna/externa, Basileia II) e
    totalProvisao > 0 -> inconsistencia. Sem gate de individualizacao: a
    condicao oficial nao recorta por bloco de saida, entao avalia todo
    evento agrupado consistente."""

    categoria = evento.valor_evento("categoriaNivel1")
    if categoria not in ("1", "2"):
        return None
    if evento.total_provisao is None or evento.total_provisao <= 0:
        return None
    return _erro(
        evento,
        "DRO000032",
        (
            "Eventos de fraude (categorias 1 e 2 do 1º Nível de "
            "Classificação Basileia II) com provisão."
        ),
        (
            f"categoriaNivel1={categoria!r} e "
            f"totalProvisao={evento.total_provisao:.2f}."
        ),
        ("categoriaNivel1", "totalProvisao"),
    )


def validar_categorias_compativeis(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO000021: o primeiro dígito de categoriaNivel2 deve ser igual a
    categoriaNivel1 (enumeração tipoCategoriaNivel2 do XSD 06/2025:
    11,12,21,22,31...86 — o primeiro dígito sempre reflete o nível 1)."""

    nivel1 = evento.valor_evento("categoriaNivel1")
    nivel2 = evento.valor_evento("categoriaNivel2")
    if nivel1 is None or nivel2 is None:
        return None
    if not str(nivel2).startswith(str(nivel1)):
        return _erro(
            evento,
            "DRO000021",
            (
                "Eventos com atribuição de 2º Nível de Classificação "
                "Basileia II incondizente com 1º Nível"
            ),
            f"categoriaNivel1={nivel1!r}, categoriaNivel2={nivel2!r}.",
            ("categoriaNivel1", "categoriaNivel2"),
        )
    return None


# ---------------------------------------------------------------------------
# Saldo acumulado por data de fechamento (secao 18)
# ---------------------------------------------------------------------------


def validar_saldo_acumulado_perda(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO000023."""

    if saldo_acumulado_fica_negativo(evento, "valor_perda_efetiva"):
        return _erro(
            evento,
            "DRO000023",
            (
                "Verifica a existência momentânea de saldo acumulado "
                "negativo de Perda Efetiva, no bloco de contabilizações."
            ),
            "O saldo acumulado de valorPerdaEfetiva por fechamento diário ficou negativo.",
            ("valorPerdaEfetiva", "dataContabilizacao"),
        )
    return None


def validar_saldo_acumulado_provisao(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO000024 (Esclarecimento -> AVISO)."""

    if saldo_acumulado_fica_negativo(evento, "valor_provisao"):
        return _erro(
            evento,
            "DRO000024",
            (
                "Verifica a existência momentânea de saldo acumulado "
                "negativo de Provisão, no bloco de contabilizações."
            ),
            "O saldo acumulado de valorProvisao por fechamento diário ficou negativo.",
            ("valorProvisao", "dataContabilizacao"),
            tipo=TIPO_AVISO,
        )
    return None


REGRAS_POR_EVENTO = (
    validar_pr_com_provisao_zero,
    validar_po_re_com_risco_zero,
    validar_contingencia_individual_sem_probabilidade,
    validar_primeira_contabilizacao_sem_categoria,
    validar_contabilizacao_anterior_a_descoberta,
    validar_perda_minima,
    validar_provisao_minima,
    validar_recuperacao_maxima,
    validar_recuperacao_dentro_do_limite,
    validar_totais_batem_com_contabilizacoes,
    validar_fraude_com_provisao,
    validar_categorias_compativeis,
    validar_saldo_acumulado_perda,
    validar_saldo_acumulado_provisao,
)


def validar_evento(evento: EventoAgrupado) -> list[Ocorrencia]:
    if not evento.consistente:
        return []
    ocorrencias: list[Ocorrencia] = []
    for regra in REGRAS_POR_EVENTO:
        resultado = regra(evento)
        if resultado is not None:
            ocorrencias.append(resultado)
    return ocorrencias


# ---------------------------------------------------------------------------
# Consolidacao por categoriaNivel1 (secao 16)
# ---------------------------------------------------------------------------


def validar_media_semestral(
    consolidado: EventoConsolidado,
) -> Ocorrencia | None:
    """DRO000001."""

    if consolidado.num_eventos_semestre == 0:
        return None
    media = (
        consolidado.perda_efetiva_semestre + consolidado.provisao_semestre
    ) / consolidado.num_eventos_semestre
    if media > MEDIA_MAXIMA:
        return Ocorrencia(
            etapa=ETAPA_POS_PROCESSAMENTO,
            tipo=TIPO_ERRO_IMPEDITIVO,
            codigo="DRO000001",
            descricao=(
                "Verifica, em cada categoria do Bloco 2 - Eventos "
                "Consolidados, se a perda bruta acumulada no semestre é, "
                "em média, superior ao limite de R$ 1.000,00."
            ),
            detalhe=(
                f"categoriaNivel1={consolidado.categoria_nivel1!r}, "
                f"média={media:.2f}."
            ),
            campos=(
                "perdaEfetivaSemestreConsol",
                "provisaoSemestreConsol",
                "numEventosSemestreConsol",
            ),
        )
    return None


def validar_media_total(consolidado: EventoConsolidado) -> Ocorrencia | None:
    """DRO000002."""

    if consolidado.num_eventos_total == 0:
        return None
    media = (
        consolidado.perda_efetiva_total + consolidado.provisao_total
    ) / consolidado.num_eventos_total
    if media > MEDIA_MAXIMA:
        return Ocorrencia(
            etapa=ETAPA_POS_PROCESSAMENTO,
            tipo=TIPO_ERRO_IMPEDITIVO,
            codigo="DRO000002",
            descricao=(
                "Verifica, em cada categoria do Bloco 2 - Eventos "
                "Consolidados, se a perda bruta acumulada é, em média, "
                "superior ao limite de R$ 1.000,00."
            ),
            detalhe=(
                f"categoriaNivel1={consolidado.categoria_nivel1!r}, "
                f"média={media:.2f}."
            ),
            campos=(
                "perdaEfetivaTotalConsol",
                "provisaoTotalConsol",
                "numEventosTotalConsol",
            ),
        )
    return None


def validar_perda_consolidada_minima(
    consolidado: EventoConsolidado,
) -> Ocorrencia | None:
    """DRO000018."""

    if consolidado.perda_efetiva_total < LIMIAR_SALDO_NEGATIVO:
        return Ocorrencia(
            etapa=ETAPA_POS_PROCESSAMENTO,
            tipo=TIPO_ERRO_IMPEDITIVO,
            codigo="DRO000018",
            descricao=(
                "Verifica a existência de perda efetiva negativa em cada "
                "categoria do Bloco 2 - Eventos Consolidados."
            ),
            detalhe=(
                f"categoriaNivel1={consolidado.categoria_nivel1!r}, "
                f"perdaEfetivaTotalConsol={consolidado.perda_efetiva_total:.2f}."
            ),
            campos=("perdaEfetivaTotalConsol",),
        )
    return None


def validar_provisao_consolidada_minima(
    consolidado: EventoConsolidado,
) -> Ocorrencia | None:
    """DRO000019."""

    if consolidado.provisao_total < LIMIAR_SALDO_NEGATIVO:
        return Ocorrencia(
            etapa=ETAPA_POS_PROCESSAMENTO,
            tipo=TIPO_ERRO_IMPEDITIVO,
            codigo="DRO000019",
            descricao=(
                "Verifica a existência de provisão negativa em cada "
                "categoria do Bloco 2 - Eventos Consolidados."
            ),
            detalhe=(
                f"categoriaNivel1={consolidado.categoria_nivel1!r}, "
                f"provisaoTotalConsol={consolidado.provisao_total:.2f}."
            ),
            campos=("provisaoTotalConsol",),
        )
    return None


REGRAS_POR_CONSOLIDADO = (
    validar_media_semestral,
    validar_media_total,
    validar_perda_consolidada_minima,
    validar_provisao_consolidada_minima,
)


def validar_consolidado(consolidado: EventoConsolidado) -> list[Ocorrencia]:
    ocorrencias: list[Ocorrencia] = []
    for regra in REGRAS_POR_CONSOLIDADO:
        resultado = regra(consolidado)
        if resultado is not None:
            ocorrencias.append(resultado)
    return ocorrencias
