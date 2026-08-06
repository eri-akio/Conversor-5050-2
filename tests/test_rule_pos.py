"""Testes da Fase 6: consolidacao e criticas locais de pos-processamento
(src/rule_pos.py)."""

from __future__ import annotations

from decimal import Decimal

from src.builders import consolidar_eventos, montar_evento, normalizar_linha_base
from src.reader import BASE_COLUNAS
from src.rules_local import validar_datas_apos_data_base
from src.rules_pre import validar_categoria_nivel2_obrigatoria
from src.rule_pos import (
    validar_categorias_compativeis,
    validar_contabilizacao_anterior_a_descoberta,
    validar_contingencia_individual_sem_probabilidade,
    validar_evento,
    validar_fraude_com_provisao,
    validar_media_semestral,
    validar_media_total,
    validar_perda_consolidada_minima,
    validar_perda_minima,
    validar_po_re_com_risco_zero,
    validar_pr_com_provisao_zero,
    validar_primeira_contabilizacao_sem_categoria,
    validar_provisao_consolidada_minima,
    validar_provisao_minima,
    validar_recuperacao_dentro_do_limite,
    validar_recuperacao_maxima,
    validar_saldo_acumulado_perda,
    validar_saldo_acumulado_provisao,
    validar_totais_batem_com_contabilizacoes,
)

CAMPOS_EVENTO_PADRAO = {
    "idEvento": "EVT-1",
    "categoriaNivel1": "1",
    "categoriaNivel2": "11",
    "tipoAvaliacao": "NA",
    "unidadeNegocio": "1",
    "dataOcorrencia": "2025-06-10",
    "dataDescoberta": "2025-06-10",
    "naturezaContingencia": "NA",
    "codSistemaOrigem": "SIS1",
    "nomeSistema": "Sistema Um",
    "codigoEventoOrigem": "COD-1",
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


def _evento(id_evento: str, linhas: list):
    return montar_evento(id_evento, linhas)


def test_pr_com_provisao_zero_gera_dro000004() -> None:
    linhas = [
        _linha(
            2,
            tipoAvaliacao="I",
            probabilidadePerda="PR",
            valorRisco=100,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_pr_com_provisao_zero(evento).codigo == "DRO000004"


def test_po_com_risco_zero_gera_dro000005() -> None:
    linhas = [
        _linha(
            2,
            tipoAvaliacao="I",
            probabilidadePerda="PO",
            valorRisco=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_po_re_com_risco_zero(evento).codigo == "DRO000005"


def test_dro000004_nao_dispara_para_avaliacao_massificada() -> None:
    evento = _evento(
        "EVT-1",
        [
            _linha(
                2,
                tipoAvaliacao="M",
                naturezaContingencia="TRI",
                probabilidadePerda="PR",
                valorRisco=100,
                dataContabilizacao="2025-06-15",
                valorPerdaEfetiva=0,
                valorProvisao=0,
                valorRecuperacao=0,
            )
        ],
    )

    assert validar_pr_com_provisao_zero(evento) is None


def test_dro000005_nao_dispara_para_avaliacao_massificada() -> None:
    evento = _evento(
        "EVT-1",
        [
            _linha(
                2,
                tipoAvaliacao="M",
                naturezaContingencia="TRI",
                probabilidadePerda="PO",
                valorRisco=0,
            )
        ],
    )

    assert validar_po_re_com_risco_zero(evento) is None


def test_contingencia_individual_sem_probabilidade_gera_dro000003() -> None:
    evento = _evento(
        "EVT-1", [_linha(2, tipoAvaliacao="I", dataOcorrencia="2025-06-10")]
    )

    assert (
        validar_contingencia_individual_sem_probabilidade(evento).codigo
        == "DRO000003"
    )


def test_primeira_contabilizacao_sem_categoria_gera_dro000009() -> None:
    linhas = [
        _linha(
            2,
            categoriaNivel2=None,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    ocorrencia = validar_primeira_contabilizacao_sem_categoria(evento)

    assert ocorrencia.codigo == "DRO000009"
    assert "dataOcorrencia" in ocorrencia.detalhe


def test_dro000009_dispara_mesmo_com_dataocorrencia_antes_de_2021() -> None:
    """Auditoria DRO001212 vs DRO000009: um evento pode ter ocorrido
    antes de 2021 (isentando-o da DRO001212, que usa dataOcorrencia) mas
    ter sido contabilizado so depois de 2021 -- nesse caso a DRO000009
    (que usa min(dataContabilizacao)) dispara mesmo assim. Nao e
    conflito: sao duas criticas oficiais distintas, cada uma com sua
    propria data-gatilho."""

    linhas = [
        _linha(
            2,
            dataOcorrencia="2020-01-06",
            categoriaNivel2=None,
            dataContabilizacao="2025-11-01",
            valorPerdaEfetiva=0,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_categoria_nivel2_obrigatoria(evento) is None

    ocorrencia = validar_primeira_contabilizacao_sem_categoria(evento)
    assert ocorrencia.codigo == "DRO000009"
    assert "2020-01-06" in ocorrencia.detalhe


def test_primeira_contabilizacao_exatamente_em_2021_01_01_nao_gera_dro000009() -> (
    None
):
    """#6: a planilha oficial usa min(dataContabilizacao) > 01/01/2021
    (estrito) -- a data exata deve ser isenta."""

    linhas = [
        _linha(
            2,
            categoriaNivel2=None,
            dataContabilizacao="2021-01-01",
            valorPerdaEfetiva=0,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_primeira_contabilizacao_sem_categoria(evento) is None


def test_primeira_contabilizacao_em_2021_01_02_gera_dro000009() -> None:
    linhas = [
        _linha(
            2,
            categoriaNivel2=None,
            dataContabilizacao="2021-01-02",
            valorPerdaEfetiva=0,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert (
        validar_primeira_contabilizacao_sem_categoria(evento).codigo
        == "DRO000009"
    )


def test_contabilizacao_anterior_a_descoberta_gera_dro000010() -> None:
    linhas = [
        _linha(
            2,
            dataDescoberta="2025-06-10",
            dataContabilizacao="2025-06-01",
            valorPerdaEfetiva=0,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert (
        validar_contabilizacao_anterior_a_descoberta(evento).codigo
        == "DRO000010"
    )


def test_perda_abaixo_de_dez_negativos_gera_dro000011() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=-20,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_perda_minima(evento).codigo == "DRO000011"


def test_provisao_abaixo_de_dez_negativos_gera_dro000012() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=-20,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_provisao_minima(evento).codigo == "DRO000012"


def test_recuperacao_positiva_gera_dro000013() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=100,
            valorProvisao=0,
            valorRecuperacao=50,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_recuperacao_maxima(evento).codigo == "DRO000013"


def test_recuperacao_acima_do_limite_gera_dro000014() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=100,
            valorProvisao=0,
            valorRecuperacao=-200,
            fonteRecuperacao="S",
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_recuperacao_dentro_do_limite(evento).codigo == "DRO000014"


def test_dro000014_usa_soma_literal_sem_modulo_na_perda_bruta() -> None:
    evento = _evento(
        "EVT-1",
        [
            _linha(
                2,
                dataContabilizacao="2025-06-15",
                valorPerdaEfetiva=-5,
                valorProvisao=0,
                valorRecuperacao=-1,
                fonteRecuperacao="S",
            )
        ],
    )

    ocorrencia = validar_recuperacao_dentro_do_limite(evento)
    assert ocorrencia is not None
    assert ocorrencia.codigo == "DRO000014"


def test_totais_sempre_batem_com_contabilizacoes_por_construcao() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=100,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_totais_batem_com_contabilizacoes(evento) is None


def test_categorias_incompativeis_gera_dro000021() -> None:
    evento = _evento(
        "EVT-1", [_linha(2, categoriaNivel1="1", categoriaNivel2="21")]
    )

    assert validar_categorias_compativeis(evento).codigo == "DRO000021"


def test_categorias_compativeis_nao_gera_ocorrencia() -> None:
    evento = _evento(
        "EVT-1", [_linha(2, categoriaNivel1="1", categoriaNivel2="11")]
    )

    assert validar_categorias_compativeis(evento) is None


def test_saldo_acumulado_de_perda_fica_negativo_gera_dro000023() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-01",
            valorPerdaEfetiva=100,
            valorProvisao=0,
            valorRecuperacao=0,
        ),
        _linha(
            3,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=-150,
            valorProvisao=0,
            valorRecuperacao=0,
        ),
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_saldo_acumulado_perda(evento).codigo == "DRO000023"


def test_saldo_acumulado_de_perda_positivo_nao_gera_ocorrencia() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-01",
            valorPerdaEfetiva=100,
            valorProvisao=0,
            valorRecuperacao=0,
        ),
        _linha(
            3,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=-50,
            valorProvisao=0,
            valorRecuperacao=0,
        ),
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_saldo_acumulado_perda(evento) is None


def test_saldo_acumulado_de_provisao_negativo_gera_dro000024_como_aviso() -> (
    None
):
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-01",
            valorPerdaEfetiva=0,
            valorProvisao=100,
            valorRecuperacao=0,
        ),
        _linha(
            3,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=-150,
            valorRecuperacao=0,
        ),
    ]
    evento = _evento("EVT-1", linhas)

    ocorrencia = validar_saldo_acumulado_provisao(evento)

    assert ocorrencia.codigo == "DRO000024"
    assert ocorrencia.tipo == "AVISO"


def test_lancamentos_no_mesmo_dia_sao_somados_antes_de_acumular() -> None:
    # 100 e -150 no MESMO dia devem ser somados (-50) antes de acumular,
    # nao avaliados em uma ordem intradiaria arbitraria.
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-01",
            valorPerdaEfetiva=100,
            valorProvisao=0,
            valorRecuperacao=0,
        ),
        _linha(
            3,
            dataContabilizacao="2025-06-01",
            valorPerdaEfetiva=-150,
            valorProvisao=0,
            valorRecuperacao=0,
        ),
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_saldo_acumulado_perda(evento).codigo == "DRO000023"


def test_validar_evento_sem_problemas_retorna_lista_vazia() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=100,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_evento(evento) == []


def test_validar_evento_inconsistente_retorna_lista_vazia() -> None:
    linhas = [
        _linha(2, categoriaNivel1="1"),
        _linha(3, categoriaNivel1="2"),
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_evento(evento) == []


def test_consolidar_eventos_agrupa_por_categoria_e_soma_totais() -> None:
    linhas_evt1 = [
        _linha(
            2,
            idEvento="EVT-1",
            categoriaNivel1="1",
            categoriaNivel2="11",
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=Decimal("10.00"),
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    linhas_evt2 = [
        _linha(
            3,
            idEvento="EVT-2",
            categoriaNivel1="1",
            categoriaNivel2="12",
            dataContabilizacao="2025-06-16",
            valorPerdaEfetiva=Decimal("20.00"),
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    eventos = {
        "EVT-1": _evento("EVT-1", linhas_evt1),
        "EVT-2": _evento("EVT-2", linhas_evt2),
    }

    consolidados = consolidar_eventos(eventos, "2025-06")

    assert set(consolidados) == {"1"}
    consolidado = consolidados["1"]
    assert consolidado.num_eventos_total == 2
    assert consolidado.perda_efetiva_total == Decimal("30.00")
    assert consolidado.num_eventos_semestre == 2
    assert consolidado.perda_efetiva_semestre == Decimal("30.00")


def test_consolidar_eventos_exclui_eventos_individualizados() -> None:
    linhas_individualizado = [
        _linha(
            2,
            idEvento="EVT-1",
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=Decimal("5000.00"),
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    eventos = {"EVT-1": _evento("EVT-1", linhas_individualizado)}

    consolidados = consolidar_eventos(eventos, "2025-06")

    assert consolidados == {}


def test_consolidar_eventos_semestre_diferente_nao_conta_no_semestre() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-12-15",
            valorPerdaEfetiva=Decimal("10.00"),
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    eventos = {"EVT-1": _evento("EVT-1", linhas)}

    consolidados = consolidar_eventos(eventos, "2025-06")

    consolidado = consolidados["1"]
    assert consolidado.num_eventos_total == 1
    assert consolidado.num_eventos_semestre == 0
    assert consolidado.perda_efetiva_semestre == Decimal("0.00")


def test_consolidar_eventos_separa_quantidade_e_valores_do_semestre() -> None:
    linhas = [
        _linha(
            2,
            idEvento="EVT-1",
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=Decimal("10.00"),
            valorProvisao=0,
            valorRecuperacao=0,
        ),
        _linha(
            3,
            idEvento="EVT-1",
            dataContabilizacao="2025-12-15",
            valorPerdaEfetiva=Decimal("20.00"),
            valorProvisao=0,
            valorRecuperacao=0,
        ),
    ]
    eventos = {"EVT-1": _evento("EVT-1", linhas)}

    consolidados_1s = consolidar_eventos(eventos, "2025-06")
    consolidados_2s = consolidar_eventos(eventos, "2025-12")

    assert consolidados_1s["1"].num_eventos_semestre == 1
    assert consolidados_1s["1"].perda_efetiva_semestre == Decimal("10.00")
    assert consolidados_2s["1"].num_eventos_semestre == 0
    assert consolidados_2s["1"].perda_efetiva_semestre == Decimal("20.00")


def test_consolidado_semestral_soma_apenas_movimentos_do_periodo() -> None:
    linhas = [
        _linha(
            2,
            idEvento="EVT-1",
            dataContabilizacao="2024-12-20",
            valorPerdaEfetiva=0,
            valorProvisao=700,
            valorRecuperacao=0,
        ),
        _linha(
            3,
            idEvento="EVT-1",
            dataContabilizacao="2025-02-10",
            valorPerdaEfetiva=30,
            valorProvisao=200,
            valorRecuperacao=0,
        ),
    ]
    consolidados = consolidar_eventos(
        {"EVT-1": _evento("EVT-1", linhas)}, "2025-06"
    )

    consolidado = consolidados["1"]
    assert consolidado.num_eventos_semestre == 0
    assert consolidado.perda_efetiva_semestre == Decimal("30.00")
    assert consolidado.provisao_semestre == Decimal("200.00")
    assert consolidado.provisao_total == Decimal("900.00")


def test_media_semestral_acima_do_limite_gera_dro000001() -> None:
    from src.models import EventoConsolidado

    consolidado = EventoConsolidado(
        categoria_nivel1="1",
        num_eventos_total=1,
        num_eventos_semestre=1,
        perda_efetiva_total=Decimal("2000.00"),
        perda_efetiva_semestre=Decimal("2000.00"),
        provisao_total=Decimal("0.00"),
        provisao_semestre=Decimal("0.00"),
    )

    assert validar_media_semestral(consolidado).codigo == "DRO000001"


def test_media_total_acima_do_limite_gera_dro000002() -> None:
    from src.models import EventoConsolidado

    consolidado = EventoConsolidado(
        categoria_nivel1="1",
        num_eventos_total=1,
        num_eventos_semestre=0,
        perda_efetiva_total=Decimal("2000.00"),
        perda_efetiva_semestre=Decimal("0.00"),
        provisao_total=Decimal("0.00"),
        provisao_semestre=Decimal("0.00"),
    )

    assert validar_media_total(consolidado).codigo == "DRO000002"


def test_perda_consolidada_minima_gera_dro000018() -> None:
    from src.models import EventoConsolidado

    consolidado = EventoConsolidado(
        categoria_nivel1="1",
        num_eventos_total=1,
        num_eventos_semestre=0,
        perda_efetiva_total=Decimal("-20.00"),
        perda_efetiva_semestre=Decimal("0.00"),
        provisao_total=Decimal("0.00"),
        provisao_semestre=Decimal("0.00"),
    )

    assert validar_perda_consolidada_minima(consolidado).codigo == "DRO000018"


def test_provisao_consolidada_minima_gera_dro000019() -> None:
    from src.models import EventoConsolidado

    consolidado = EventoConsolidado(
        categoria_nivel1="1",
        num_eventos_total=1,
        num_eventos_semestre=0,
        perda_efetiva_total=Decimal("0.00"),
        perda_efetiva_semestre=Decimal("0.00"),
        provisao_total=Decimal("-20.00"),
        provisao_semestre=Decimal("0.00"),
    )

    assert (
        validar_provisao_consolidada_minima(consolidado).codigo
        == "DRO000019"
    )


def test_validar_datas_apos_data_base_dataocorrencia_posterior() -> None:
    """P3: dataOcorrencia posterior ao fim do semestre da dataBase."""
    linhas = [
        _linha(
            2,
            dataOcorrencia="2025-07-15",
            dataDescoberta="2025-07-15",
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=100,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    ocorrencias = validar_datas_apos_data_base(evento, "2025-06")

    assert any(o.codigo == "BASE-DATA-PERIODO-001" for o in ocorrencias)


def test_validar_datas_apos_data_base_datacontabilizacao_posterior() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-12-15",
            valorPerdaEfetiva=100,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    ocorrencias = validar_datas_apos_data_base(evento, "2025-06")

    assert any(o.codigo == "BASE-DATA-PERIODO-001" for o in ocorrencias)


def test_validar_datas_apos_data_base_dentro_do_periodo_nao_gera_ocorrencia() -> (
    None
):
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=100,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_datas_apos_data_base(evento, "2025-06") == []


def test_validar_fraude_com_provisao_gera_dro000032() -> None:
    """P6: categoriaNivel1 em {1,2} e totalProvisao>0, sem restricao a
    eventos individualizados (planilha oficial, linha 27)."""

    linhas = [
        _linha(
            2,
            categoriaNivel1="1",
            categoriaNivel2="11",
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=100,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    ocorrencia = validar_fraude_com_provisao(evento)

    assert ocorrencia is not None
    assert ocorrencia.codigo == "DRO000032"


def test_validar_fraude_com_provisao_categoria_fora_do_dominio_nao_gera() -> (
    None
):
    linhas = [
        _linha(
            2,
            categoriaNivel1="3",
            categoriaNivel2="31",
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=100,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_fraude_com_provisao(evento) is None


def test_validar_fraude_com_provisao_sem_provisao_nao_gera() -> None:
    linhas = [
        _linha(
            2,
            categoriaNivel1="1",
            categoriaNivel2="11",
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=100,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_fraude_com_provisao(evento) is None
