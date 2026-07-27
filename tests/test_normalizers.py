"""Testes da Fase 3: normalizacao de celulas (src/normalizers.py)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from src.models import CampoNormalizado, StatusCampo
from src.normalizers import (
    _decimal_fora_da_faixa,
    detectar_ausencia_e_invalidez,
    maiusculizar_campo,
    normalizar_cnpj,
    normalizar_codigo_rotulado,
    normalizar_data,
    normalizar_data_base,
    normalizar_decimal,
    normalizar_maiusculo,
    normalizar_removendo_caracteres,
    normalizar_texto,
)


@pytest.mark.parametrize("valor", [None, "", "   "])
def test_normalizar_texto_ausente(valor: object) -> None:
    campo = normalizar_texto("descricaoEvento", valor)
    assert campo.status is StatusCampo.AUSENTE
    assert campo.valor is None


@pytest.mark.parametrize("valor", ["N/A", "NULL", "-", "*", " NULL "])
def test_normalizar_texto_marcador_invalido(valor: object) -> None:
    campo = normalizar_texto("descricaoEvento", valor)
    assert campo.status is StatusCampo.INVALIDO


def test_normalizar_texto_na_e_aceito_como_valor_normal() -> None:
    # "NA" (sem barra) e um codigo de dominio valido em varios campos; a
    # decisao sobre onde e aceito e do dominio (Fase 4/5), nao daqui.
    campo = normalizar_texto("tipoAvaliacao", "NA")
    assert campo.status is StatusCampo.VALIDO
    assert campo.valor == "NA"


def test_normalizar_texto_preserva_valor_sem_correcao() -> None:
    campo = normalizar_texto("descricaoEvento", "  Perda operacional  ")
    assert campo.valor == "Perda operacional"


def test_normalizar_data_valida_a_partir_de_datetime() -> None:
    campo = normalizar_data("dataOcorrencia", datetime(2025, 6, 15))
    assert campo.status is StatusCampo.VALIDO
    assert campo.valor == date(2025, 6, 15)


def test_normalizar_data_valida_a_partir_de_texto_iso() -> None:
    campo = normalizar_data("dataOcorrencia", "2025-06-15")
    assert campo.valor == date(2025, 6, 15)


def test_normalizar_data_formato_nao_reconhecido_e_invalido() -> None:
    campo = normalizar_data("dataOcorrencia", "2025/06/15")
    assert campo.status is StatusCampo.INVALIDO


def test_normalizar_data_ausente() -> None:
    campo = normalizar_data("dataOcorrencia", None)
    assert campo.status is StatusCampo.AUSENTE


def test_normalizar_data_a_partir_de_texto_formato_brasileiro() -> None:
    campo = normalizar_data("dataOcorrencia", "05/12/2025")
    assert campo.status is StatusCampo.VALIDO
    assert campo.valor == date(2025, 12, 5)


def test_normalizar_data_formato_brasileiro_sem_zero_a_esquerda() -> None:
    campo = normalizar_data("dataOcorrencia", "5/1/2025")
    assert campo.valor == date(2025, 1, 5)


def test_normalizar_data_formato_brasileiro_dia_invalido() -> None:
    campo = normalizar_data("dataOcorrencia", "31/02/2025")
    assert campo.status is StatusCampo.INVALIDO


def test_normalizar_data_formato_brasileiro_mes_invalido() -> None:
    campo = normalizar_data("dataOcorrencia", "13/13/2025")
    assert campo.status is StatusCampo.INVALIDO


def test_normalizar_data_base_a_partir_de_datetime() -> None:
    campo = normalizar_data_base("dataBase", datetime(2026, 6, 1))
    assert campo.valor == "2026-06"


def test_normalizar_data_base_a_partir_de_texto() -> None:
    campo = normalizar_data_base("dataBase", "2026-06")
    assert campo.valor == "2026-06"


def test_normalizar_data_base_formato_invalido() -> None:
    campo = normalizar_data_base("dataBase", "06/2026")
    assert campo.status is StatusCampo.INVALIDO


@pytest.mark.parametrize("valor", ["2026-01", "2026-07", "2026-13", "2020-11"])
def test_normalizar_data_base_mes_invalido(valor: str) -> None:
    """P2: Documento 5050 e semestral, so mes 06 ou 12."""
    campo = normalizar_data_base("dataBase", valor)
    assert campo.status is StatusCampo.INVALIDO


@pytest.mark.parametrize("valor", ["2026-06", "2026-12", "2020-12"])
def test_normalizar_data_base_mes_valido(valor: str) -> None:
    campo = normalizar_data_base("dataBase", valor)
    assert campo.status is StatusCampo.VALIDO
    assert campo.valor == valor


def test_normalizar_data_base_datetime_com_mes_invalido() -> None:
    """A mesma regra de mes vale para celulas de data nativas do Excel,
    nao so para texto."""
    campo = normalizar_data_base("dataBase", datetime(2026, 7, 1))
    assert campo.status is StatusCampo.INVALIDO


def test_normalizar_data_base_anterior_ao_piso_do_xsd_e_invalido() -> None:
    """XSD tipoDataMesAno: minInclusive 2020-12."""
    campo = normalizar_data_base("dataBase", "2020-06")
    assert campo.status is StatusCampo.INVALIDO


def test_normalizar_data_base_com_digitos_unicode_fullwidth_e_invalido() -> (
    None
):
    campo = normalizar_data_base("dataBase", "２０２６-０６")
    assert campo.status is StatusCampo.INVALIDO


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (2300, Decimal("2300")),
        (2300.5, Decimal("2300.5")),
        ("2300", Decimal("2300")),
        ("2300.00", Decimal("2300.00")),
        ("2300,00", Decimal("2300.00")),
        ("-150,25", Decimal("-150.25")),
        ("1427,98", Decimal("1427.98")),
        ("1427.98", Decimal("1427.98")),
        ("1.427,98", Decimal("1427.98")),
        ("1.552.165,46", Decimal("1552165.46")),
        ("-1.427,98", Decimal("-1427.98")),
    ],
)
def test_normalizar_decimal_formatos_aceitos(
    valor: object, esperado: Decimal
) -> None:
    campo = normalizar_decimal("valorPerdaEfetiva", valor)
    assert campo.status is StatusCampo.VALIDO
    assert campo.valor == esperado
    assert isinstance(campo.valor, Decimal)


def test_normalizar_decimal_nunca_usa_float_no_resultado() -> None:
    campo = normalizar_decimal("valorPerdaEfetiva", 1999.99)
    assert isinstance(campo.valor, Decimal)
    assert not isinstance(campo.valor, float)


@pytest.mark.parametrize("valor", ["R$ 2.300,00", "abc", True])
def test_normalizar_decimal_formato_nao_suportado_e_invalido(
    valor: object,
) -> None:
    campo = normalizar_decimal("valorPerdaEfetiva", valor)
    assert campo.status is StatusCampo.INVALIDO


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("1.427", Decimal("1427")),
        ("1,427", Decimal("1427")),
        ("-1.427", Decimal("-1427")),
    ],
)
def test_normalizar_decimal_separador_unico_com_tres_digitos_e_milhar(
    valor: str, esperado: Decimal
) -> None:
    """Decisão registrada: um separador único seguido de exatamente 3
    dígitos é resolvido como separador de milhar (não como decimal) —
    a leitura decimal teria 3 casas, que nenhum valor monetário deste
    sistema aceita (máximo 2), então milhar é a única leitura possível,
    não uma adivinhação entre duas igualmente válidas."""

    campo = normalizar_decimal("valorPerdaEfetiva", valor)
    assert campo.status is StatusCampo.VALIDO
    assert campo.valor == esperado


def test_normalizar_decimal_ausente() -> None:
    campo = normalizar_decimal("valorPerdaEfetiva", None)
    assert campo.status is StatusCampo.AUSENTE


@pytest.mark.parametrize("valor", [1200.005, 300.005, 0.005])
def test_normalizar_decimal_float_com_precisao_excedente_e_invalido(
    valor: float,
) -> None:
    # Caso relatado: celula numerica do Excel (nao texto) com mais de duas
    # casas decimais nao pode passar sem arredondamento silencioso.
    campo = normalizar_decimal("valorPerdaEfetiva", valor)
    assert campo.status is StatusCampo.INVALIDO
    assert "casas decimais" in campo.motivo.lower()


def test_normalizar_decimal_texto_com_quatro_casas_e_invalido() -> None:
    campo = normalizar_decimal("valorPerdaEfetiva", "1427.9876")
    assert campo.status is StatusCampo.INVALIDO
    assert "casas decimais" in campo.motivo.lower()


@pytest.mark.parametrize(
    ("valor", "esperado"), [(2300.5, Decimal("2300.5")), (1427.9, Decimal("1427.9"))]
)
def test_normalizar_decimal_float_com_uma_casa_continua_valido(
    valor: float, esperado: Decimal
) -> None:
    # Uma casa decimal e exata em duas casas (1427.9 == 1427.90) -- nao e
    # precisao excedente, so falta o zero a direita.
    campo = normalizar_decimal("valorPerdaEfetiva", valor)
    assert campo.status is StatusCampo.VALIDO
    assert campo.valor == esperado


def test_precisao_excedente_pega_o_cenario_exato_do_relatorio() -> None:
    """Reproduz o bug relatado: 3 lancamentos com 3 casas decimais cada,
    cuja soma bruta e 1500.015 (arredonda para 1500.02) mas a soma dos
    valores ja arredondados individualmente e 1500.00. Com a correcao,
    nenhum dos 3 valores passa da normalizacao."""

    for valor in (1200.005, 300.005, 0.005):
        campo = normalizar_decimal("valorPerdaEfetiva", valor)
        assert campo.status is StatusCampo.INVALIDO


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (Decimal("0.01"), False),
        (Decimal("1427.900"), False),  # zeros a direita, sem perda real
        (Decimal("1200.005"), True),  # 3 casas reais
        (Decimal("2300.50"), False),
        (Decimal("9999999999999999.99"), False),  # 16 digitos inteiros
        (Decimal("10000000000000000.00"), True),  # 17 digitos inteiros
        (Decimal("1E+20"), True),  # 21 digitos inteiros
        (Decimal("nan"), True),
        (Decimal("inf"), True),
        (Decimal("-inf"), True),
        (Decimal("-1234.56"), False),
        (Decimal("1" * 50 + ".00"), True),  # 50 digitos inteiros
        (Decimal("0.0"), False),
        (Decimal("0"), False),
        (Decimal("100"), False),
        (Decimal("1000000000000000.00"), False),  # exatos 16 digitos
        (Decimal("10000000000000.001"), True),  # 3 casas reais
    ],
)
def test_decimal_fora_da_faixa(valor: Decimal, esperado: bool) -> None:
    """P9: algoritmo baseado em as_tuple(), sem normalize()/quantize() —
    nao depende do contexto decimal ativo e nao levanta excecao para
    valores muito grandes."""
    assert _decimal_fora_da_faixa(valor) is esperado


def test_normalizar_decimal_float_extremamente_grande_e_invalido_sem_crash() -> (
    None
):
    """P9: regressao da correcao anterior de arredondamento silencioso —
    normalizar_decimal(nome, 1e40) nao pode levantar
    decimal.InvalidOperation, so retornar INVALIDO."""

    campo = normalizar_decimal("valorPerdaEfetiva", float("1" * 40))
    assert campo.status is StatusCampo.INVALIDO


def test_normalizar_decimal_texto_extremamente_grande_e_invalido_sem_crash() -> (
    None
):
    campo = normalizar_decimal("valorPerdaEfetiva", "1" * 40 + ".00")
    assert campo.status is StatusCampo.INVALIDO


def test_normalizar_decimal_com_dezesseis_digitos_inteiros_e_valido() -> None:
    campo = normalizar_decimal("valorPerdaEfetiva", "9999999999999999.99")
    assert campo.status is StatusCampo.VALIDO


def test_normalizar_decimal_texto_com_1427_900_e_milhar_nao_decimal() -> (
    None
):
    """Distinção importante: '1427.900' como TEXTO (separador único + 3
    dígitos depois) passa pela regra de resolução de milhar em
    _interpretar_valor_monetario ANTES de qualquer análise de casas
    decimais — vira 1427900 (um milhão e tanto), não 1427.90. Isso é
    diferente de testar _decimal_fora_da_faixa isoladamente com um
    Decimal já construído como 1427.900 (que ali equivale a 1427.90,
    zeros à direita não contam) — o teste acima cobre esse outro caminho.
    Os dois caminhos calculam coisas diferentes por design: um interpreta
    texto de planilha (onde "1427.900" é claramente milhar, não decimal
    com 3 casas — este sistema nunca aceita mais de 2), o outro só
    verifica a faixa de um valor já numérico."""

    campo = normalizar_decimal("valorPerdaEfetiva", "1427.900")
    assert campo.status is StatusCampo.VALIDO
    assert campo.valor == Decimal("1427900")


def test_detectar_ausencia_gera_base_obr_001() -> None:
    campos = {
        "idEvento": normalizar_texto("idEvento", None),
        "categoriaNivel1": normalizar_texto("categoriaNivel1", "1"),
    }

    ocorrencias = detectar_ausencia_e_invalidez(
        campos,
        numero_linha=2,
        id_evento=None,
        sempre_obrigatorios=("idEvento", "categoriaNivel1"),
    )

    assert len(ocorrencias) == 1
    assert ocorrencias[0].codigo == "BASE-OBR-001"
    assert ocorrencias[0].campos == ("idEvento",)
    assert ocorrencias[0].linhas == (2,)


def test_detectar_invalidez_gera_base_nulo_001_mesmo_em_campo_opcional() -> None:
    campos = {
        "idEvento": normalizar_texto("idEvento", "EVT-1"),
        "descricaoEvento": normalizar_texto("descricaoEvento", "NULL"),
    }

    ocorrencias = detectar_ausencia_e_invalidez(
        campos,
        numero_linha=3,
        id_evento="EVT-1",
        sempre_obrigatorios=("idEvento",),
    )

    assert len(ocorrencias) == 1
    assert ocorrencias[0].codigo == "BASE-NULO-001"
    assert ocorrencias[0].campos == ("descricaoEvento",)


def test_detectar_ausencia_e_invalidez_sem_problemas() -> None:
    campos = {
        "idEvento": normalizar_texto("idEvento", "EVT-1"),
    }

    ocorrencias = detectar_ausencia_e_invalidez(
        campos,
        numero_linha=2,
        id_evento="EVT-1",
        sempre_obrigatorios=("idEvento",),
    )

    assert ocorrencias == []


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("1 - Fraudes internas", "1"),
        ("I - Individual", "I"),
        ("TRA - Trabalhista", "TRA"),
        ("41 - Adequacao de produto a cliente", "41"),
    ],
)
def test_normalizar_codigo_rotulado_extrai_codigo(
    valor: str, esperado: str
) -> None:
    campo = normalizar_codigo_rotulado("categoriaNivel1", valor)
    assert campo.status is StatusCampo.VALIDO
    assert campo.valor == esperado
    assert campo.valor_original == valor


def test_normalizar_codigo_rotulado_aceita_codigo_puro() -> None:
    campo = normalizar_codigo_rotulado("tipoAvaliacao", "I")
    assert campo.valor == "I"


def test_normalizar_codigo_rotulado_ausente() -> None:
    campo = normalizar_codigo_rotulado("categoriaNivel1", None)
    assert campo.status is StatusCampo.AUSENTE


def test_normalizar_codigo_rotulado_marcador_invalido() -> None:
    campo = normalizar_codigo_rotulado("tipoAvaliacao", "NULL")
    assert campo.status is StatusCampo.INVALIDO


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [("c0099999", "C0099999"), ("i", "I"), ("n", "N"), ("S", "S")],
)
def test_normalizar_maiusculo_converte_para_maiusculo(
    valor: str, esperado: str
) -> None:
    campo = normalizar_maiusculo("tipoRemessa", valor)
    assert campo.status is StatusCampo.VALIDO
    assert campo.valor == esperado


def test_normalizar_maiusculo_ausente() -> None:
    campo = normalizar_maiusculo("codigoConglomerado", None)
    assert campo.status is StatusCampo.AUSENTE


def test_normalizar_maiusculo_marcador_invalido() -> None:
    campo = normalizar_maiusculo("codigoConglomerado", "NULL")
    assert campo.status is StatusCampo.INVALIDO


def test_maiusculizar_campo_converte_valor_valido() -> None:
    campo = CampoNormalizado("tipoAvaliacao", "i", "i", StatusCampo.VALIDO)
    resultado = maiusculizar_campo(campo)
    assert resultado.valor == "I"
    assert resultado.status is StatusCampo.VALIDO


def test_maiusculizar_campo_preserva_ausente() -> None:
    campo = CampoNormalizado("tipoAvaliacao", None, None, StatusCampo.AUSENTE)
    resultado = maiusculizar_campo(campo)
    assert resultado is campo


def test_maiusculizar_campo_preserva_invalido() -> None:
    campo = CampoNormalizado(
        "tipoAvaliacao", "NULL", None, StatusCampo.INVALIDO, motivo="x"
    )
    resultado = maiusculizar_campo(campo)
    assert resultado is campo


def test_maiusculizar_campo_rejeita_valor_nao_textual() -> None:
    campo = CampoNormalizado("valorRisco", 100, Decimal("100"), StatusCampo.VALIDO)
    with pytest.raises(TypeError):
        maiusculizar_campo(campo)


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("46.169.337/0001-28", "46169337"),
        ("46169337000128", "46169337"),
        ("46169337", "46169337"),
    ],
)
def test_normalizar_cnpj_extrai_raiz(valor: str, esperado: str) -> None:
    campo = normalizar_cnpj("cnpj", valor)
    assert campo.status is StatusCampo.VALIDO
    assert campo.valor == esperado


def test_normalizar_cnpj_com_menos_de_oito_digitos_e_invalido() -> None:
    campo = normalizar_cnpj("cnpj", "123.456")
    assert campo.status is StatusCampo.INVALIDO


@pytest.mark.parametrize(
    "valor",
    [
        "391516589",  # 9 digitos: nem raiz (8) nem completo (14)
        "39151658ABC",  # letras misturadas
        "39151658000100123",  # 17 digitos
        "39151658ＡＢＣ",  # letras fullwidth apos a raiz
    ],
)
def test_normalizar_cnpj_malformado_e_invalido(valor: str) -> None:
    """P7: nao trunca nem aceita silenciosamente entrada malformada."""
    campo = normalizar_cnpj("cnpj", valor)
    assert campo.status is StatusCampo.INVALIDO


def test_normalizar_cnpj_com_digitos_unicode_fullwidth_e_invalido() -> None:
    campo = normalizar_cnpj("cnpj", "４６１６９３３７")
    assert campo.status is StatusCampo.INVALIDO


def test_normalizar_cnpj_ausente() -> None:
    campo = normalizar_cnpj("cnpj", None)
    assert campo.status is StatusCampo.AUSENTE


def test_normalizar_codigo_rotulado_ignora_texto_da_descricao() -> None:
    # A mesma decisao (NA) deve ser extraida independente da redacao ou
    # acentuacao da descricao apos o separador.
    campo_1 = normalizar_codigo_rotulado(
        "naturezaContingencia", "NA - Nao se aplica"
    )
    campo_2 = normalizar_codigo_rotulado(
        "naturezaContingencia", "NA - Não Aplicável"
    )
    assert campo_1.valor == "NA"
    assert campo_2.valor == "NA"


def test_normalizar_codigo_rotulado_extrai_id_bacen() -> None:
    campo = normalizar_codigo_rotulado("idBacen", "Z1234567 - Banco Alfa")
    assert campo.status is StatusCampo.VALIDO
    assert campo.valor == "Z1234567"


def test_normalizar_removendo_caracteres_remove_hifen_do_id_evento() -> None:
    campo = normalizar_removendo_caracteres("idEvento", "IND-0001", "-")
    assert campo.status is StatusCampo.VALIDO
    assert campo.valor == "IND0001"


def test_normalizar_removendo_caracteres_remove_pontos_da_conta() -> None:
    campo = normalizar_removendo_caracteres(
        "contaBalAnaliticoDebito",
        "819.951.010.400.000.000.000.003",
        ".",
    )
    assert campo.valor == "819951010400000000000003"


def test_normalizar_removendo_caracteres_aceita_valor_sem_o_caractere() -> (
    None
):
    campo = normalizar_removendo_caracteres("idEvento", "IND0001", "-")
    assert campo.valor == "IND0001"


def test_normalizar_removendo_caracteres_ausente() -> None:
    campo = normalizar_removendo_caracteres("idEvento", None, "-")
    assert campo.status is StatusCampo.AUSENTE


def test_normalizar_removendo_caracteres_marcador_invalido() -> None:
    campo = normalizar_removendo_caracteres("idEvento", "NULL", "-")
    assert campo.status is StatusCampo.INVALIDO
