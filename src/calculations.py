"""Formulas puras usadas pelo conversor DRO 5050."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.models import EventoAgrupado
from src.regulatory_constants import (
    LIMIAR_EMISSAO_VALOR_TOTAL_RISCO,
    LIMIAR_INDIVIDUALIZACAO,
    LIMIAR_RISCO_NAO_COBERTO,
)


@dataclass(frozen=True)
class TotaisEvento:
    perda_efetiva: Decimal
    provisao: Decimal
    recuperado: Decimal
    valor_total_risco: Decimal | None


def calcular_soma_risco(evento: EventoAgrupado) -> Decimal:
    """Soma os valores de risco validos associados ao evento."""
    return sum(
        (p.valor_risco for p in evento.probabilidades), Decimal("0.00")
    )


def calcular_totais(evento: EventoAgrupado) -> TotaisEvento | None:
    """Calcula os totais sem alterar o evento recebido."""
    if not evento.consistente:
        return None
    total_perda = sum(
        (c.valor_perda_efetiva for c in evento.contabilizacoes),
        Decimal("0.00"),
    )
    total_provisao = sum(
        (c.valor_provisao for c in evento.contabilizacoes), Decimal("0.00")
    )
    total_recuperado = sum(
        (c.valor_recuperacao for c in evento.contabilizacoes), Decimal("0.00")
    )
    valor_total_risco = None
    if evento.valor_evento("tipoAvaliacao") == "I":
        calculado = total_provisao + calcular_soma_risco(evento)
        if calculado >= LIMIAR_EMISSAO_VALOR_TOTAL_RISCO:
            valor_total_risco = calculado
    return TotaisEvento(
        perda_efetiva=total_perda,
        provisao=total_provisao,
        recuperado=total_recuperado,
        valor_total_risco=valor_total_risco,
    )


def classificar_evento(evento: EventoAgrupado) -> bool:
    """DRO001231: indica se o evento deve ser individualizado."""
    if not evento.consistente or evento.total_perda_efetiva is None:
        return False
    limiar_atingido = (
        evento.total_perda_efetiva + evento.total_provisao
        >= LIMIAR_INDIVIDUALIZACAO
    )
    risco_nao_coberto = (
        calcular_soma_risco(evento) >= LIMIAR_RISCO_NAO_COBERTO
    )
    return limiar_atingido or risco_nao_coberto


def calcular_intervalo_semestre(data_base: str) -> tuple[date, date]:
    """Retorna o primeiro e o ultimo dia do semestre da data-base."""
    ano, mes = (int(parte) for parte in data_base.split("-"))
    if mes == 6:
        return date(ano, 1, 1), date(ano, 6, 30)
    return date(ano, 7, 1), date(ano, 12, 31)


def calcular_saldos_diarios(
    evento: EventoAgrupado, campo: str
) -> list[tuple[date, Decimal]]:
    """Agrega um movimento contabil por data de contabilizacao."""
    por_dia: dict[date, Decimal] = {}
    for contabilizacao in evento.contabilizacoes:
        if contabilizacao.data_contabilizacao is None:
            continue
        valor = getattr(contabilizacao, campo)
        por_dia[contabilizacao.data_contabilizacao] = (
            por_dia.get(contabilizacao.data_contabilizacao, Decimal("0.00"))
            + valor
        )
    return sorted(por_dia.items())


def saldo_acumulado_fica_negativo(
    evento: EventoAgrupado, campo: str
) -> bool:
    """Informa se o saldo acumulado por fechamento diario fica negativo."""
    saldo = Decimal("0.00")
    for _dia, valor_do_dia in calcular_saldos_diarios(evento, campo):
        saldo += valor_do_dia
        if saldo < 0:
            return True
    return False
