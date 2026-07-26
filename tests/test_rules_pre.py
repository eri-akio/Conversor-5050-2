"""Testes da Fase 5: criticas locais de pre-processamento
(src/rules_pre.py)."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from src.calculations import (
    construir_mapa_contas,
    construir_mapa_sistemas,
    montar_evento,
    normalizar_linha_base,
)
from src.normalizers import (
    normalizar_cnpj,
    normalizar_data_base,
    normalizar_maiusculo,
    normalizar_texto,
)
from src.reader import BASE_COLUNAS
from src.rules_pre import (
    cabecalho_tem_data_base_valida,
    classificar_evento,
    validar_cabecalho,
    validar_campos_contabeis_quando_ha_movimento,
    validar_codigo_conglomerado_unicad,
    validar_composicao_risco_total,
    validar_conta_cosif_credito,
    validar_conta_cosif_debito,
    validar_contas_referenciadas,
    validar_cosif_obrigatorio,
    validar_descoberta_obrigatoria,
    validar_descricao_materialidade,
    validar_evento,
    validar_evento_apenas_risco,
    validar_natureza_contingencia_avaliacao,
    validar_natureza_para_risco,
    validar_ordem_datas,
    validar_probabilidade_obrigatoria_individual,
    validar_probabilidade_proibida_massificada,
    validar_provisao_avaliacao_im,
    validar_sistema_referenciado,
    validar_soma_risco_positiva,
    validar_unicidade_do_documento,
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


def _evento(id_evento: str, linhas: list) -> "EventoAgrupado":  # noqa: F821
    evento, _ = montar_evento(id_evento, linhas)
    return evento


def test_ordem_datas_invalida_gera_dro001201() -> None:
    evento = _evento(
        "EVT-1",
        [_linha(2, dataOcorrencia="2025-06-10", dataDescoberta="2025-06-01")],
    )

    assert validar_ordem_datas(evento) is not None
    assert validar_ordem_datas(evento).codigo == "DRO001201"


def test_ordem_datas_valida_nao_gera_ocorrencia() -> None:
    evento = _evento(
        "EVT-1",
        [_linha(2, dataOcorrencia="2025-05-01", dataDescoberta="2025-06-10")],
    )

    assert validar_ordem_datas(evento) is None


def test_descoberta_ausente_apos_2021_gera_dro001202() -> None:
    evento = _evento(
        "EVT-1", [_linha(2, dataOcorrencia="2025-06-10", dataDescoberta=None)]
    )

    assert validar_descoberta_obrigatoria(evento).codigo == "DRO001202"


def test_descoberta_ausente_antes_de_2021_nao_gera_ocorrencia() -> None:
    evento = _evento(
        "EVT-1", [_linha(2, dataOcorrencia="2020-06-10", dataDescoberta=None)]
    )

    assert validar_descoberta_obrigatoria(evento) is None


def test_natureza_na_com_avaliacao_diferente_de_na_gera_base_cont_001() -> None:
    evento = _evento(
        "EVT-1",
        [_linha(2, naturezaContingencia="NA", tipoAvaliacao="I")],
    )

    assert (
        validar_natureza_contingencia_avaliacao(evento).codigo
        == "BASE-CONT-001"
    )


def test_natureza_tri_com_avaliacao_na_gera_base_cont_001() -> None:
    evento = _evento(
        "EVT-1",
        [_linha(2, naturezaContingencia="TRI", tipoAvaliacao="NA")],
    )

    assert (
        validar_natureza_contingencia_avaliacao(evento).codigo
        == "BASE-CONT-001"
    )


def test_natureza_e_avaliacao_coerentes_nao_geram_ocorrencia() -> None:
    evento = _evento(
        "EVT-1",
        [_linha(2, naturezaContingencia="TRI", tipoAvaliacao="I")],
    )

    assert validar_natureza_contingencia_avaliacao(evento) is None


def test_natureza_para_risco_ausente_gera_dro001233() -> None:
    linhas = [
        _linha(
            2,
            tipoAvaliacao="I",
            naturezaContingencia="NA",
            probabilidadePerda="PR",
            # >= 10_000_000,00 (piso de emissao, P4) para que
            # valorTotalRisco seja de fato calculado.
            valorRisco=10_000_000,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=500,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert evento.valor_total_risco is not None
    assert validar_natureza_para_risco(evento).codigo == "DRO001233"


def test_descricao_obrigatoria_pela_materialidade_gera_dro001241() -> None:
    linhas = [
        _linha(
            2,
            descricaoEvento=None,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=Decimal("2000000.00"),
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_descricao_materialidade(evento).codigo == "DRO001241"


def test_descricao_presente_nao_gera_dro001241() -> None:
    linhas = [
        _linha(
            2,
            descricaoEvento="Perda relevante",
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=Decimal("2000000.00"),
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_descricao_materialidade(evento) is None


def test_provisao_ausente_em_avaliacao_i_gera_dro001302() -> None:
    evento = _evento("EVT-1", [_linha(2, tipoAvaliacao="I")])

    assert validar_provisao_avaliacao_im(evento).codigo == "DRO001302"


def test_provisao_informada_em_avaliacao_i_nao_gera_dro001302() -> None:
    linhas = [
        _linha(
            2,
            tipoAvaliacao="I",
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_provisao_avaliacao_im(evento) is None


def test_evento_exclusivamente_de_risco_nao_gera_dro001302() -> None:
    """P#4: DRO001452 exige que um evento exclusivamente de risco NAO
    tenha contabilizacoes -- DRO001302 nao pode reprovar exatamente esse
    caso exigido."""

    linhas = [
        _linha(
            2,
            tipoAvaliacao="I",
            probabilidadePerda="PR",
            valorRisco=15_000_000,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_provisao_avaliacao_im(evento) is None


def test_probabilidade_obrigatoria_individual_ausente_gera_dro001312() -> None:
    evento = _evento(
        "EVT-1", [_linha(2, tipoAvaliacao="I", dataOcorrencia="2025-06-10")]
    )

    assert (
        validar_probabilidade_obrigatoria_individual(evento).codigo
        == "DRO001312"
    )


def test_probabilidade_proibida_em_avaliacao_massificada_gera_dro001313() -> (
    None
):
    evento = _evento(
        "EVT-1",
        [
            _linha(
                2,
                tipoAvaliacao="M",
                probabilidadePerda="PR",
                valorRisco=100,
            )
        ],
    )

    assert (
        validar_probabilidade_proibida_massificada(evento).codigo
        == "DRO001313"
    )


def test_soma_risco_nao_positiva_gera_dro001314() -> None:
    evento = _evento(
        "EVT-1",
        [
            _linha(
                2,
                tipoAvaliacao="I",
                naturezaContingencia="TRI",
                probabilidadePerda="PR",
                valorRisco=0,
            )
        ],
    )

    assert validar_soma_risco_positiva(evento).codigo == "DRO001314"


def test_sistema_nunca_associado_a_nome_gera_dro001321() -> None:
    """DRO001321: codSistemaOrigem nao encontrado no bloco global de
    sistemas (Bloco 3) -- aqui o codigo "SIS-DESCONHECIDO" nunca aparece
    com um nome em nenhuma linha."""
    linha = _linha(2, codSistemaOrigem="SIS-DESCONHECIDO", nomeSistema=None)
    evento = _evento("EVT-1", [linha])
    sistemas_globais = construir_mapa_sistemas([linha])

    ocorrencia = validar_sistema_referenciado(evento, sistemas_globais)

    assert ocorrencia is not None
    assert ocorrencia.codigo == "DRO001321"


def test_sistema_estabelecido_em_outra_linha_nao_gera_dro001321() -> None:
    """P7-d: o sistema existe no bloco global (estabelecido em outro
    evento), mesmo sem nomeSistema preenchido na linha que o referencia
    de novo -- nao deve reprovar (falso positivo corrigido)."""
    linha_com_nome = _linha(
        2, idEvento="EVT-A", codSistemaOrigem="S1", nomeSistema="Sistema Um"
    )
    linha_sem_nome = _linha(
        3, idEvento="EVT-B", codSistemaOrigem="S1", nomeSistema=None
    )
    sistemas_globais = construir_mapa_sistemas([linha_com_nome, linha_sem_nome])
    evento_b = _evento("EVT-B", [linha_sem_nome])

    assert validar_sistema_referenciado(evento_b, sistemas_globais) is None


def test_conta_debito_nunca_associada_a_nome_gera_dro001401() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=0,
            valorRecuperacao=0,
            contaBalAnaliticoDebito="123",
            nomeContaDebito=None,
        )
    ]
    evento = _evento("EVT-1", linhas)
    contas_globais = construir_mapa_contas(linhas)

    ocorrencias = validar_contas_referenciadas(evento, contas_globais)

    assert any(o.codigo == "DRO001401" for o in ocorrencias)


def test_conta_debito_estabelecida_em_outra_linha_nao_gera_dro001401() -> (
    None
):
    """P7-b: a conta existe no bloco global (nome estabelecido em outra
    linha/evento), mesmo sem o nome repetido na linha que a referencia de
    novo -- nao deve reprovar (falso positivo corrigido)."""
    linha_com_nome = _linha(
        2,
        idEvento="EVT-A",
        dataContabilizacao="2025-06-15",
        valorPerdaEfetiva=0,
        valorProvisao=0,
        valorRecuperacao=0,
        contaBalAnaliticoDebito="123456",
        nomeContaDebito="Conta de perda",
    )
    linha_sem_nome = _linha(
        3,
        idEvento="EVT-B",
        dataContabilizacao="2025-06-16",
        valorPerdaEfetiva=0,
        valorProvisao=0,
        valorRecuperacao=0,
        contaBalAnaliticoDebito="123456",
        nomeContaDebito=None,
    )
    contas_globais = construir_mapa_contas([linha_com_nome, linha_sem_nome])
    evento_b = _evento("EVT-B", [linha_sem_nome])

    ocorrencias = validar_contas_referenciadas(evento_b, contas_globais)

    assert not any(o.codigo == "DRO001401" for o in ocorrencias)


def test_conta_debito_sem_cosif_gera_dro001441() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=0,
            valorRecuperacao=0,
            contaBalAnaliticoDebito="123",
            nomeContaDebito="Conta A",
            contaCosifDebito=None,
        )
    ]
    evento = _evento("EVT-1", linhas)

    ocorrencias = validar_cosif_obrigatorio(evento)

    assert any(o.codigo == "DRO001441" for o in ocorrencias)


def test_conta_cosif_debito_no_cadastro_nao_gera_ocorrencia() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=0,
            valorRecuperacao=0,
            contaBalAnaliticoDebito="123",
            nomeContaDebito="Conta A",
            contaCosifDebito="10000007",
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_conta_cosif_debito(evento) == []


def test_conta_cosif_debito_fora_do_cadastro_gera_dro001431() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=0,
            valorRecuperacao=0,
            contaBalAnaliticoDebito="123",
            nomeContaDebito="Conta A",
            contaCosifDebito="99999999",
        )
    ]
    evento = _evento("EVT-1", linhas)

    ocorrencias = validar_conta_cosif_debito(evento)

    assert any(o.codigo == "DRO001431" for o in ocorrencias)


def test_conta_cosif_debito_ausente_nao_gera_ocorrencia() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=0,
            valorRecuperacao=0,
            contaBalAnaliticoDebito=None,
            nomeContaDebito=None,
            contaCosifDebito=None,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_conta_cosif_debito(evento) == []


def test_conta_cosif_credito_no_cadastro_nao_gera_ocorrencia() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=0,
            valorRecuperacao=0,
            contaBalAnaliticoCredito="456",
            nomeContaCredito="Conta B",
            contaCosifCredito="20000006",
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_conta_cosif_credito(evento) == []


def test_conta_cosif_credito_fora_do_cadastro_gera_dro001432() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=0,
            valorRecuperacao=0,
            contaBalAnaliticoCredito="456",
            nomeContaCredito="Conta B",
            contaCosifCredito="99999998",
        )
    ]
    evento = _evento("EVT-1", linhas)

    ocorrencias = validar_conta_cosif_credito(evento)

    assert any(o.codigo == "DRO001432" for o in ocorrencias)


def test_evento_apenas_risco_com_contabilizacao_gera_dro001452() -> None:
    linhas = [
        _linha(
            2,
            tipoAvaliacao="I",
            naturezaContingencia="TRI",
            probabilidadePerda="PR",
            valorRisco=100,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_evento_apenas_risco(evento).codigo == "DRO001452"


def test_evento_apenas_risco_sem_contabilizacao_nao_gera_ocorrencia() -> None:
    linhas = [
        _linha(
            2,
            tipoAvaliacao="I",
            naturezaContingencia="TRI",
            probabilidadePerda="PR",
            valorRisco=100,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_evento_apenas_risco(evento) is None


def test_evento_com_risco_e_movimento_real_nao_gera_dro001452() -> None:
    """Um evento pode ter risco E movimento real ao mesmo tempo; isso nao e
    "exclusivamente" de risco, entao DRO001452 nao deve disparar."""

    linhas = [
        _linha(
            2,
            tipoAvaliacao="I",
            naturezaContingencia="TRI",
            probabilidadePerda="PR",
            valorRisco=100,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=50,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert validar_evento_apenas_risco(evento) is None


def test_composicao_risco_total_com_valor_divergente_gera_dro001311() -> None:
    linhas = [
        _linha(
            2,
            tipoAvaliacao="I",
            probabilidadePerda="PR",
            # >= 10_000_000,00 (piso de emissao, P4) para que
            # valorTotalRisco seja de fato calculado.
            valorRisco=10_000_000,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=0,
            valorProvisao=500,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)
    evento_divergente = replace(
        evento, valor_total_risco=evento.valor_total_risco + 1
    )

    ocorrencia = validar_composicao_risco_total(evento_divergente)

    assert ocorrencia is not None
    assert ocorrencia.codigo == "DRO001311"


def test_campos_contabeis_quando_ha_movimento_sem_contabilizacao_gera_dro001451() -> (
    None
):
    """Rede de seguranca de consistencia interna: totais forcados
    nao-zero sem nenhuma contabilizacao (matematicamente inatingivel a
    partir de uma planilha real, ja que calcular_totais so soma valores
    de contabilizacoes existentes)."""

    linhas = [_linha(2)]
    evento = _evento("EVT-1", linhas)
    evento_com_totais_forcados = replace(
        evento,
        total_perda_efetiva=Decimal("100.00"),
        total_provisao=Decimal("0.00"),
        total_recuperado=Decimal("0.00"),
    )

    ocorrencias = validar_campos_contabeis_quando_ha_movimento(
        evento_com_totais_forcados
    )

    assert any(o.codigo == "DRO001451" for o in ocorrencias)


def test_contabilizacao_com_movimento_e_so_par_debito_gera_dro001451() -> (
    None
):
    """P#3: ter só um dos dois pares completos não é suficiente -- a
    critica oficial exige informacoes relativas as contas
    correspondentes, e o XML de exemplo oficial sempre preenche os dois
    lados juntos (partida dobrada)."""

    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=2500,
            valorProvisao=0,
            valorRecuperacao=0,
            contaBalAnaliticoDebito="123456",
            nomeContaDebito="Conta de perda",
            contaCosifDebito="12345678",
        )
    ]
    evento = _evento("EVT-1", linhas)

    ocorrencias = validar_campos_contabeis_quando_ha_movimento(evento)

    assert any(o.codigo == "DRO001451" for o in ocorrencias)


def test_contabilizacao_com_movimento_e_sem_nenhuma_conta_gera_dro001451() -> (
    None
):
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=2500,
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    ocorrencias = validar_campos_contabeis_quando_ha_movimento(evento)

    assert any(o.codigo == "DRO001451" for o in ocorrencias)


def test_contabilizacao_com_movimento_e_os_dois_pares_completos_nao_gera_dro001451() -> (
    None
):
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=2500,
            valorProvisao=0,
            valorRecuperacao=0,
            contaBalAnaliticoDebito="123456",
            nomeContaDebito="Conta de perda",
            contaCosifDebito="12345678",
            contaBalAnaliticoCredito="654321",
            nomeContaCredito="Conta de contrapartida",
            contaCosifCredito="87654321",
        )
    ]
    evento = _evento("EVT-1", linhas)

    ocorrencias = validar_campos_contabeis_quando_ha_movimento(evento)

    assert not any(o.codigo == "DRO001451" for o in ocorrencias)


def test_classificar_evento_individualiza_pelo_limiar_monetario() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=Decimal("1000.00"),
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert classificar_evento(evento) is True


def test_classificar_evento_individualiza_pelo_risco_nao_coberto() -> None:
    linhas = [
        _linha(
            2,
            tipoAvaliacao="I",
            probabilidadePerda="PR",
            valorRisco=Decimal("10000000.00"),
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert classificar_evento(evento) is True


def test_classificar_evento_consolida_abaixo_dos_dois_limiares() -> None:
    linhas = [
        _linha(
            2,
            dataContabilizacao="2025-06-15",
            valorPerdaEfetiva=Decimal("10.00"),
            valorProvisao=0,
            valorRecuperacao=0,
        )
    ]
    evento = _evento("EVT-1", linhas)

    assert classificar_evento(evento) is False


def test_classificar_evento_inconsistente_nunca_individualiza() -> None:
    linhas = [
        _linha(2, categoriaNivel1="1"),
        _linha(3, categoriaNivel1="2"),
    ]
    evento = _evento("EVT-1", linhas)

    assert classificar_evento(evento) is False


def test_validar_evento_evento_limpo_nao_gera_ocorrencias() -> None:
    linhas = [_linha(2)]
    evento = _evento("EVT-1", linhas)

    assert validar_evento(evento) == []


def test_validar_unicidade_do_documento_sem_problemas() -> None:
    evento = _evento("EVT-1", [_linha(2)])

    assert validar_unicidade_do_documento({"EVT-1": evento}) == []


CABECALHO_VALORES_PADRAO = {
    "codigoDocumento": "5050",
    "dataBase": "2026-06",
    "codigoConglomerado": "C0099999",
    "cnpj": "46169337",
    "tipoRemessa": "I",
    "opcaoPorProvisaoAcumulada": "N",
}


def _cabecalho(**sobrescritas: object) -> dict:
    valores = dict(CABECALHO_VALORES_PADRAO)
    valores.update(sobrescritas)
    return {
        "codigoDocumento": normalizar_texto(
            "codigoDocumento", valores["codigoDocumento"]
        ),
        "dataBase": normalizar_data_base("dataBase", valores["dataBase"]),
        "codigoConglomerado": normalizar_maiusculo(
            "codigoConglomerado", valores["codigoConglomerado"]
        ),
        "cnpj": normalizar_cnpj("cnpj", valores["cnpj"]),
        "tipoRemessa": normalizar_maiusculo(
            "tipoRemessa", valores["tipoRemessa"]
        ),
        "opcaoPorProvisaoAcumulada": normalizar_maiusculo(
            "opcaoPorProvisaoAcumulada", valores["opcaoPorProvisaoAcumulada"]
        ),
    }


def test_validar_cabecalho_valido_nao_gera_ocorrencias() -> None:
    assert validar_cabecalho(_cabecalho()) == []


def test_validar_cabecalho_codigo_documento_diferente_de_5050() -> None:
    ocorrencias = validar_cabecalho(_cabecalho(codigoDocumento="5051"))
    assert len(ocorrencias) == 1
    assert ocorrencias[0].codigo == "BASE-CAB-CODDOC-001"


def test_validar_cabecalho_codigo_documento_ausente() -> None:
    ocorrencias = validar_cabecalho(_cabecalho(codigoDocumento=None))
    assert len(ocorrencias) == 1
    assert ocorrencias[0].codigo == "BASE-CAB-CODDOC-001"


def test_validar_cabecalho_data_base_invalida_gera_uma_unica_ocorrencia() -> (
    None
):
    """Estado (ausente/invalido) e checado antes do dominio: so 1
    ocorrencia por campo, nunca 2-3 para o mesmo problema."""
    ocorrencias = validar_cabecalho(_cabecalho(dataBase="2026-07"))
    assert len(ocorrencias) == 1
    assert ocorrencias[0].codigo == "BASE-CAB-DATABASE-001"


def test_validar_cabecalho_data_base_ausente() -> None:
    ocorrencias = validar_cabecalho(_cabecalho(dataBase=None))
    assert len(ocorrencias) == 1
    assert ocorrencias[0].codigo == "BASE-CAB-DATABASE-001"


def test_validar_cabecalho_conglomerado_fora_do_padrao() -> None:
    ocorrencias = validar_cabecalho(_cabecalho(codigoConglomerado="X0099999"))
    assert len(ocorrencias) == 1
    assert ocorrencias[0].codigo == "BASE-CAB-CONGLOMERADO-001"


def test_validar_codigo_conglomerado_unicad_presente_no_cadastro() -> None:
    assert validar_codigo_conglomerado_unicad(_cabecalho()) is None


def test_validar_codigo_conglomerado_unicad_ausente_do_cadastro() -> None:
    ocorrencia = validar_codigo_conglomerado_unicad(
        _cabecalho(codigoConglomerado="C0000001")
    )
    assert ocorrencia is not None
    assert ocorrencia.codigo == "DRO001001"


def test_validar_codigo_conglomerado_unicad_nao_duplica_erro_de_formato() -> (
    None
):
    """Quando o formato ja esta invalido, BASE-CAB-CONGLOMERADO-001 ja cobre
    o problema; DRO001001 nao deve gerar uma segunda ocorrencia."""
    ocorrencia = validar_codigo_conglomerado_unicad(
        _cabecalho(codigoConglomerado="X0099999")
    )
    assert ocorrencia is None


def test_validar_codigo_conglomerado_unicad_campo_ausente() -> None:
    ocorrencia = validar_codigo_conglomerado_unicad(
        _cabecalho(codigoConglomerado=None)
    )
    assert ocorrencia is None


def test_validar_cabecalho_cnpj_invalido() -> None:
    ocorrencias = validar_cabecalho(_cabecalho(cnpj="123"))
    assert len(ocorrencias) == 1
    assert ocorrencias[0].codigo == "BASE-CAB-CNPJ-001"


def test_validar_cabecalho_tipo_remessa_fora_do_dominio() -> None:
    ocorrencias = validar_cabecalho(_cabecalho(tipoRemessa="X"))
    assert len(ocorrencias) == 1
    assert ocorrencias[0].codigo == "BASE-CAB-REMESSA-001"


def test_validar_cabecalho_opcao_provisao_acumulada_fora_do_dominio() -> None:
    ocorrencias = validar_cabecalho(
        _cabecalho(opcaoPorProvisaoAcumulada="X")
    )
    assert len(ocorrencias) == 1
    assert ocorrencias[0].codigo == "BASE-CAB-PROVACUM-001"


def test_cabecalho_tem_data_base_valida() -> None:
    assert cabecalho_tem_data_base_valida(_cabecalho()) is True
    assert (
        cabecalho_tem_data_base_valida(_cabecalho(dataBase="2026-07"))
        is False
    )
    assert (
        cabecalho_tem_data_base_valida(_cabecalho(dataBase=None)) is False
    )
