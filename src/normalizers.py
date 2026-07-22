"""Normalizacao de celulas (Fase 3).

Ver docs/plano_conversor_dro_5050_simples.md secao 8 (ausencia e
normalizacao) e secao 19 (BASE-OBR-001, BASE-NULO-001).

Nao ha correcao ortografica, remocao silenciosa de acentos, truncamento ou
substituicao automatica de valores invalidos: um marcador invalido sempre
vira INVALIDO, nunca e reinterpretado.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from src.models import (
    CampoNormalizado,
    ETAPA_NORMALIZACAO,
    Ocorrencia,
    StatusCampo,
    TIPO_ERRO_IMPEDITIVO,
)

# Ausencia e invalidez (secao 8):
#   ""  (celula vazia ou so espacos) -> AUSENTE (ver _texto_bruto, nao
#        entra nesta lista: e um estado diferente de "invalido").
#   "NULL", "N/A", "-", "*"          -> INVALIDO.
#
# "NA" (sem barra) NAO entra aqui de proposito: e um codigo de dominio
# valido em varios campos do Documento 5050 (tipoAvaliacao,
# naturezaContingencia, riscoAssociado etc.) — tratá-lo como nulo
# reprovaria silenciosamente celulas corretas. A obrigatoriedade de "NA"
# em cada campo e decidida pelo dominio (Fase 4/5), nao aqui.
MARCADORES_INVALIDOS = frozenset({"NULL", "N/A", "-", "*"})

# Digitos ASCII explicitos ([0-9]), nao \d: \d tambem casa digitos Unicode
# fora do intervalo ASCII (ex.: fullwidth), que o XSD (baseado em [0-9])
# nao aceita.
_PADRAO_DATA_ISO = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_PADRAO_DATA_BR = re.compile(r"^([0-9]{1,2})/([0-9]{1,2})/([0-9]{4})$")
_PADRAO_DATA_BASE_ISO = re.compile(r"^[0-9]{4}-[0-9]{2}$")

# secao 8: formatos monetarios aceitos.
_PADRAO_DECIMAL_INTEIRO = re.compile(r"^[0-9]+$")
_PADRAO_DECIMAL_UM_SEPARADOR = re.compile(r"^([0-9]+)([.,])([0-9]+)$")
_PADRAO_DECIMAL_AGRUPADO = re.compile(r"^[0-9]{1,3}(?:\.[0-9]{3})+,[0-9]{2}$")


def _interpretar_valor_monetario(corpo: str) -> str | None:
    """Interpreta o texto de um valor monetario (sem o sinal `-`).

    Devolve o texto decimal equivalente quando reconhecido, ou None
    quando o formato nao e reconhecido.

    Decisao registrada: um separador unico seguido de exatamente 3 digitos
    (ex.: "1.500", "1,500") e resolvido como separador de milhar, nunca
    como decimal — nao e uma adivinhacao entre duas leituras igualmente
    validas, porque a leitura decimal teria 3 casas decimais, e nenhum
    valor monetario deste sistema aceita mais de 2 (LIMITE_CASAS_DECIMAIS,
    ver _decimal_fora_da_faixa); a leitura de milhar e a unica que pode
    resultar num valor valido."""

    if _PADRAO_DECIMAL_INTEIRO.match(corpo):
        return corpo

    if _PADRAO_DECIMAL_AGRUPADO.match(corpo):
        parte_inteira, parte_decimal = corpo.rsplit(",", 1)
        return parte_inteira.replace(".", "") + "." + parte_decimal

    um_separador = _PADRAO_DECIMAL_UM_SEPARADOR.match(corpo)
    if um_separador:
        inteiro, _separador, decimais = um_separador.groups()
        if len(decimais) == 3:
            return f"{inteiro}{decimais}"
        return f"{inteiro}.{decimais}"

    return None


# Campos cuja celula e sempre obrigatoria na Base, independente de condicoes
# (secao 9). Demais campos podem ser condicionalmente obrigatorios; essa
# obrigatoriedade condicional e avaliada nas Fases 4/5, nao aqui.
CAMPOS_SEMPRE_OBRIGATORIOS: tuple[str, ...] = (
    "idEvento",
    "categoriaNivel1",
    "tipoAvaliacao",
    "unidadeNegocio",
    "dataOcorrencia",
    "naturezaContingencia",
    "codSistemaOrigem",
    "nomeSistema",
    "codigoEventoOrigem",
    "idBacen",
)


def _texto_bruto(valor: object) -> str | None:
    """Texto sem espacos externos, ou None quando a celula esta ausente."""
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto if texto else None


def normalizar_texto(nome: str, valor: object) -> CampoNormalizado:
    texto = _texto_bruto(valor)
    if texto is None:
        return CampoNormalizado(nome, valor, None, StatusCampo.AUSENTE)
    if texto in MARCADORES_INVALIDOS:
        return CampoNormalizado(
            nome,
            valor,
            None,
            StatusCampo.INVALIDO,
            motivo=f"Marcador invalido: {texto}",
        )
    return CampoNormalizado(nome, valor, texto, StatusCampo.VALIDO)


SEPARADOR_CODIGO_DESCRICAO = " - "


def normalizar_codigo_rotulado(nome: str, valor: object) -> CampoNormalizado:
    """Igual a normalizar_texto, mas extrai o codigo de celulas no formato
    "codigo - descricao" (secao 8: campos com codigo e descricao). Usada em
    categoriaNivel1, categoriaNivel2, tipoAvaliacao, naturezaContingencia
    (ex.: "NA - Nao se aplica" ou "NA - Não Aplicável" — o texto da
    descricao nao importa, so o que vem antes do separador), idBacen
    (ex.: "Z1234567 - Banco Alfa" -> "Z1234567") e probabilidadePerda
    (ex.: "PO - Possível", "PR - Provável", "RE - Remoto")."""

    campo = normalizar_texto(nome, valor)
    if not campo.valido:
        return campo

    texto = campo.valor
    if SEPARADOR_CODIGO_DESCRICAO in texto:
        codigo = texto.split(SEPARADOR_CODIGO_DESCRICAO, 1)[0].strip()
        return CampoNormalizado(nome, valor, codigo, StatusCampo.VALIDO)
    return campo


def normalizar_maiusculo(nome: str, valor: object) -> CampoNormalizado:
    """Igual a normalizar_texto, mas converte o texto valido para
    maiusculo (secao 7: codigoConglomerado, tipoRemessa,
    opcaoPorProvisaoAcumulada). Nao e correcao de valor invalido — letras
    minusculas representam o mesmo codigo."""

    campo = normalizar_texto(nome, valor)
    if not campo.valido:
        return campo
    return CampoNormalizado(nome, valor, campo.valor.upper(), StatusCampo.VALIDO)


_CARACTERES_CNPJ_REMOVIDOS = str.maketrans("", "", ".-/")
TAMANHO_RAIZ_CNPJ = 8
TAMANHO_CNPJ_COMPLETO = 14
_PADRAO_SOMENTE_DIGITOS_ASCII = re.compile(r"^[0-9]+$")


def normalizar_cnpj(nome: str, valor: object) -> CampoNormalizado:
    """Igual a normalizar_texto, mas remove '.', '-' e '/' e exige que o
    texto restante tenha exatamente 8 (ja a raiz do CNPJ) ou exatamente 14
    digitos ASCII (CNPJ completo: 8 de raiz + 4 de filial + 2
    verificadores, secao 7) — nesse caso usa os 8 primeiros. Qualquer outra
    contagem de caracteres, ou caracteres que nao sejam digitos ASCII
    (letras, digitos Unicode fora de [0-9]), deixa o campo INVALIDO: nao
    ha truncamento nem invencao de digito."""

    campo = normalizar_texto(nome, valor)
    if not campo.valido:
        return campo

    limpo = campo.valor.translate(_CARACTERES_CNPJ_REMOVIDOS)
    if len(limpo) not in (TAMANHO_RAIZ_CNPJ, TAMANHO_CNPJ_COMPLETO) or not (
        _PADRAO_SOMENTE_DIGITOS_ASCII.match(limpo)
    ):
        return CampoNormalizado(
            nome,
            valor,
            None,
            StatusCampo.INVALIDO,
            motivo=(
                f"CNPJ deve ter {TAMANHO_RAIZ_CNPJ} (raiz) ou "
                f"{TAMANHO_CNPJ_COMPLETO} (completo) dígitos numéricos "
                f"após remover pontuação: {campo.valor!r}."
            ),
        )
    return CampoNormalizado(
        nome, valor, limpo[:TAMANHO_RAIZ_CNPJ], StatusCampo.VALIDO
    )


def normalizar_removendo_caracteres(
    nome: str, valor: object, caracteres: str
) -> CampoNormalizado:
    """Igual a normalizar_texto, mas remove os caracteres indicados do
    texto valido (secao 8): hífen em idEvento (`"IND-0001"` -> `"IND0001"`)
    e ponto em contaBalAnaliticoDebito/Credito e contaCosifDebito/Credito
    (`"819.951.010.4"` -> `"8199510104"`). Nao e correcao de valor
    invalido — os caracteres removidos sao apenas separadores visuais que
    o XSD nao aceita."""

    campo = normalizar_texto(nome, valor)
    if not campo.valido:
        return campo
    tabela = str.maketrans("", "", caracteres)
    return CampoNormalizado(
        nome, valor, campo.valor.translate(tabela), StatusCampo.VALIDO
    )


def normalizar_data(nome: str, valor: object) -> CampoNormalizado:
    texto = _texto_bruto(valor)
    if texto is None:
        return CampoNormalizado(nome, valor, None, StatusCampo.AUSENTE)
    if texto in MARCADORES_INVALIDOS:
        return CampoNormalizado(
            nome,
            valor,
            None,
            StatusCampo.INVALIDO,
            motivo=f"Marcador invalido: {texto}",
        )
    if isinstance(valor, datetime):
        return CampoNormalizado(nome, valor, valor.date(), StatusCampo.VALIDO)
    if isinstance(valor, date):
        return CampoNormalizado(nome, valor, valor, StatusCampo.VALIDO)
    if _PADRAO_DATA_ISO.match(texto):
        try:
            data = date.fromisoformat(texto)
        except ValueError:
            return CampoNormalizado(
                nome,
                valor,
                None,
                StatusCampo.INVALIDO,
                motivo=f"Data invalida: {texto}",
            )
        return CampoNormalizado(nome, valor, data, StatusCampo.VALIDO)
    correspondencia_br = _PADRAO_DATA_BR.match(texto)
    if correspondencia_br:
        dia, mes, ano = (int(grupo) for grupo in correspondencia_br.groups())
        try:
            data = date(ano, mes, dia)
        except ValueError:
            return CampoNormalizado(
                nome,
                valor,
                None,
                StatusCampo.INVALIDO,
                motivo=f"Data invalida: {texto}",
            )
        return CampoNormalizado(nome, valor, data, StatusCampo.VALIDO)
    return CampoNormalizado(
        nome,
        valor,
        None,
        StatusCampo.INVALIDO,
        motivo=(
            "Formato de data nao reconhecido (esperado AAAA-MM-DD ou "
            f"DD/MM/AAAA): {texto}"
        ),
    )


MESES_DATA_BASE_VALIDOS = ("06", "12")
PISO_DATA_BASE = (2020, 12)  # XSD tipoDataMesAno: minInclusive 2020-12


def _motivo_mes_ou_piso_invalido(ano: int, mes: int) -> str | None:
    """None quando ano/mes formam uma data-base valida (Documento 5050 e
    semestral: so meses 06/12, secao 16); string com o motivo caso
    contrario."""

    mes_str = f"{mes:02d}"
    if mes_str not in MESES_DATA_BASE_VALIDOS:
        return (
            "Data-base deve ser de um semestre fechado (mês 06 ou 12): "
            f"mês {mes_str}."
        )
    if (ano, mes) < PISO_DATA_BASE:
        return (
            "Data-base anterior ao piso do XSD (2020-12): "
            f"{ano:04d}-{mes_str}."
        )
    return None


def normalizar_data_base(nome: str, valor: object) -> CampoNormalizado:
    texto = _texto_bruto(valor)
    if texto is None:
        return CampoNormalizado(nome, valor, None, StatusCampo.AUSENTE)
    if texto in MARCADORES_INVALIDOS:
        return CampoNormalizado(
            nome,
            valor,
            None,
            StatusCampo.INVALIDO,
            motivo=f"Marcador invalido: {texto}",
        )
    if isinstance(valor, (datetime, date)):
        motivo = _motivo_mes_ou_piso_invalido(valor.year, valor.month)
        if motivo is not None:
            return CampoNormalizado(nome, valor, None, StatusCampo.INVALIDO, motivo=motivo)
        normalizado = f"{valor.year:04d}-{valor.month:02d}"
        return CampoNormalizado(nome, valor, normalizado, StatusCampo.VALIDO)
    if _PADRAO_DATA_BASE_ISO.match(texto):
        ano, mes = (int(parte) for parte in texto.split("-"))
        motivo = _motivo_mes_ou_piso_invalido(ano, mes)
        if motivo is not None:
            return CampoNormalizado(nome, valor, None, StatusCampo.INVALIDO, motivo=motivo)
        return CampoNormalizado(nome, valor, texto, StatusCampo.VALIDO)
    return CampoNormalizado(
        nome,
        valor,
        None,
        StatusCampo.INVALIDO,
        motivo=(
            f"Formato de data-base nao reconhecido (esperado AAAA-MM): {texto}"
        ),
    )


LIMITE_DIGITOS_INTEIROS = 16  # tipoDecimal do XSD: -?\d{1,16}\.\d{2}
LIMITE_CASAS_DECIMAIS = 2


def _decimal_fora_da_faixa(valor: Decimal) -> bool:
    """True quando o valor tem mais de duas casas decimais reais (zeros a
    direita nao contam: 1427.900 == 1427.90) ou mais digitos inteiros do
    que o XSD aceita (tipoDecimal: ate 16), ou nao e finito (NaN/Infinity).

    Nao usa quantize() (pode lancar InvalidOperation para valores muito
    grandes) nem normalize() (tambem depende da precisao do contexto
    decimal ativo — ex.: Decimal("1"*50 + ".00").normalize() arredonda
    silenciosamente para 28 digitos significativos). Em vez disso, decompoe
    o valor com as_tuple() e remove manualmente so os zeros decimais nao
    significativos — nunca invoca uma operacao dependente do contexto."""

    if not valor.is_finite():
        return True
    if valor.is_zero():
        return False

    _sinal, digitos_tupla, expoente = valor.as_tuple()
    digitos = list(digitos_tupla)

    while expoente < 0 and digitos and digitos[-1] == 0:
        digitos.pop()
        expoente += 1

    if not digitos:
        return False

    casas_decimais = max(-expoente, 0)
    digitos_inteiros = max(len(digitos) + expoente, 1)

    return (
        casas_decimais > LIMITE_CASAS_DECIMAIS
        or digitos_inteiros > LIMITE_DIGITOS_INTEIROS
    )


def normalizar_decimal(nome: str, valor: object) -> CampoNormalizado:
    if isinstance(valor, bool):
        return CampoNormalizado(
            nome,
            valor,
            None,
            StatusCampo.INVALIDO,
            motivo=f"Valor booleano nao e monetario: {valor}",
        )
    if isinstance(valor, (int, float)):
        try:
            decimal_valor = Decimal(str(valor))
        except InvalidOperation:
            return CampoNormalizado(
                nome,
                valor,
                None,
                StatusCampo.INVALIDO,
                motivo=f"Valor numerico invalido: {valor}",
            )
        if _decimal_fora_da_faixa(decimal_valor):
            return CampoNormalizado(
                nome,
                valor,
                None,
                StatusCampo.INVALIDO,
                motivo=(
                    "Valor monetário fora da faixa aceita (até 16 dígitos "
                    f"inteiros e até 2 casas decimais): {valor}"
                ),
            )
        return CampoNormalizado(nome, valor, decimal_valor, StatusCampo.VALIDO)

    texto = _texto_bruto(valor)
    if texto is None:
        return CampoNormalizado(nome, valor, None, StatusCampo.AUSENTE)
    if texto in MARCADORES_INVALIDOS:
        return CampoNormalizado(
            nome,
            valor,
            None,
            StatusCampo.INVALIDO,
            motivo=f"Marcador invalido: {texto}",
        )
    sinal = ""
    corpo = texto
    if corpo.startswith("-"):
        sinal, corpo = "-", corpo[1:]

    texto_decimal = _interpretar_valor_monetario(corpo)
    if texto_decimal is None:
        return CampoNormalizado(
            nome,
            valor,
            None,
            StatusCampo.INVALIDO,
            motivo=f"Formato monetario nao reconhecido: {texto}",
        )
    try:
        decimal_valor = Decimal(sinal + texto_decimal)
    except InvalidOperation:
        return CampoNormalizado(
            nome,
            valor,
            None,
            StatusCampo.INVALIDO,
            motivo=f"Valor numerico invalido: {texto}",
        )
    if _decimal_fora_da_faixa(decimal_valor):
        return CampoNormalizado(
            nome,
            valor,
            None,
            StatusCampo.INVALIDO,
            motivo=(
                "Valor monetário fora da faixa aceita (até 16 dígitos "
                f"inteiros e até 2 casas decimais): {texto}"
            ),
        )
    return CampoNormalizado(nome, valor, decimal_valor, StatusCampo.VALIDO)


def detectar_ausencia_e_invalidez(
    campos: dict[str, CampoNormalizado],
    numero_linha: int,
    id_evento: str | None,
    *,
    sempre_obrigatorios: tuple[str, ...] = CAMPOS_SEMPRE_OBRIGATORIOS,
) -> list[Ocorrencia]:
    """BASE-OBR-001 (ausencia em campo sempre obrigatorio) e BASE-NULO-001
    (marcador invalido, em qualquer campo)."""

    ocorrencias: list[Ocorrencia] = []

    for nome in sempre_obrigatorios:
        campo = campos.get(nome)
        if campo is not None and campo.ausente:
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_NORMALIZACAO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="BASE-OBR-001",
                    descricao="Celula sempre obrigatoria vazia.",
                    detalhe=f"O campo {nome} esta ausente.",
                    linhas=(numero_linha,),
                    id_evento=id_evento,
                    campos=(nome,),
                )
            )

    for nome, campo in campos.items():
        if campo.invalido:
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_NORMALIZACAO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="BASE-NULO-001",
                    descricao=(
                        "Marcador invalido como N/A, NULL, - ou *."
                    ),
                    detalhe=campo.motivo or f"O campo {nome} e invalido.",
                    linhas=(numero_linha,),
                    id_evento=id_evento,
                    campos=(nome,),
                )
            )

    return ocorrencias
