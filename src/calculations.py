"""Agrupamento, probabilidades, contabilizacoes, referencias e totais (Fase 4).

Ver docs/plano_conversor_dro_5050_simples.md secoes 9 a 15.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from src.models import (
    Contabilizacao,
    ETAPA_AGRUPAMENTO,
    EventoAgrupado,
    LinhaNormalizada,
    Ocorrencia,
    Probabilidade,
    TIPO_ERRO_IMPEDITIVO,
)
from src.normalizers import (
    colapsar_espacos_para_validacao,
    maiusculizar_campo,
    normalizar_codigo_rotulado,
    normalizar_data,
    normalizar_decimal,
    normalizar_removendo_caracteres,
    normalizar_texto,
)
from src.reader import ALIAS_CANONICO_POR_NOME_ANTIGO, BASE_COLUNAS
from src.regulatory_constants import (
    DATA_INICIO_2021,
    LIMIAR_EMISSAO_VALOR_TOTAL_RISCO,
)

COLUNAS_DATA: tuple[str, ...] = (
    "dataDescoberta",
    "dataOcorrencia",
    "dataContabilizacao",
)
COLUNAS_DECIMAL: tuple[str, ...] = (
    "valorRisco",
    "valorPerdaEfetiva",
    "valorProvisao",
    "valorRecuperacao",
)
# Aceitam celulas no formato "codigo - descricao" (secao 8).
COLUNAS_CODIGO_ROTULADO: tuple[str, ...] = (
    "categoriaNivel1",
    "categoriaNivel2",
    "tipoAvaliacao",
    "naturezaContingencia",
    "idBacen",
    "probabilidadePerda",
)
# Aceitam hifen decorativo, removido antes de validar (secao 8).
COLUNAS_SEM_HIFEN: tuple[str, ...] = ("idEvento",)
# Aceitam ponto e hifen decorativos, removidos antes de validar (secao 8):
# ex. "8.1.9.99.00-6" -> "819990006".
COLUNAS_SEM_PONTO_E_HIFEN: tuple[str, ...] = (
    "contaBalAnaliticoDebito",
    "contaBalAnaliticoCredito",
    "contaCosifDebito",
    "contaCosifCredito",
)

# Colunas de dominio fechado da Base cujo valor valido e convertido para
# maiusculo (mesmo tratamento ja aplicado ao Cabecalho, secao 7).
# idEvento, codSistemaOrigem e idBacen ficam de fora de proposito: sao
# identidades/referencias externas, nao um conjunto fechado de codigos,
# e o XSD aceita maiusculo/minusculo para elas.
COLUNAS_MAIUSCULAS: frozenset[str] = frozenset(
    {
        "tipoAvaliacao",
        "naturezaContingencia",
        "riscoAssociado",
        "ligadoRiscoSocioAmbiental",
        "ligadoRiscoCibernetico",
        "negocioDescontinuado",
        "probabilidadePerda",
        "fonteRecuperacao",
    }
)

# Campos que devem ser iguais em todas as linhas do mesmo idEvento (secao 10).
CAMPOS_CONSTANTES_NO_EVENTO: tuple[str, ...] = (
    "categoriaNivel1",
    "categoriaNivel2",
    "tipoAvaliacao",
    "unidadeNegocio",
    "dataDescoberta",
    "dataOcorrencia",
    "naturezaContingencia",
    "codSistemaOrigem",
    "nomeSistema",
    "codigoEventoOrigem",
    "descricaoEvento",
    "riscoAssociado",
    "ligadoRiscoSocioAmbiental",
    "ligadoRiscoCibernetico",
    "negocioDescontinuado",
    "idBacen",
)

CODIGOS_PROBABILIDADE = frozenset({"PR", "PO", "RE"})

# Codigos de formato/dominio (Base) cuja presenca faz conversion.py
# suprimir as regras de negocio posteriores a montagem do evento (rodam
# antes do EventoAgrupado existir, entao nao passam por
# validar_formatos_e_dominios_evento).
CODIGOS_FORMATO_QUE_SUPRIMEM_REGRAS = frozenset({
    "BASE-PROBABILIDADE-FORM-001",
    "BASE-FONTERECUPERACAO-FORM-001",
})

COLUNAS_CONTABILIZACAO: tuple[str, ...] = (
    "dataContabilizacao",
    "contaBalAnaliticoDebito",
    "nomeContaDebito",
    "contaBalAnaliticoCredito",
    "nomeContaCredito",
    "contaCosifDebito",
    "contaCosifCredito",
    "valorPerdaEfetiva",
    "valorProvisao",
    "valorRecuperacao",
    "fonteRecuperacao",
)
CAMPOS_CONTABILIZACAO_OBRIGATORIOS: tuple[str, ...] = (
    "dataContabilizacao",
    "valorPerdaEfetiva",
    "valorProvisao",
    "valorRecuperacao",
)

_PADRAO_COSIF = re.compile(r"^(?:[0-9]{8}|[0-9]{10})$")
_PADRAO_NOME_ASCII = re.compile(r"^[A-Za-z0-9 ]{1,70}$")
_PADRAO_COD_SISTEMA_ORIGEM = re.compile(r"^[0-9A-Za-z]{1,10}$")
_PADRAO_CONTA_BAL_ANALITICO = re.compile(r"^[0-9]{1,24}$")


# ---------------------------------------------------------------------------
# Normalizacao de linha completa e agrupamento por idEvento
# ---------------------------------------------------------------------------


def normalizar_linha_base(
    numero_linha: int,
    cabecalhos: tuple[str, ...],
    valores: tuple[object, ...],
) -> LinhaNormalizada:
    brutos: dict[str, object] = {}
    for cabecalho, valor in zip(cabecalhos, valores):
        nome = ALIAS_CANONICO_POR_NOME_ANTIGO.get(cabecalho, cabecalho)
        if nome in BASE_COLUNAS:
            brutos[nome] = valor

    campos = {}
    for nome in BASE_COLUNAS:
        valor_bruto = brutos.get(nome)
        if nome in COLUNAS_DATA:
            campo = normalizar_data(nome, valor_bruto)
        elif nome in COLUNAS_DECIMAL:
            campo = normalizar_decimal(nome, valor_bruto)
        elif nome in COLUNAS_CODIGO_ROTULADO:
            campo = normalizar_codigo_rotulado(nome, valor_bruto)
        elif nome in COLUNAS_SEM_HIFEN:
            campo = normalizar_removendo_caracteres(nome, valor_bruto, "-")
        elif nome in COLUNAS_SEM_PONTO_E_HIFEN:
            campo = normalizar_removendo_caracteres(
                nome, valor_bruto, ".-"
            )
        else:
            campo = normalizar_texto(nome, valor_bruto)
        if nome in COLUNAS_MAIUSCULAS:
            campo = maiusculizar_campo(campo)
        campos[nome] = campo

    return LinhaNormalizada(numero_linha=numero_linha, campos=campos)


def detectar_colisoes_id_evento(
    linhas: list[LinhaNormalizada],
) -> list[Ocorrencia]:
    """BASE-IDEVENTO-COLISAO-001: a remocao de hifen em idEvento (secao 8)
    pode fazer valores originais distintos colidirem no mesmo valor
    normalizado (ex.: "IND-0001" e "IND0001" -> "IND0001"). Compara o
    valor original canonico (str().strip(), o mesmo tratamento de espacos
    usado no resto do projeto) para nao gerar falso positivo por espacos
    externos ou diferenca de tipo (int vs str) vindos do Excel. Chamada
    antes de agrupar_linhas_por_evento, que mantem seu contrato atual
    (agrupa pelo valor normalizado, sem conhecimento de colisao)."""

    originais_por_normalizado: dict[str, dict[str, list[int]]] = {}
    for linha in linhas:
        campo = linha.campos.get("idEvento")
        if campo is None or not campo.valido:
            continue
        normalizado = str(campo.valor)
        original_canonico = str(campo.valor_original).strip()
        originais_por_normalizado.setdefault(normalizado, {}).setdefault(
            original_canonico, []
        ).append(linha.numero_linha)

    ocorrencias: list[Ocorrencia] = []
    for normalizado, originais in originais_por_normalizado.items():
        if len(originais) < 2:
            continue
        todas_linhas = tuple(
            sorted(
                numero_linha
                for linhas_do_original in originais.values()
                for numero_linha in linhas_do_original
            )
        )
        detalhe = "; ".join(
            f"{original!r} (linhas {linhas_do_original})"
            for original, linhas_do_original in originais.items()
        )
        ocorrencias.append(
            Ocorrencia(
                etapa=ETAPA_AGRUPAMENTO,
                tipo=TIPO_ERRO_IMPEDITIVO,
                codigo="BASE-IDEVENTO-COLISAO-001",
                descricao=(
                    "idEvento com valores originais distintos colidindo "
                    "no mesmo valor normalizado."
                ),
                detalhe=f"idEvento normalizado={normalizado!r}: {detalhe}.",
                linhas=todas_linhas,
                id_evento=normalizado,
                campos=("idEvento",),
            )
        )
    return ocorrencias


def agrupar_linhas_por_evento(
    linhas: list[LinhaNormalizada],
) -> dict[str, list[LinhaNormalizada]]:
    """Agrupa por idEvento. Linhas sem idEvento (ja reportadas por
    BASE-OBR-001) nao entram em nenhum grupo."""

    grupos: dict[str, list[LinhaNormalizada]] = {}
    for linha in linhas:
        id_evento = linha.valor("idEvento")
        if id_evento is None:
            continue
        grupos.setdefault(str(id_evento), []).append(linha)
    return grupos


def verificar_consistencia(
    id_evento: str, linhas: list[LinhaNormalizada]
) -> tuple[bool, tuple[str, ...], Ocorrencia | None]:
    """BASE-AGR-001: campos que devem ser iguais em todas as linhas."""

    conflitantes = [
        nome
        for nome in CAMPOS_CONSTANTES_NO_EVENTO
        if len({(linha.status(nome), linha.valor(nome)) for linha in linhas})
        > 1
    ]
    if not conflitantes:
        return True, (), None

    ocorrencia = Ocorrencia(
        etapa=ETAPA_AGRUPAMENTO,
        tipo=TIPO_ERRO_IMPEDITIVO,
        codigo="BASE-AGR-001",
        descricao="Conflito entre campos de nível do mesmo evento.",
        detalhe=(
            "Campos com valores divergentes entre linhas do evento: "
            f"{', '.join(conflitantes)}."
        ),
        linhas=tuple(linha.numero_linha for linha in linhas),
        id_evento=id_evento,
        campos=tuple(conflitantes),
    )
    return False, tuple(conflitantes), ocorrencia


# ---------------------------------------------------------------------------
# Probabilidades (secao 11)
# ---------------------------------------------------------------------------


def extrair_probabilidades(
    linhas: list[LinhaNormalizada],
) -> tuple[tuple[Probabilidade, ...], list[Ocorrencia]]:
    probabilidades: list[Probabilidade] = []
    ocorrencias: list[Ocorrencia] = []

    for linha in linhas:
        campo_codigo = linha.campos["probabilidadePerda"]
        campo_valor = linha.campos["valorRisco"]

        if campo_codigo.invalido:
            continue

        if campo_codigo.valido:
            codigo = str(campo_codigo.valor)
            if codigo not in CODIGOS_PROBABILIDADE:
                ocorrencias.append(
                    Ocorrencia(
                        etapa=ETAPA_AGRUPAMENTO,
                        tipo=TIPO_ERRO_IMPEDITIVO,
                        codigo="BASE-PROBABILIDADE-FORM-001",
                        descricao="probabilidadePerda deve ser PR, PO ou RE.",
                        detalhe=f"probabilidadePerda={codigo!r}.",
                        linhas=(linha.numero_linha,),
                        campos=("probabilidadePerda",),
                    )
                )
                continue  # nao entra no pareamento nem na tupla de probabilidades

        if campo_valor.invalido:
            continue

        if campo_codigo.valido and campo_valor.valido:
            probabilidades.append(
                Probabilidade(
                    numero_linha=linha.numero_linha,
                    codigo=str(campo_codigo.valor),
                    valor_risco=campo_valor.valor,
                )
            )
        elif campo_codigo.valido != campo_valor.valido:
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_AGRUPAMENTO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="BASE-PROB-001",
                    descricao="Probabilidade e valor de risco incompletos.",
                    detalhe=(
                        "probabilidadePerda e valorRisco devem ser "
                        "preenchidos juntos."
                    ),
                    linhas=(linha.numero_linha,),
                    campos=("probabilidadePerda", "valorRisco"),
                )
            )

    return tuple(probabilidades), ocorrencias


def validar_probabilidades_do_evento(
    id_evento: str,
    tipo_avaliacao: object | None,
    probabilidades: tuple[Probabilidade, ...],
) -> list[Ocorrencia]:
    ocorrencias: list[Ocorrencia] = []
    numeros_linha = tuple(p.numero_linha for p in probabilidades)

    if tipo_avaliacao == "NA" and probabilidades:
        ocorrencias.append(
            Ocorrencia(
                etapa=ETAPA_AGRUPAMENTO,
                tipo=TIPO_ERRO_IMPEDITIVO,
                codigo="BASE-PROB-002",
                descricao="Probabilidade informada para avaliação NA.",
                detalhe=(
                    "tipoAvaliacao=NA não aceita probabilidade informada."
                ),
                linhas=numeros_linha,
                id_evento=id_evento,
                campos=("tipoAvaliacao", "probabilidadePerda"),
            )
        )

    codigos = [p.codigo for p in probabilidades]
    if len(probabilidades) > 3 or len(set(codigos)) != len(codigos):
        ocorrencias.append(
            Ocorrencia(
                etapa=ETAPA_AGRUPAMENTO,
                tipo=TIPO_ERRO_IMPEDITIVO,
                codigo="BASE-PROB-003",
                descricao=(
                    "Probabilidade repetida ou mais de três no evento."
                ),
                detalhe=(
                    f"Códigos informados: {', '.join(codigos) or '(nenhum)'}."
                ),
                linhas=numeros_linha,
                id_evento=id_evento,
                campos=("probabilidadePerda",),
            )
        )

    return ocorrencias


# ---------------------------------------------------------------------------
# Contabilizacoes (secao 12)
# ---------------------------------------------------------------------------


def extrair_contabilizacoes(
    linhas: list[LinhaNormalizada],
) -> tuple[tuple[Contabilizacao, ...], list[Ocorrencia]]:
    contabilizacoes: list[Contabilizacao] = []
    ocorrencias: list[Ocorrencia] = []

    for linha in linhas:
        campo_fonte = linha.campos["fonteRecuperacao"]
        if campo_fonte.valido:
            fonte = str(campo_fonte.valor)
            if fonte not in {"S", "O", "NA"}:
                ocorrencias.append(
                    Ocorrencia(
                        etapa=ETAPA_AGRUPAMENTO,
                        tipo=TIPO_ERRO_IMPEDITIVO,
                        codigo="BASE-FONTERECUPERACAO-FORM-001",
                        descricao="fonteRecuperacao deve ser S, O ou NA.",
                        detalhe=f"fonteRecuperacao={fonte!r}.",
                        linhas=(linha.numero_linha,),
                        campos=("fonteRecuperacao",),
                    )
                )

        campos_preenchidos = [
            nome
            for nome in COLUNAS_CONTABILIZACAO
            if linha.campos[nome].valido
        ]
        if not campos_preenchidos:
            continue

        if any(linha.campos[nome].invalido for nome in COLUNAS_CONTABILIZACAO):
            continue

        faltando = [
            nome
            for nome in CAMPOS_CONTABILIZACAO_OBRIGATORIOS
            if linha.campos[nome].ausente
        ]
        if faltando:
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_AGRUPAMENTO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="BASE-CONT-OBR-001",
                    descricao=(
                        "Contabilização iniciada sem dataContabilizacao, "
                        "valorPerdaEfetiva, valorProvisao ou "
                        "valorRecuperacao."
                    ),
                    detalhe=f"Campos ausentes: {', '.join(faltando)}.",
                    linhas=(linha.numero_linha,),
                    campos=tuple(faltando),
                )
            )
            continue

        contabilizacoes.append(
            Contabilizacao(
                numero_linha=linha.numero_linha,
                data_contabilizacao=linha.valor("dataContabilizacao"),
                valor_perda_efetiva=linha.valor("valorPerdaEfetiva"),
                valor_provisao=linha.valor("valorProvisao"),
                valor_recuperacao=linha.valor("valorRecuperacao"),
                fonte_recuperacao=linha.valor("fonteRecuperacao"),
                conta_debito=linha.valor("contaBalAnaliticoDebito"),
                conta_credito=linha.valor("contaBalAnaliticoCredito"),
                conta_cosif_debito=linha.valor("contaCosifDebito"),
                conta_cosif_credito=linha.valor("contaCosifCredito"),
            )
        )

    return tuple(contabilizacoes), ocorrencias


def validar_contabilizacoes(
    id_evento: str,
    contabilizacoes: tuple[Contabilizacao, ...],
    data_ocorrencia: object | None = None,
) -> list[Ocorrencia]:
    ocorrencias: list[Ocorrencia] = []

    for contabilizacao in contabilizacoes:
        linhas = (contabilizacao.numero_linha,)

        if contabilizacao.valor_perda_efetiva < 0:
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_AGRUPAMENTO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="BASE-SINAL-CONT-001",
                    descricao=(
                        "Perda contabilizada informada com sinal negativo."
                    ),
                    detalhe=(
                        "valorPerdaEfetiva="
                        f"{contabilizacao.valor_perda_efetiva:.2f} deve "
                        "usar sinal positivo."
                    ),
                    linhas=linhas,
                    id_evento=id_evento,
                    campos=("valorPerdaEfetiva",),
                )
            )

        if (
            contabilizacao.valor_perda_efetiva == 0
            and contabilizacao.valor_provisao == 0
            and contabilizacao.valor_recuperacao == 0
        ):
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_AGRUPAMENTO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="BASE-CONT-SEM-MOV-001",
                    descricao=(
                        "Contabilização com os três movimentos zerados."
                    ),
                    detalhe=(
                        "valorPerdaEfetiva, valorProvisao e "
                        "valorRecuperacao estão todos zerados."
                    ),
                    linhas=linhas,
                    id_evento=id_evento,
                    campos=(
                        "valorPerdaEfetiva",
                        "valorProvisao",
                        "valorRecuperacao",
                    ),
                )
            )

        if contabilizacao.valor_recuperacao > 0:
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_AGRUPAMENTO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="DRO001411",
                    descricao=(
                        "valorRecuperacao deve ser menor ou igual a zero."
                    ),
                    detalhe=(
                        "valorRecuperacao="
                        f"{contabilizacao.valor_recuperacao:.2f}."
                    ),
                    linhas=linhas,
                    id_evento=id_evento,
                    campos=("valorRecuperacao",),
                )
            )

        fonte = contabilizacao.fonte_recuperacao
        ocorrencia_valida_a_partir_de_2021 = isinstance(
            data_ocorrencia, date
        ) and data_ocorrencia >= DATA_INICIO_2021
        if (
            ocorrencia_valida_a_partir_de_2021
            and contabilizacao.valor_recuperacao < 0
            and fonte not in ("S", "O")
        ):
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_AGRUPAMENTO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="DRO001421",
                    descricao=(
                        "Recuperação efetiva exige fonte S ou O a partir "
                        "de 2021."
                    ),
                    detalhe=(
                        f"dataOcorrencia={data_ocorrencia}, "
                        f"valorRecuperacao={contabilizacao.valor_recuperacao:.2f}"
                        f", fonteRecuperacao={fonte!r}."
                    ),
                    linhas=linhas,
                    id_evento=id_evento,
                    campos=("valorRecuperacao", "fonteRecuperacao"),
                )
            )
        elif contabilizacao.valor_recuperacao == 0 and fonte in ("S", "O"):
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_AGRUPAMENTO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="BASE-REC-FONTE-001",
                    descricao=(
                        "Fonte de recuperação informada sem recuperação "
                        "efetiva."
                    ),
                    detalhe=(
                        "valorRecuperacao=0,00 não aceita "
                        f"fonteRecuperacao={fonte!r}."
                    ),
                    linhas=linhas,
                    id_evento=id_evento,
                    campos=("valorRecuperacao", "fonteRecuperacao"),
                )
            )

    return ocorrencias


def validar_provisao_avaliacao_na(
    id_evento: str,
    tipo_avaliacao: object | None,
    contabilizacoes: tuple[Contabilizacao, ...],
) -> list[Ocorrencia]:
    """DRO001301: tipoAvaliacao=NA não aceita valorProvisao diferente de
    zero."""

    if tipo_avaliacao != "NA":
        return []

    ocorrencias: list[Ocorrencia] = []
    for contabilizacao in contabilizacoes:
        if contabilizacao.valor_provisao != 0:
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_AGRUPAMENTO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="DRO001301",
                    descricao=(
                        "Avaliação NA não aceita provisão diferente de "
                        "zero."
                    ),
                    detalhe=(
                        f"valorProvisao={contabilizacao.valor_provisao:.2f} "
                        "com tipoAvaliacao=NA."
                    ),
                    linhas=(contabilizacao.numero_linha,),
                    id_evento=id_evento,
                    campos=("tipoAvaliacao", "valorProvisao"),
                )
            )
    return ocorrencias


# ---------------------------------------------------------------------------
# Sistemas de origem e contas internas (secao 13)
# ---------------------------------------------------------------------------


def validar_sistemas_e_contas(
    linhas: list[LinhaNormalizada],
) -> list[Ocorrencia]:
    ocorrencias: list[Ocorrencia] = []

    # codigo -> nome_colapsado -> (nome_original_representativo, [linhas]).
    # Usado so para BASE-SIS-001/BASE-CONTA-001 (mesmo codigo, nomes
    # diferentes) — a chave colapsada evita falso conflito por espacamento
    # ("Sistema de Risco" vs "Sistema   de   Risco").
    nomes_por_codigo_sistema: dict[str, dict[str, tuple[str, list[int]]]] = {}
    nomes_por_codigo_conta: dict[str, dict[str, tuple[str, list[int]]]] = {}

    # Estruturas independentes para formato: cada uma dispara mesmo se o
    # campo irmao (codigo sem nome, ou nome sem codigo) estiver ausente.
    linhas_por_codigo_sistema: dict[str, list[int]] = {}
    linhas_por_nome_sistema: dict[str, tuple[str, list[int]]] = {}
    linhas_por_codigo_conta: dict[str, list[tuple[int, str]]] = {}
    linhas_por_nome_conta: dict[str, tuple[str, list[tuple[int, str]]]] = {}

    for linha in linhas:
        codigo_sistema = linha.valor("codSistemaOrigem")
        nome_sistema = linha.valor("nomeSistema")

        if codigo_sistema is not None:
            linhas_por_codigo_sistema.setdefault(
                str(codigo_sistema), []
            ).append(linha.numero_linha)
        if nome_sistema is not None:
            nome_str = str(nome_sistema)
            colapsado = colapsar_espacos_para_validacao(nome_str)
            _, linhas_do_nome = linhas_por_nome_sistema.setdefault(
                colapsado, (nome_str, [])
            )
            linhas_do_nome.append(linha.numero_linha)
        if codigo_sistema is not None and nome_sistema is not None:
            nome_str = str(nome_sistema)
            colapsado = colapsar_espacos_para_validacao(nome_str)
            grupo = nomes_por_codigo_sistema.setdefault(str(codigo_sistema), {})
            _, linhas_do_par = grupo.setdefault(colapsado, (nome_str, []))
            linhas_do_par.append(linha.numero_linha)

        for campo_conta, campo_nome in (
            ("contaBalAnaliticoDebito", "nomeContaDebito"),
            ("contaBalAnaliticoCredito", "nomeContaCredito"),
        ):
            codigo_conta = linha.valor(campo_conta)
            nome_conta = linha.valor(campo_nome)

            if codigo_conta is not None:
                linhas_por_codigo_conta.setdefault(str(codigo_conta), []).append(
                    (linha.numero_linha, campo_conta)
                )
            if nome_conta is not None:
                nome_str = str(nome_conta)
                colapsado = colapsar_espacos_para_validacao(nome_str)
                _, linhas_do_nome = linhas_por_nome_conta.setdefault(
                    colapsado, (nome_str, [])
                )
                linhas_do_nome.append((linha.numero_linha, campo_nome))
            if codigo_conta is not None and nome_conta is not None:
                nome_str = str(nome_conta)
                colapsado = colapsar_espacos_para_validacao(nome_str)
                grupo = nomes_por_codigo_conta.setdefault(str(codigo_conta), {})
                _, linhas_do_par = grupo.setdefault(colapsado, (nome_str, []))
                linhas_do_par.append(linha.numero_linha)

        for campo_cosif, campo_conta in (
            ("contaCosifDebito", "contaBalAnaliticoDebito"),
            ("contaCosifCredito", "contaBalAnaliticoCredito"),
        ):
            valor_cosif = linha.valor(campo_cosif)
            if valor_cosif is not None:
                if not _PADRAO_COSIF.match(str(valor_cosif)):
                    ocorrencias.append(
                        Ocorrencia(
                            etapa=ETAPA_AGRUPAMENTO,
                            tipo=TIPO_ERRO_IMPEDITIVO,
                            codigo="BASE-COSIF-FORM-001",
                            descricao="COSIF não possui 8 ou 10 dígitos.",
                            detalhe=f"{campo_cosif}={valor_cosif!r}.",
                            linhas=(linha.numero_linha,),
                            campos=(campo_cosif,),
                        )
                    )
                if linha.valor(campo_conta) is None:
                    # DRO001443/DRO001444 (planilha oficial de criticas de
                    # pre-processamento): verifica, quando ha lancamento em
                    # contaCosifDebito/Credito, se o contaBalAnaliticoDebito/
                    # Credito correspondente foi preenchido.
                    codigo_regra = (
                        "DRO001443"
                        if campo_conta == "contaBalAnaliticoDebito"
                        else "DRO001444"
                    )
                    ocorrencias.append(
                        Ocorrencia(
                            etapa=ETAPA_AGRUPAMENTO,
                            tipo=TIPO_ERRO_IMPEDITIVO,
                            codigo=codigo_regra,
                            descricao=(
                                f"{campo_cosif} preenchida exige "
                                f"{campo_conta}."
                            ),
                            detalhe=(
                                f"{campo_cosif}={valor_cosif!r} sem "
                                f"{campo_conta}."
                            ),
                            linhas=(linha.numero_linha,),
                            campos=(campo_cosif, campo_conta),
                        )
                    )

    for codigo, nomes in nomes_por_codigo_sistema.items():
        if len(nomes) > 1:
            linhas_afetadas = tuple(
                sorted(
                    numero
                    for _, numeros in nomes.values()
                    for numero in numeros
                )
            )
            nomes_originais = sorted(
                nome_original for nome_original, _ in nomes.values()
            )
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_AGRUPAMENTO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="BASE-SIS-001",
                    descricao="Mesmo sistema associado a nomes diferentes.",
                    detalhe=(
                        f"codSistemaOrigem={codigo!r} possui os nomes: "
                        f"{', '.join(nomes_originais)}."
                    ),
                    linhas=linhas_afetadas,
                    campos=("codSistemaOrigem", "nomeSistema"),
                )
            )

    for codigo, nomes in nomes_por_codigo_conta.items():
        if len(nomes) > 1:
            linhas_afetadas = tuple(
                sorted(
                    numero
                    for _, numeros in nomes.values()
                    for numero in numeros
                )
            )
            nomes_originais = sorted(
                nome_original for nome_original, _ in nomes.values()
            )
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_AGRUPAMENTO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="BASE-CONTA-001",
                    descricao="Mesma conta associada a nomes diferentes.",
                    detalhe=(
                        f"conta={codigo!r} possui os nomes: "
                        f"{', '.join(nomes_originais)}."
                    ),
                    linhas=linhas_afetadas,
                    campos=(
                        "contaBalAnaliticoDebito",
                        "contaBalAnaliticoCredito",
                    ),
                )
            )

    for codigo, linhas_do_codigo in linhas_por_codigo_sistema.items():
        if not _PADRAO_COD_SISTEMA_ORIGEM.fullmatch(codigo):
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_AGRUPAMENTO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="BASE-SISTEMA-FORM-001",
                    descricao=(
                        "codSistemaOrigem deve ser alfanumérico, até 10 "
                        "caracteres."
                    ),
                    detalhe=f"codSistemaOrigem={codigo!r}.",
                    linhas=tuple(sorted(linhas_do_codigo)),
                    campos=("codSistemaOrigem",),
                )
            )

    for colapsado, (nome_original, linhas_do_nome) in linhas_por_nome_sistema.items():
        if not _PADRAO_NOME_ASCII.fullmatch(colapsado):
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_AGRUPAMENTO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="BASE-NOMESISTEMA-FORM-001",
                    descricao=(
                        "nomeSistema deve ser alfanumérico+espaço, até 70 "
                        "caracteres."
                    ),
                    detalhe=f"nomeSistema={nome_original!r}.",
                    linhas=tuple(sorted(linhas_do_nome)),
                    campos=("nomeSistema",),
                )
            )

    for codigo, ocorrencias_do_codigo in linhas_por_codigo_conta.items():
        if not _PADRAO_CONTA_BAL_ANALITICO.fullmatch(codigo):
            linhas_afetadas = tuple(
                sorted({numero for numero, _ in ocorrencias_do_codigo})
            )
            campos_afetados = tuple(
                sorted({campo for _, campo in ocorrencias_do_codigo})
            )
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_AGRUPAMENTO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="BASE-CONTABAL-FORM-001",
                    descricao=(
                        "Conta interna (contaBalAnaliticoDebito/Credito) "
                        "deve ter de 1 a 24 dígitos."
                    ),
                    detalhe=f"conta={codigo!r}.",
                    linhas=linhas_afetadas,
                    campos=campos_afetados,
                )
            )

    for colapsado, (nome_original, ocorrencias_do_nome) in linhas_por_nome_conta.items():
        if not _PADRAO_NOME_ASCII.fullmatch(colapsado):
            linhas_afetadas = tuple(
                sorted({numero for numero, _ in ocorrencias_do_nome})
            )
            campos_afetados = tuple(
                sorted({campo for _, campo in ocorrencias_do_nome})
            )
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_AGRUPAMENTO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="BASE-NOMECONTA-FORM-001",
                    descricao=(
                        "Nome da conta interna (nomeContaDebito/Credito) "
                        "deve ser alfanumérico+espaço, até 70 caracteres."
                    ),
                    detalhe=f"nomeConta={nome_original!r}.",
                    linhas=linhas_afetadas,
                    campos=campos_afetados,
                )
            )

    return ocorrencias


# ---------------------------------------------------------------------------
# Totais por evento (secao 15)
# ---------------------------------------------------------------------------


def calcular_totais(evento: EventoAgrupado) -> EventoAgrupado:
    """Calcula os totais do evento; None quando o evento nao e consistente."""

    if not evento.consistente:
        return evento

    total_perda = sum(
        (c.valor_perda_efetiva for c in evento.contabilizacoes),
        Decimal("0.00"),
    )
    total_provisao = sum(
        (c.valor_provisao for c in evento.contabilizacoes),
        Decimal("0.00"),
    )
    total_recuperado = sum(
        (c.valor_recuperacao for c in evento.contabilizacoes),
        Decimal("0.00"),
    )

    tipo_avaliacao = evento.valor_evento("tipoAvaliacao")
    valor_total_risco = None
    if tipo_avaliacao == "I":
        soma_risco = sum(
            (p.valor_risco for p in evento.probabilidades),
            Decimal("0.00"),
        )
        calculado = total_provisao + soma_risco
        # Instrucoes de Preenchimento 12/2020, item "k": o valor minimo
        # para um evento ser incluido no campo valorTotalRisco e
        # R$10.000.000,00; abaixo disso, o campo nao deve ser informado.
        if calculado >= LIMIAR_EMISSAO_VALOR_TOTAL_RISCO:
            valor_total_risco = calculado

    evento.total_perda_efetiva = total_perda
    evento.total_provisao = total_provisao
    evento.total_recuperado = total_recuperado
    evento.valor_total_risco = valor_total_risco
    return evento


def validar_convencao_de_sinal(evento: EventoAgrupado) -> Ocorrencia | None:
    """BASE-SINAL-EVENTO-001 (secao 15): sinal dos totais do evento."""

    if not evento.consistente:
        return None

    violacoes = []
    if evento.total_perda_efetiva is not None and evento.total_perda_efetiva < 0:
        violacoes.append("totalPerdaEfetiva")
    if evento.total_provisao is not None and evento.total_provisao < 0:
        violacoes.append("totalProvisao")
    if evento.total_recuperado is not None and evento.total_recuperado > 0:
        violacoes.append("totalRecuperado")
    if evento.valor_total_risco is not None and evento.valor_total_risco < 0:
        violacoes.append("valorTotalRisco")

    if not violacoes:
        return None

    return Ocorrencia(
        etapa=ETAPA_AGRUPAMENTO,
        tipo=TIPO_ERRO_IMPEDITIVO,
        codigo="BASE-SINAL-EVENTO-001",
        descricao="Totais do evento agrupado violam a convenção de sinal.",
        detalhe=f"Campos com sinal inválido: {', '.join(violacoes)}.",
        linhas=evento.numeros_linha,
        id_evento=evento.id_evento,
        campos=tuple(violacoes),
    )


def montar_evento(
    id_evento: str, linhas: list[LinhaNormalizada]
) -> tuple[EventoAgrupado, list[Ocorrencia]]:
    """Funcao de conveniencia: roda todas as etapas da Fase 4 para 1 evento."""

    ocorrencias: list[Ocorrencia] = []

    consistente, campos_conflitantes, ocorrencia_conflito = (
        verificar_consistencia(id_evento, linhas)
    )
    if ocorrencia_conflito is not None:
        ocorrencias.append(ocorrencia_conflito)

    probabilidades, ocorrencias_prob = extrair_probabilidades(linhas)
    ocorrencias.extend(ocorrencias_prob)

    contabilizacoes, ocorrencias_cont = extrair_contabilizacoes(linhas)
    ocorrencias.extend(ocorrencias_cont)

    evento = EventoAgrupado(
        id_evento=id_evento,
        linhas=tuple(linhas),
        consistente=consistente,
        campos_conflitantes=campos_conflitantes,
        probabilidades=probabilidades,
        contabilizacoes=contabilizacoes,
    )

    if consistente:
        tipo_avaliacao = evento.valor_evento("tipoAvaliacao")
        ocorrencias.extend(
            validar_probabilidades_do_evento(
                id_evento, tipo_avaliacao, probabilidades
            )
        )
        data_ocorrencia = evento.valor_evento("dataOcorrencia")
        ocorrencias.extend(
            validar_contabilizacoes(
                id_evento, contabilizacoes, data_ocorrencia
            )
        )
        ocorrencias.extend(
            validar_provisao_avaliacao_na(
                id_evento, tipo_avaliacao, contabilizacoes
            )
        )
        evento = calcular_totais(evento)
        ocorrencia_sinal = validar_convencao_de_sinal(evento)
        if ocorrencia_sinal is not None:
            ocorrencias.append(ocorrencia_sinal)

    return evento, ocorrencias


# ---------------------------------------------------------------------------
# Blocos de referencia para o XML (secao 13/20): sistemas e contas
# deduplicados globalmente por codigo. Pressupoe que
# validar_sistemas_e_contas ja rodou e nao encontrou BASE-SIS-001/
# BASE-CONTA-001 (codigo com nomes conflitantes) para os dados em questao.
# ---------------------------------------------------------------------------


def construir_mapa_sistemas(linhas: list[LinhaNormalizada]) -> dict[str, str]:
    mapa: dict[str, str] = {}
    for linha in linhas:
        codigo = linha.valor("codSistemaOrigem")
        nome = linha.valor("nomeSistema")
        if codigo is not None and nome is not None:
            mapa.setdefault(str(codigo), str(nome))
    return mapa


def construir_mapa_contas(linhas: list[LinhaNormalizada]) -> dict[str, str]:
    mapa: dict[str, str] = {}
    for linha in linhas:
        for campo_conta, campo_nome in (
            ("contaBalAnaliticoDebito", "nomeContaDebito"),
            ("contaBalAnaliticoCredito", "nomeContaCredito"),
        ):
            codigo = linha.valor(campo_conta)
            nome = linha.valor(campo_nome)
            if codigo is not None and nome is not None:
                mapa.setdefault(str(codigo), str(nome))
    return mapa
