"""Testes de builders, regras locais e calculos puros da Fase 4."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.builders import (
    agrupar_linhas_por_evento,
    construir_probabilidades_validas,
    montar_evento as construir_evento,
    normalizar_linha_base,
)
from src.calculations import calcular_totais
from src.reader import BASE_COLUNAS
from src.rules_local import (
    detectar_colisoes_id_evento,
    validar_contabilizacao_antes_pre,
    validar_contabilizacao_depois_pre,
    validar_contabilizacoes_linhas,
    validar_convencao_de_sinal,
    validar_probabilidades_do_evento,
    validar_probabilidades_linhas,
    validar_referencias_linha,
    validar_sistemas_e_contas_globais,
    verificar_consistencia,
)
from src.rules_pre import (
    validar_contabilizacao_pre,
    validar_provisao_avaliacao_na,
    validar_referencias_linha_pre,
)


def extrair_probabilidades(linhas):
    return construir_probabilidades_validas(linhas), validar_probabilidades_linhas(linhas)


def validar_sistemas_e_contas(linhas):
    ocorrencias = []
    for linha in linhas:
        ocorrencias.extend(validar_referencias_linha(linha))
        ocorrencias.extend(validar_referencias_linha_pre(linha))
    ocorrencias.extend(validar_sistemas_e_contas_globais(linhas))
    return ocorrencias


def montar_evento(id_evento, linhas):
    evento = construir_evento(id_evento, linhas)
    ocorrencias = []
    _ok, _campos, conflito = verificar_consistencia(id_evento, linhas)
    if conflito is not None:
        ocorrencias.append(conflito)
    ocorrencias.extend(validar_probabilidades_linhas(linhas))
    ocorrencias.extend(validar_contabilizacoes_linhas(linhas))
    if evento.consistente:
        tipo = evento.valor_evento("tipoAvaliacao")
        ocorrencias.extend(validar_probabilidades_do_evento(
            id_evento, tipo, evento.probabilidades
        ))
        data = evento.valor_evento("dataOcorrencia")
        for contabilizacao in evento.contabilizacoes:
            ocorrencias.extend(validar_contabilizacao_antes_pre(id_evento, contabilizacao))
            ocorrencias.extend(validar_contabilizacao_pre(id_evento, contabilizacao, data))
            ocorrencias.extend(validar_contabilizacao_depois_pre(id_evento, contabilizacao))
        ocorrencias.extend(validar_provisao_avaliacao_na(evento))
        sinal = validar_convencao_de_sinal(evento)
        if sinal is not None:
            ocorrencias.append(sinal)
    return evento, ocorrencias

CAMPOS_EVENTO_PADRAO = {
    "idEvento": "EVT-1",
    "categoriaNivel1": "1",
    "categoriaNivel2": "11",
    "tipoAvaliacao": "M",
    "unidadeNegocio": "1",
    "dataOcorrencia": "2025-06-10",
    "naturezaContingencia": "NA",
    "codSistemaOrigem": "SIS1",
    "nomeSistema": "Sistema Um",
    "codigoEventoOrigem": "COD-1",
    "idBacen": "Z0000001",
}


def _linha(numero_linha: int, **sobrescritas: object) -> "LinhaNormalizada":  # noqa: F821
    valores_por_coluna = dict(CAMPOS_EVENTO_PADRAO)
    valores_por_coluna.update(sobrescritas)
    valores = tuple(valores_por_coluna.get(coluna) for coluna in BASE_COLUNAS)
    return normalizar_linha_base(numero_linha, BASE_COLUNAS, valores)


def test_agrupar_linhas_por_evento() -> None:
    linhas = [
        _linha(2, idEvento="EVT1"),
        _linha(3, idEvento="EVT1"),
        _linha(4, idEvento="EVT2"),
    ]

    grupos = agrupar_linhas_por_evento(linhas)

    assert set(grupos) == {"EVT1", "EVT2"}
    assert len(grupos["EVT1"]) == 2
    assert len(grupos["EVT2"]) == 1


def test_detectar_colisoes_id_evento_com_duas_variantes() -> None:
    """P8: 'IND-0001' e 'IND0001' colidem no mesmo idEvento normalizado
    (so o hifen e removido)."""

    linhas = [
        _linha(2, idEvento="IND-0001"),
        _linha(3, idEvento="IND0001"),
    ]

    ocorrencias = detectar_colisoes_id_evento(linhas)

    assert len(ocorrencias) == 1
    assert ocorrencias[0].codigo == "BASE-IDEVENTO-COLISAO-001"
    assert ocorrencias[0].linhas == (2, 3)


def test_detectar_colisoes_id_evento_com_tres_variantes() -> None:
    linhas = [
        _linha(2, idEvento="IND-0001"),
        _linha(3, idEvento="IND--0001"),
        _linha(4, idEvento="IND0001"),
    ]

    ocorrencias = detectar_colisoes_id_evento(linhas)

    assert len(ocorrencias) == 1
    assert ocorrencias[0].linhas == (2, 3, 4)


def test_detectar_colisoes_id_evento_ignora_espacos_externos() -> None:
    """Comparacao canonica: ' IND-0001 ' e 'IND-0001' sao a mesma origem
    apos strip(), nao uma colisao."""

    linhas = [
        _linha(2, idEvento="IND-0001"),
        _linha(3, idEvento=" IND-0001 "),
    ]

    ocorrencias = detectar_colisoes_id_evento(linhas)

    assert ocorrencias == []


def test_detectar_colisoes_id_evento_sem_colisao() -> None:
    linhas = [
        _linha(2, idEvento="IND-0001"),
        _linha(3, idEvento="IND-0002"),
    ]

    ocorrencias = detectar_colisoes_id_evento(linhas)

    assert ocorrencias == []


def test_normalizar_linha_base_aceita_data_no_formato_brasileiro() -> None:
    linha = _linha(2, dataOcorrencia="05/12/2025")

    assert linha.valor("dataOcorrencia") == date(2025, 12, 5)


def test_normalizar_linha_base_remove_hifen_do_id_evento() -> None:
    linha = _linha(2, idEvento="IND-0001")

    assert linha.valor("idEvento") == "IND0001"


def test_normalizar_linha_base_extrai_id_bacen_rotulado() -> None:
    linha = _linha(2, idBacen="Z1234567 - Banco Alfa")

    assert linha.valor("idBacen") == "Z1234567"


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [("PO - Possível", "PO"), ("PR - Provável", "PR"), ("RE - Remoto", "RE")],
)
def test_normalizar_linha_base_extrai_probabilidade_rotulada(
    valor: str, esperado: str
) -> None:
    linha = _linha(2, probabilidadePerda=valor, valorRisco=100)

    assert linha.valor("probabilidadePerda") == esperado


def test_normalizar_linha_base_remove_pontos_das_contas() -> None:
    linha = _linha(
        2,
        contaBalAnaliticoDebito="819.951.010.400.000.000.000.003",
        contaCosifDebito="819.951.0104",
    )

    assert linha.valor("contaBalAnaliticoDebito") == "819951010400000000000003"
    assert linha.valor("contaCosifDebito") == "8199510104"


def test_normalizar_linha_base_remove_pontos_e_hifens_das_contas() -> None:
    linha = _linha(
        2,
        contaBalAnaliticoCredito="8.1.9.99.00-6",
        contaCosifCredito="81-99.00-6",
    )

    assert linha.valor("contaBalAnaliticoCredito") == "81999006"
    assert linha.valor("contaCosifCredito") == "8199006"


@pytest.mark.parametrize(
    ("campo", "valor", "esperado"),
    [
        ("tipoAvaliacao", "m", "M"),
        ("naturezaContingencia", "tri", "TRI"),
        ("riscoAssociado", "na", "NA"),
        ("ligadoRiscoSocioAmbiental", "s", "S"),
        ("ligadoRiscoCibernetico", "n", "N"),
        ("negocioDescontinuado", "n", "N"),
        ("fonteRecuperacao", "o", "O"),
    ],
)
def test_normalizar_linha_base_maiusculiza_campos_de_dominio_fechado(
    campo: str, valor: str, esperado: str
) -> None:
    linha = _linha(2, **{campo: valor})

    assert linha.valor(campo) == esperado


def test_normalizar_linha_base_maiusculiza_probabilidade_rotulada() -> None:
    linha = _linha(2, probabilidadePerda="pr - provável", valorRisco=100)

    assert linha.valor("probabilidadePerda") == "PR"


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("idEvento", "EventoAbc01"),
        ("codSistemaOrigem", "SisOrigem01"),
    ],
)
def test_normalizar_linha_base_preserva_caixa_de_campos_de_identidade(
    campo: str, valor: str
) -> None:
    linha = _linha(2, **{campo: valor})

    assert linha.valor(campo) == valor


def test_normalizar_linha_base_id_bacen_rotulado_preserva_caixa() -> None:
    linha = _linha(2, idBacen="z1234567 - Banco Teste")

    assert linha.valor("idBacen") == "z1234567"


def test_conflito_entre_linhas_gera_base_agr_001() -> None:
    linhas = [
        _linha(2, categoriaNivel1="1"),
        _linha(3, categoriaNivel1="2"),
    ]

    evento, ocorrencias = montar_evento("EVT-1", linhas)

    assert evento.consistente is False
    assert "categoriaNivel1" in evento.campos_conflitantes
    assert any(o.codigo == "BASE-AGR-001" for o in ocorrencias)


def test_evento_consistente_sem_conflito() -> None:
    linhas = [_linha(2), _linha(3)]

    evento, ocorrencias = montar_evento("EVT-1", linhas)

    assert evento.consistente is True
    assert not any(o.codigo == "BASE-AGR-001" for o in ocorrencias)


def test_probabilidade_incompleta_gera_base_prob_001() -> None:
    linhas = [_linha(2, probabilidadePerda="PR", valorRisco=None)]

    _, ocorrencias = montar_evento("EVT-1", linhas)

    assert any(o.codigo == "BASE-PROB-001" for o in ocorrencias)


def test_ate_tres_probabilidades_validas_sao_aceitas() -> None:
    linhas = [
        _linha(2, tipoAvaliacao="I", probabilidadePerda="PR", valorRisco=100),
        _linha(3, tipoAvaliacao="I", probabilidadePerda="PO", valorRisco=200),
        _linha(4, tipoAvaliacao="I", probabilidadePerda="RE", valorRisco=300),
    ]

    evento, ocorrencias = montar_evento("EVT-1", linhas)

    assert len(evento.probabilidades) == 3
    assert not any(o.codigo == "BASE-PROB-003" for o in ocorrencias)


def test_quarta_probabilidade_repetida_gera_base_prob_003() -> None:
    linhas = [
        _linha(2, tipoAvaliacao="I", probabilidadePerda="PR", valorRisco=100),
        _linha(3, tipoAvaliacao="I", probabilidadePerda="PO", valorRisco=200),
        _linha(4, tipoAvaliacao="I", probabilidadePerda="RE", valorRisco=300),
        _linha(5, tipoAvaliacao="I", probabilidadePerda="PR", valorRisco=400),
    ]

    _, ocorrencias = montar_evento("EVT-1", linhas)

    assert any(o.codigo == "BASE-PROB-003" for o in ocorrencias)


def test_probabilidade_em_avaliacao_na_gera_base_prob_002() -> None:
    linhas = [
        _linha(
            2,
            tipoAvaliacao="NA",
            probabilidadePerda="PR",
            valorRisco=100,
        )
    ]

    _, ocorrencias = montar_evento("EVT-1", linhas)

    assert any(o.codigo == "BASE-PROB-002" for o in ocorrencias)


def test_contabilizacao_com_tres_movimentos_zerados_gera_base_cont_sem_mov() -> (
    None
):
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]

    _, ocorrencias = montar_evento("EVT-1", linhas)

    assert any(o.codigo == "BASE-CONT-SEM-MOV-001" for o in ocorrencias)


def test_contabilizacao_incompleta_gera_base_cont_obr_001() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=100,
            valorProvisao=None,
            valorRecuperacao=None,
        )
    ]

    _, ocorrencias = montar_evento("EVT-1", linhas)

    assert any(o.codigo == "BASE-CONT-OBR-001" for o in ocorrencias)


def test_estorno_de_perda_nao_gera_regra_local_de_sinal() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-14",
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

    evento, ocorrencias = montar_evento("EVT-1", linhas)

    assert evento.total_perda_efetiva == Decimal("50.00")
    assert not any(o.codigo.startswith("BASE-SINAL-") for o in ocorrencias)

def test_recuperacao_positiva_gera_dro001411() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=100,
            valorProvisao=0,
            valorRecuperacao=50,
        )
    ]

    _, ocorrencias = montar_evento("EVT-1", linhas)

    assert any(o.codigo == "DRO001411" for o in ocorrencias)


def test_recuperacao_negativa_sem_fonte_gera_dro001421() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=100,
            valorProvisao=0,
            valorRecuperacao=-50,
            fonteRecuperacao=None,
        )
    ]

    _, ocorrencias = montar_evento("EVT-1", linhas)

    assert any(o.codigo == "DRO001421" for o in ocorrencias)


def test_recuperacao_negativa_sem_fonte_antes_de_2021_nao_gera_dro001421() -> (
    None
):
    """P5: DRO001421 so vale para dataOcorrencia >= 2021-01-01 (planilha
    oficial de criticas de pre-processamento, linha 27)."""

    linhas = [
        _linha(
            2,
            dataOcorrencia="2020-06-10",
            dataContabilizacao="2020-06-15",
            valorPerdaEfetiva=100,
            valorProvisao=0,
            valorRecuperacao=-50,
            fonteRecuperacao=None,
        )
    ]

    _, ocorrencias = montar_evento("EVT-1", linhas)

    assert not any(o.codigo == "DRO001421" for o in ocorrencias)


def test_recuperacao_negativa_com_fonte_nao_gera_dro001421() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=100,
            valorProvisao=0,
            valorRecuperacao=-50,
            fonteRecuperacao="S",
        )
    ]

    _, ocorrencias = montar_evento("EVT-1", linhas)

    assert not any(o.codigo == "DRO001421" for o in ocorrencias)


def test_recuperacao_zero_com_fonte_preenchida_gera_base_rec_fonte_001() -> (
    None
):
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=100,
            valorProvisao=0,
            valorRecuperacao=0,
            fonteRecuperacao="S",
        )
    ]

    _, ocorrencias = montar_evento("EVT-1", linhas)

    assert any(o.codigo == "BASE-REC-FONTE-001" for o in ocorrencias)


def test_provisao_diferente_de_zero_em_avaliacao_na_gera_dro001301() -> None:
    linhas = [
        _linha(
            2,
            tipoAvaliacao="NA",
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=100,
            valorRecuperacao=0,
        )
    ]

    _, ocorrencias = montar_evento("EVT-1", linhas)

    assert any(o.codigo == "DRO001301" for o in ocorrencias)


def test_totais_sao_calculados_para_evento_consistente() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=100,
            valorProvisao=50,
            valorRecuperacao=-10,
        ),
        _linha(
            3,
            dataContabilizacao="2025-06-16",
            valorPerdaEfetiva=200,
            valorProvisao=0,
            valorRecuperacao=0,
        ),
    ]

    evento, _ = montar_evento("EVT-1", linhas)

    assert evento.total_perda_efetiva == Decimal("300")
    assert evento.total_provisao == Decimal("50")
    assert evento.total_recuperado == Decimal("-10")


def test_valor_total_risco_so_e_calculado_para_avaliacao_individual() -> None:
    # valorRisco + totalProvisao >= 10_000_000,00 (piso de emissao, P4:
    # Instrucoes de Preenchimento 12/2020, item "k") para que
    # valorTotalRisco seja de fato emitido.
    linhas_i = [
        _linha(
            2,
            tipoAvaliacao="I",
            probabilidadePerda="PR",
            valorRisco=9999500,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=500,
            valorRecuperacao=0,
        )
    ]
    evento_i, _ = montar_evento("EVT-1", linhas_i)
    assert evento_i.valor_total_risco == Decimal("10000000")

    linhas_m = [_linha(2, tipoAvaliacao="M")]
    evento_m, _ = montar_evento("EVT-2", linhas_m)
    assert evento_m.valor_total_risco is None


def test_valor_total_risco_omitido_abaixo_do_piso_de_10_milhoes() -> None:
    """P4: mesmo com tipoAvaliacao=I, valorTotalRisco fica None quando o
    valor calculado nao atinge R$10.000.000,00 (nao e emitido no XML)."""

    linhas = [
        _linha(
            2,
            tipoAvaliacao="I",
            probabilidadePerda="PR",
            valorRisco=9999999.99,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento, _ = montar_evento("EVT-1", linhas)
    assert evento.valor_total_risco is None


def test_totais_nao_sao_calculados_quando_evento_inconsistente() -> None:
    linhas = [
        _linha(2, categoriaNivel1="1"),
        _linha(3, categoriaNivel1="2"),
    ]

    evento, _ = montar_evento("EVT-1", linhas)

    assert evento.total_perda_efetiva is None


def test_total_de_provisao_no_limiar_nao_gera_regra_local_de_sinal() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=5,
            valorProvisao=0,
            valorRecuperacao=0,
        ),
        _linha(
            3,
            dataContabilizacao="2025-06-16",
            valorPerdaEfetiva=0,
            valorProvisao=-10,
            valorRecuperacao=0,
        ),
    ]

    evento, ocorrencias = montar_evento("EVT-1", linhas)

    assert evento.total_provisao == Decimal("-10")
    assert not any(o.codigo.startswith("BASE-SINAL-") for o in ocorrencias)

def test_total_negativo_dentro_da_tolerancia_fica_para_regra_oficial() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=-5,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]

    evento, ocorrencias = montar_evento("EVT-1", linhas)

    assert evento.total_perda_efetiva == Decimal("-5")
    assert not any(o.codigo.startswith("BASE-SINAL-") for o in ocorrencias)

def test_sistema_com_nomes_diferentes_gera_base_sis_001() -> None:
    linhas = [
        _linha(2, idEvento="EVT-1", codSistemaOrigem="SIS1", nomeSistema="Nome A"),
        _linha(3, idEvento="EVT-2", codSistemaOrigem="SIS1", nomeSistema="Nome B"),
    ]

    ocorrencias = validar_sistemas_e_contas(linhas)

    assert any(o.codigo == "BASE-SIS-001" for o in ocorrencias)


def test_conta_com_nomes_diferentes_gera_base_conta_001() -> None:
    linhas = [
        _linha(
            2,
            idEvento="EVT-1",
            contaBalAnaliticoDebito="123",
            nomeContaDebito="Conta A",
        ),
        _linha(
            3,
            idEvento="EVT-2",
            contaBalAnaliticoDebito="123",
            nomeContaDebito="Conta B",
        ),
    ]

    ocorrencias = validar_sistemas_e_contas(linhas)

    assert any(o.codigo == "BASE-CONTA-001" for o in ocorrencias)


def test_cosif_fora_do_formato_gera_base_cosif_form_001() -> None:
    linhas = [
        _linha(
            2,
            contaBalAnaliticoDebito="123",
            contaCosifDebito="123",
        )
    ]

    ocorrencias = validar_sistemas_e_contas(linhas)

    assert any(o.codigo == "BASE-COSIF-FORM-001" for o in ocorrencias)


def test_cosif_com_digitos_unicode_fullwidth_gera_base_cosif_form_001() -> (
    None
):
    """Correcao transversal: \\d casaria digitos Unicode fullwidth
    (U+FF10-FF19), que o XSD ([0-9] estrito) nao aceita."""

    linhas = [
        _linha(
            2,
            contaBalAnaliticoDebito="123",
            contaCosifDebito="１２３４５６７８",
        )
    ]

    ocorrencias = validar_sistemas_e_contas(linhas)

    assert any(o.codigo == "BASE-COSIF-FORM-001" for o in ocorrencias)


def test_cosif_sem_conta_interna_gera_dro001443() -> None:
    linhas = [
        _linha(
            2,
            contaBalAnaliticoDebito=None,
            contaCosifDebito="12345678",
        )
    ]

    ocorrencias = validar_sistemas_e_contas(linhas)

    assert any(o.codigo == "DRO001443" for o in ocorrencias)


def test_sistemas_e_contas_consistentes_nao_geram_ocorrencia() -> None:
    linhas = [
        _linha(
            2,
            contaBalAnaliticoDebito="123",
            nomeContaDebito="Conta A",
            contaCosifDebito="12345678",
        ),
        _linha(
            3,
            contaBalAnaliticoDebito="123",
            nomeContaDebito="Conta A",
            contaCosifDebito="12345678",
        ),
    ]

    ocorrencias = validar_sistemas_e_contas(linhas)

    assert ocorrencias == []


# ---------------------------------------------------------------------------
# Formato/dominio: BASE-*-FORM-001 (sistemas/contas, probabilidade,
# fonteRecuperacao)
# ---------------------------------------------------------------------------


def test_codigo_sistema_malformado_gera_uma_unica_ocorrencia_para_varias_linhas() -> (
    None
):
    linhas = [
        _linha(2, idEvento="EVT-1", codSistemaOrigem="SISTEMA_INVALIDO_123"),
        _linha(3, idEvento="EVT-2", codSistemaOrigem="SISTEMA_INVALIDO_123"),
        _linha(4, idEvento="EVT-3", codSistemaOrigem="SISTEMA_INVALIDO_123"),
    ]

    ocorrencias = validar_sistemas_e_contas(linhas)

    ocorrencias_formato = [
        o for o in ocorrencias if o.codigo == "BASE-SISTEMA-FORM-001"
    ]
    assert len(ocorrencias_formato) == 1
    assert ocorrencias_formato[0].linhas == (2, 3, 4)


def test_nomes_com_espacos_diferentes_nao_geram_conflito() -> None:
    linhas = [
        _linha(2, idEvento="EVT-1", codSistemaOrigem="SIS1", nomeSistema="Sistema de Risco"),
        _linha(3, idEvento="EVT-2", codSistemaOrigem="SIS1", nomeSistema="Sistema   de   Risco"),
    ]

    ocorrencias = validar_sistemas_e_contas(linhas)

    assert not any(o.codigo == "BASE-SIS-001" for o in ocorrencias)


def test_codigo_sistema_malformado_independe_do_nome_estar_presente() -> None:
    linhas = [
        _linha(
            2,
            idEvento="EVT-1",
            codSistemaOrigem="SISTEMA_INVALIDO_123",
            nomeSistema=None,
        )
    ]

    ocorrencias = validar_sistemas_e_contas(linhas)

    assert any(o.codigo == "BASE-SISTEMA-FORM-001" for o in ocorrencias)


def test_nome_sistema_com_espaco_nao_separavel_no_meio_gera_ocorrencia() -> None:
    linhas = [
        _linha(2, nomeSistema="Sistema de Risco"),
    ]

    ocorrencias = validar_sistemas_e_contas(linhas)

    assert any(o.codigo == "BASE-NOMESISTEMA-FORM-001" for o in ocorrencias)


def test_conta_bal_analitico_malformada_aponta_campo_de_origem() -> None:
    linhas = [
        _linha(2, idEvento="EVT-1", contaBalAnaliticoDebito="ABC123"),
        _linha(3, idEvento="EVT-2", contaBalAnaliticoCredito="XYZ789"),
    ]

    ocorrencias = validar_sistemas_e_contas(linhas)
    ocorrencias_formato = {
        o.campos: o for o in ocorrencias if o.codigo == "BASE-CONTABAL-FORM-001"
    }

    assert ("contaBalAnaliticoDebito",) in ocorrencias_formato
    assert ("contaBalAnaliticoCredito",) in ocorrencias_formato


def test_nome_conta_malformado_aponta_campo_de_origem() -> None:
    linhas = [
        _linha(2, idEvento="EVT-1", nomeContaDebito="Conta_com_erro"),
        _linha(3, idEvento="EVT-2", nomeContaCredito="Conta#Credito"),
    ]

    ocorrencias = validar_sistemas_e_contas(linhas)
    ocorrencias_formato = {
        o.campos: o for o in ocorrencias if o.codigo == "BASE-NOMECONTA-FORM-001"
    }

    assert ("nomeContaDebito",) in ocorrencias_formato
    assert ("nomeContaCredito",) in ocorrencias_formato


def test_probabilidade_fora_do_dominio_gera_ocorrencia_e_nao_entra_na_tupla() -> (
    None
):
    linhas = [_linha(2, probabilidadePerda="XX", valorRisco=100)]

    probabilidades, ocorrencias = extrair_probabilidades(linhas)

    assert probabilidades == ()
    assert len(ocorrencias) == 1
    assert ocorrencias[0].codigo == "BASE-PROBABILIDADE-FORM-001"


def test_probabilidade_fora_do_dominio_sem_valor_risco_nao_gera_base_prob_001() -> (
    None
):
    linhas = [_linha(2, probabilidadePerda="XX", valorRisco=None)]

    _, ocorrencias = extrair_probabilidades(linhas)

    assert len(ocorrencias) == 1
    assert ocorrencias[0].codigo == "BASE-PROBABILIDADE-FORM-001"


def test_fonte_recuperacao_fora_do_dominio_pode_sobrepor_dro001421() -> None:
    """Politica aceita e documentada: quando valorRecuperacao < 0, o
    dominio invalido de fonteRecuperacao tambem dispara DRO001421 (o
    proprio DRO001421 ja rejeita qualquer fonte fora de S/O) — sobreposicao
    menor, nao resolvida por engenharia extra."""
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=100,
            valorProvisao=0,
            valorRecuperacao=-50,
            fonteRecuperacao="XX",
        )
    ]

    _, ocorrencias = montar_evento("EVT-1", linhas)

    codigos = {o.codigo for o in ocorrencias}
    assert "BASE-FONTERECUPERACAO-FORM-001" in codigos
    assert "DRO001421" in codigos


def test_fonte_recuperacao_fora_do_dominio_com_data_ausente_gera_os_dois() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao=None,
            valorPerdaEfetiva=100,
            valorProvisao=0,
            valorRecuperacao=0,
            fonteRecuperacao="XX",
        )
    ]

    _, ocorrencias = montar_evento("EVT-1", linhas)

    codigos = {o.codigo for o in ocorrencias}
    assert "BASE-FONTERECUPERACAO-FORM-001" in codigos
    assert "BASE-CONT-OBR-001" in codigos


def test_builder_preserva_todas_as_linhas_normalizadas_do_evento() -> None:
    linhas = [
        _linha(2, probabilidadePerda="PR", valorRisco=100),
        _linha(3, probabilidadePerda="XX", valorRisco=200),
    ]

    evento = construir_evento("EVT-1", linhas)

    assert evento.linhas == tuple(linhas)
    assert len(evento.probabilidades) == 1
    assert evento.probabilidades[0].codigo == "PR"

def test_calcular_totais_nao_altera_o_evento_recebido() -> None:
    evento = construir_evento(
        "EVT-1",
        [
            _linha(
                2,
                dataContabilizacao="2025-06-15",
                valorPerdaEfetiva=100,
                valorProvisao=20,
                valorRecuperacao=-5,
            )
        ],
    )
    evento.total_perda_efetiva = Decimal("999.00")
    evento.total_provisao = Decimal("888.00")
    evento.total_recuperado = Decimal("777.00")
    estado_anterior = (
        evento.total_perda_efetiva,
        evento.total_provisao,
        evento.total_recuperado,
        evento.valor_total_risco,
    )

    resultado = calcular_totais(evento)

    assert resultado is not None
    assert resultado.perda_efetiva == Decimal("100.00")
    assert resultado.provisao == Decimal("20.00")
    assert resultado.recuperado == Decimal("-5.00")
    assert (
        evento.total_perda_efetiva,
        evento.total_provisao,
        evento.total_recuperado,
        evento.valor_total_risco,
    ) == estado_anterior
