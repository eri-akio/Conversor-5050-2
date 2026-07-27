"""Criticas locais de pre-processamento (Fase 5).

28 criticas oficiais executadas localmente (secao 17) + BASE-CONT-001
(secao 9) + classificacao individualizado/consolidado (secao 16).

O relatorio so mostra problemas (secao 21): cada funcao aqui retorna uma
Ocorrencia (ou None/lista vazia) somente quando encontra um problema. Uma
regra aprovada nao produz nenhum registro.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from src.models import (
    CampoNormalizado,
    ETAPA_PRE_PROCESSAMENTO,
    EventoAgrupado,
    Ocorrencia,
    TIPO_ERRO_IMPEDITIVO,
)
from src.normalizers import colapsar_espacos_para_validacao
from src.regulatory_constants import (
    CODIGOS_CONGLOMERADOS_VALIDOS,
    CONTAS_COSIF_VALIDAS,
    DATA_INICIO_2021,
    LIMIAR_INDIVIDUALIZACAO,
    LIMIAR_RISCO_NAO_COBERTO,
)

LIMIAR_MATERIALIDADE = Decimal("1000000.00")

NATUREZAS_CONTINGENCIA = frozenset({"TRI", "TRA", "CIV"})

# Formato/tamanho/dominio dos campos constantes no evento (secao 20 do
# plano: espelha facetas do XSD 06/2025 que hoje so seriam pegas tarde,
# na validacao contra o XSD). Ver validar_formatos_e_dominios_evento.
_PADRAO_ID_EVENTO = re.compile(r"^[0-9A-Za-z]{1,40}$")
_PADRAO_CATEGORIA_NIVEL1 = re.compile(r"^[1-8]$")
_PADRAO_CATEGORIA_NIVEL2 = re.compile(
    r"^(?:11|12|21|22|31|32|33|41|42|43|44|45|51|61|71|8[1-6])$"
)
TIPOS_AVALIACAO_VALIDOS = frozenset({"I", "M", "NA"})
_PADRAO_UNIDADE_NEGOCIO = re.compile(r"^[1-8]$")
NATUREZAS_CONTINGENCIA_VALIDAS = NATUREZAS_CONTINGENCIA | {"NA"}
_PADRAO_CODIGO_EVENTO_ORIGEM = re.compile(r"^[0-9A-Za-z]{1,73}$")
LIMITE_DESCRICAO_EVENTO = 200
_PADRAO_ID_BACEN = re.compile(r"^(?:[Zz][0-9]{7}|[Ii][0-9]{5})$")
RISCOS_ASSOCIADOS_VALIDOS = frozenset({"C", "M", "NA"})
OPCOES_SIM_NAO = frozenset({"S", "N"})


def _erro(
    evento: EventoAgrupado,
    codigo: str,
    descricao: str,
    detalhe: str,
    campos: tuple[str, ...] = (),
) -> Ocorrencia:
    return Ocorrencia(
        etapa=ETAPA_PRE_PROCESSAMENTO,
        tipo=TIPO_ERRO_IMPEDITIVO,
        codigo=codigo,
        descricao=descricao,
        detalhe=detalhe,
        linhas=evento.numeros_linha,
        id_evento=evento.id_evento,
        campos=campos,
    )


def _campo_ausente(evento: EventoAgrupado, nome: str) -> bool:
    return evento.linhas[0].status(nome).name == "AUSENTE"


def _soma_risco(evento: EventoAgrupado) -> Decimal:
    return sum(
        (p.valor_risco for p in evento.probabilidades), Decimal("0.00")
    )


# ---------------------------------------------------------------------------
# Secao 9 - obrigatoriedade condicional a partir de 2021 e dominio
# ---------------------------------------------------------------------------


def validar_ordem_datas(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO001201."""

    descoberta = evento.valor_evento("dataDescoberta")
    ocorrencia_data = evento.valor_evento("dataOcorrencia")
    if descoberta is None or ocorrencia_data is None:
        return None
    if ocorrencia_data > descoberta:
        return _erro(
            evento,
            "DRO001201",
            "dataOcorrencia deve ser menor ou igual a dataDescoberta.",
            f"dataOcorrencia={ocorrencia_data} > dataDescoberta={descoberta}.",
            ("dataOcorrencia", "dataDescoberta"),
        )
    return None


def validar_descoberta_obrigatoria(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO001202."""

    ocorrencia_data = evento.valor_evento("dataOcorrencia")
    if not isinstance(ocorrencia_data, date) or ocorrencia_data < DATA_INICIO_2021:
        return None
    if _campo_ausente(evento, "dataDescoberta"):
        return _erro(
            evento,
            "DRO001202",
            "dataDescoberta obrigatória para ocorrência a partir de 2021.",
            f"dataOcorrencia={ocorrencia_data}, dataDescoberta ausente.",
            ("dataDescoberta",),
        )
    return None


def validar_categoria_nivel2_obrigatoria(
    evento: EventoAgrupado,
) -> Ocorrencia | None:
    """DRO001212."""

    ocorrencia_data = evento.valor_evento("dataOcorrencia")
    if not isinstance(ocorrencia_data, date) or ocorrencia_data < DATA_INICIO_2021:
        return None
    if _campo_ausente(evento, "categoriaNivel2"):
        return _erro(
            evento,
            "DRO001212",
            "categoriaNivel2 obrigatória para ocorrência a partir de 2021.",
            f"dataOcorrencia={ocorrencia_data}, categoriaNivel2 ausente.",
            ("categoriaNivel2",),
        )
    return None


def validar_risco_associado_obrigatorio(
    evento: EventoAgrupado,
) -> Ocorrencia | None:
    """DRO001251."""

    ocorrencia_data = evento.valor_evento("dataOcorrencia")
    if not isinstance(ocorrencia_data, date) or ocorrencia_data < DATA_INICIO_2021:
        return None
    if _campo_ausente(evento, "riscoAssociado"):
        return _erro(
            evento,
            "DRO001251",
            "riscoAssociado obrigatório para ocorrência a partir de 2021.",
            f"dataOcorrencia={ocorrencia_data}, riscoAssociado ausente.",
            ("riscoAssociado",),
        )
    return None


def validar_ligado_risco_socioambiental_obrigatorio(
    evento: EventoAgrupado,
) -> Ocorrencia | None:
    """DRO001252."""

    ocorrencia_data = evento.valor_evento("dataOcorrencia")
    if not isinstance(ocorrencia_data, date) or ocorrencia_data < DATA_INICIO_2021:
        return None
    if _campo_ausente(evento, "ligadoRiscoSocioAmbiental"):
        return _erro(
            evento,
            "DRO001252",
            (
                "ligadoRiscoSocioAmbiental obrigatório para ocorrência a "
                "partir de 2021."
            ),
            f"dataOcorrencia={ocorrencia_data}, campo ausente.",
            ("ligadoRiscoSocioAmbiental",),
        )
    return None


def validar_ligado_risco_cibernetico_obrigatorio(
    evento: EventoAgrupado,
) -> Ocorrencia | None:
    """DRO001253."""

    ocorrencia_data = evento.valor_evento("dataOcorrencia")
    if not isinstance(ocorrencia_data, date) or ocorrencia_data < DATA_INICIO_2021:
        return None
    if _campo_ausente(evento, "ligadoRiscoCibernetico"):
        return _erro(
            evento,
            "DRO001253",
            (
                "ligadoRiscoCibernetico obrigatório para ocorrência a "
                "partir de 2021."
            ),
            f"dataOcorrencia={ocorrencia_data}, campo ausente.",
            ("ligadoRiscoCibernetico",),
        )
    return None


def validar_natureza_contingencia_avaliacao(
    evento: EventoAgrupado,
) -> Ocorrencia | None:
    """BASE-CONT-001 (secao 9, regra local)."""

    natureza = evento.valor_evento("naturezaContingencia")
    avaliacao = evento.valor_evento("tipoAvaliacao")
    if natureza is None or avaliacao is None:
        return None

    if natureza == "NA" and avaliacao != "NA":
        return _erro(
            evento,
            "BASE-CONT-001",
            "Natureza da contingência incompatível com avaliação.",
            f"naturezaContingencia=NA exige tipoAvaliacao=NA (era {avaliacao}).",
            ("naturezaContingencia", "tipoAvaliacao"),
        )
    if natureza in NATUREZAS_CONTINGENCIA and avaliacao not in ("I", "M"):
        return _erro(
            evento,
            "BASE-CONT-001",
            "Natureza da contingência incompatível com avaliação.",
            (
                f"naturezaContingencia={natureza} exige tipoAvaliacao I ou M "
                f"(era {avaliacao})."
            ),
            ("naturezaContingencia", "tipoAvaliacao"),
        )
    return None


# ---------------------------------------------------------------------------
# Secao 15 - totais calculados
# ---------------------------------------------------------------------------


def validar_limite_recuperacao(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO001232."""

    if evento.total_recuperado is None:
        return None
    limite = abs(evento.total_perda_efetiva or Decimal("0")) + abs(
        evento.total_provisao or Decimal("0")
    )
    if abs(evento.total_recuperado) > limite:
        return _erro(
            evento,
            "DRO001232",
            (
                "totalRecuperado não pode superar, em módulo, a soma de "
                "perda e provisão."
            ),
            (
                f"|totalRecuperado|={abs(evento.total_recuperado):.2f} > "
                f"|perda|+|provisão|={limite:.2f}."
            ),
            ("totalRecuperado", "totalPerdaEfetiva", "totalProvisao"),
        )
    return None


def validar_natureza_para_risco(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO001233."""

    if not evento.valor_total_risco:
        return None
    natureza = evento.valor_evento("naturezaContingencia")
    if natureza not in NATUREZAS_CONTINGENCIA:
        return _erro(
            evento,
            "DRO001233",
            (
                "Risco informado exige natureza TRI, TRA ou CIV."
            ),
            f"valorTotalRisco={evento.valor_total_risco:.2f}, naturezaContingencia={natureza!r}.",
            ("valorTotalRisco", "naturezaContingencia"),
        )
    return None


def validar_descricao_materialidade(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO001241 (formula estrita da critica oficial, secao 15)."""

    ocorrencia_data = evento.valor_evento("dataOcorrencia")
    if not isinstance(ocorrencia_data, date) or ocorrencia_data < DATA_INICIO_2021:
        return None
    if evento.total_perda_efetiva is None:
        return None

    materialidade = evento.total_perda_efetiva + (
        evento.valor_total_risco or Decimal("0")
    )
    if materialidade >= LIMIAR_MATERIALIDADE and _campo_ausente(
        evento, "descricaoEvento"
    ):
        return _erro(
            evento,
            "DRO001241",
            "Descrição obrigatória pela fórmula oficial de materialidade.",
            f"valorMaterialidade={materialidade:.2f} >= 1.000.000,00.",
            ("descricaoEvento",),
        )
    return None


def validar_provisao_avaliacao_im(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO001302: avaliação I ou M exige tratamento coerente da provisão.

    Um evento exclusivamente de risco (DRO001452) e isento: nesse caso a
    ausencia de contabilizacoes e exigida, nao um erro de provisao nao
    informada. Fora desse caso, `not evento.contabilizacoes` e um proxy
    correto para "nenhuma provisao informada": extrair_contabilizacoes so
    cria uma Contabilizacao quando valorProvisao ja foi validado como
    presente (senao gera BASE-CONT-OBR-001 e descarta a linha) -- entao
    toda contabilizacao existente ja tem valorProvisao genuinamente
    informado."""

    avaliacao = evento.valor_evento("tipoAvaliacao")
    if avaliacao not in ("I", "M"):
        return None
    if evento.contabilizacoes or _evento_apenas_risco(evento):
        return None
    return _erro(
        evento,
        "DRO001302",
        "Avaliação I/M exige tratamento coerente da provisão.",
        "Nenhum valorProvisao foi informado no evento.",
        ("tipoAvaliacao", "valorProvisao"),
    )


def validar_composicao_risco_total(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO001311: valorTotalRisco = totalProvisao + soma(valorRisco).

    O calculo (calculations.calcular_totais) ja aplica esta formula
    diretamente; esta funcao existe para deixar a critica oficial
    explicitamente registrada e testavel."""

    if evento.valor_total_risco is None:
        return None
    esperado = (evento.total_provisao or Decimal("0")) + _soma_risco(evento)
    if evento.valor_total_risco != esperado:
        return _erro(
            evento,
            "DRO001311",
            "valorTotalRisco deve ser igual a totalProvisao + soma(valorRisco).",
            f"valorTotalRisco={evento.valor_total_risco:.2f}, esperado={esperado:.2f}.",
            ("valorTotalRisco", "totalProvisao"),
        )
    return None


def validar_probabilidade_obrigatoria_individual(
    evento: EventoAgrupado,
) -> Ocorrencia | None:
    """DRO001312."""

    avaliacao = evento.valor_evento("tipoAvaliacao")
    ocorrencia_data = evento.valor_evento("dataOcorrencia")
    if avaliacao != "I" or not isinstance(ocorrencia_data, date):
        return None
    if ocorrencia_data < DATA_INICIO_2021:
        return None
    if not evento.probabilidades:
        return _erro(
            evento,
            "DRO001312",
            "Avaliação individual a partir de 2021 exige probabilidade.",
            "Nenhuma probabilidade foi informada no evento.",
            ("probabilidadePerda",),
        )
    return None


def validar_probabilidade_proibida_massificada(
    evento: EventoAgrupado,
) -> Ocorrencia | None:
    """DRO001313."""

    if evento.valor_evento("tipoAvaliacao") != "M":
        return None
    if evento.probabilidades:
        return _erro(
            evento,
            "DRO001313",
            "Avaliação massificada não aceita probabilidade.",
            "tipoAvaliacao=M com probabilidade informada.",
            ("tipoAvaliacao", "probabilidadePerda"),
        )
    return None


def validar_soma_risco_positiva(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO001314."""

    ocorrencia_data = evento.valor_evento("dataOcorrencia")
    avaliacao = evento.valor_evento("tipoAvaliacao")
    natureza = evento.valor_evento("naturezaContingencia")
    if (
        not isinstance(ocorrencia_data, date)
        or ocorrencia_data < DATA_INICIO_2021
        or avaliacao != "I"
        or natureza == "NA"
        or not evento.probabilidades
    ):
        return None
    if _soma_risco(evento) <= 0:
        return _erro(
            evento,
            "DRO001314",
            "Soma dos valores de risco deve ser positiva no contexto aplicável.",
            f"soma(valorRisco)={_soma_risco(evento):.2f}.",
            ("valorRisco",),
        )
    return None


# ---------------------------------------------------------------------------
# Secao 13 - referencias de sistemas e contas (unicidade global ja garantida
# em calculations.validar_sistemas_e_contas; aqui verificamos apenas se o
# evento referencia um sistema/conta que ele proprio informou)
# ---------------------------------------------------------------------------


def validar_sistema_referenciado(
    evento: EventoAgrupado, sistemas_globais: dict[str, str]
) -> Ocorrencia | None:
    """DRO001321: codSistemaOrigem informado deve existir no Bloco 3
    (bloco global de sistemas, calculations.construir_mapa_sistemas) --
    nao precisa ter nomeSistema preenchido na mesma linha/evento que o
    referencia (planilha oficial: "Verifica se o codigo preenchido...
    esta devidamente informado no Bloco 3"). A ausencia do proprio
    codSistemaOrigem/nomeSistema em cada linha ja e coberta
    separadamente por BASE-OBR-001 (ambos estao em
    CAMPOS_SEMPRE_OBRIGATORIOS)."""

    codigo = evento.valor_evento("codSistemaOrigem")
    if codigo is None:
        return None
    if str(codigo) not in sistemas_globais:
        return _erro(
            evento,
            "DRO001321",
            "Sistema do evento deve existir no bloco de sistemas.",
            f"codSistemaOrigem={codigo!r} não encontrado no bloco de sistemas.",
            ("codSistemaOrigem",),
        )
    return None


def validar_contas_referenciadas(
    evento: EventoAgrupado, contas_globais: dict[str, str]
) -> list[Ocorrencia]:
    """DRO001401/DRO001402: a conta interna referenciada em cada
    contabilizacao deve existir no bloco global de contas (Bloco 4,
    calculations.construir_mapa_contas) -- nao precisa ter o nome
    repetido na mesma linha que a referencia (planilha oficial: "se a
    referida conta esta devidamente informada no campo codigoConta do
    Bloco 4")."""

    ocorrencias: list[Ocorrencia] = []
    for contabilizacao in evento.contabilizacoes:
        if (
            contabilizacao.conta_debito is not None
            and str(contabilizacao.conta_debito) not in contas_globais
        ):
            ocorrencias.append(
                _erro(
                    evento,
                    "DRO001401",
                    "Conta interna de débito deve existir no bloco de contas.",
                    f"contaBalAnaliticoDebito={contabilizacao.conta_debito!r} não encontrada no bloco de contas.",
                    ("contaBalAnaliticoDebito",),
                )
            )
        if (
            contabilizacao.conta_credito is not None
            and str(contabilizacao.conta_credito) not in contas_globais
        ):
            ocorrencias.append(
                _erro(
                    evento,
                    "DRO001402",
                    "Conta interna de crédito deve existir no bloco de contas.",
                    f"contaBalAnaliticoCredito={contabilizacao.conta_credito!r} não encontrada no bloco de contas.",
                    ("contaBalAnaliticoCredito",),
                )
            )
    return ocorrencias


def validar_cosif_obrigatorio(evento: EventoAgrupado) -> list[Ocorrencia]:
    """DRO001441/DRO001442."""

    ocorrencias: list[Ocorrencia] = []
    for contabilizacao in evento.contabilizacoes:
        if (
            contabilizacao.conta_debito is not None
            and contabilizacao.conta_cosif_debito is None
        ):
            ocorrencias.append(
                _erro(
                    evento,
                    "DRO001441",
                    "Conta interna de débito exige conta COSIF de débito.",
                    f"contaBalAnaliticoDebito={contabilizacao.conta_debito!r} sem COSIF.",
                    ("contaBalAnaliticoDebito", "contaCosifDebito"),
                )
            )
        if (
            contabilizacao.conta_credito is not None
            and contabilizacao.conta_cosif_credito is None
        ):
            ocorrencias.append(
                _erro(
                    evento,
                    "DRO001442",
                    "Conta interna de crédito exige conta COSIF de crédito.",
                    f"contaBalAnaliticoCredito={contabilizacao.conta_credito!r} sem COSIF.",
                    ("contaBalAnaliticoCredito", "contaCosifCredito"),
                )
            )
    return ocorrencias


def validar_conta_cosif_debito(evento: EventoAgrupado) -> list[Ocorrencia]:
    """DRO001431: a conta COSIF de debito informada deve existir no
    cadastro oficial COSIF (src.regulatory_constants.CONTAS_COSIF_VALIDAS)."""

    ocorrencias: list[Ocorrencia] = []
    for contabilizacao in evento.contabilizacoes:
        if (
            contabilizacao.conta_cosif_debito is not None
            and str(contabilizacao.conta_cosif_debito) not in CONTAS_COSIF_VALIDAS
        ):
            ocorrencias.append(
                _erro(
                    evento,
                    "DRO001431",
                    "Conta COSIF de débito deve existir no cadastro oficial COSIF.",
                    f"contaCosifDebito={contabilizacao.conta_cosif_debito!r} não encontrada no cadastro COSIF.",
                    ("contaCosifDebito",),
                )
            )
    return ocorrencias


def validar_conta_cosif_credito(evento: EventoAgrupado) -> list[Ocorrencia]:
    """DRO001432: a conta COSIF de credito informada deve existir no
    cadastro oficial COSIF (src.regulatory_constants.CONTAS_COSIF_VALIDAS)."""

    ocorrencias: list[Ocorrencia] = []
    for contabilizacao in evento.contabilizacoes:
        if (
            contabilizacao.conta_cosif_credito is not None
            and str(contabilizacao.conta_cosif_credito) not in CONTAS_COSIF_VALIDAS
        ):
            ocorrencias.append(
                _erro(
                    evento,
                    "DRO001432",
                    "Conta COSIF de crédito deve existir no cadastro oficial COSIF.",
                    f"contaCosifCredito={contabilizacao.conta_cosif_credito!r} não encontrada no cadastro COSIF.",
                    ("contaCosifCredito",),
                )
            )
    return ocorrencias


# ---------------------------------------------------------------------------
# Secao 12 - evento exclusivamente de risco vs. evento com movimento contabil
# ---------------------------------------------------------------------------


def _evento_apenas_risco(evento: EventoAgrupado) -> bool:
    """True quando o evento e EXCLUSIVAMENTE de risco (soma de valorRisco
    positiva e nenhum movimento real de perda/provisao/recuperacao). Um
    evento com risco e movimento real ao mesmo tempo nao e "exclusivamente
    de risco". Compartilhado por DRO001302 e DRO001452."""

    return (
        _soma_risco(evento) > 0
        and evento.total_perda_efetiva == 0
        and evento.total_provisao == 0
        and evento.total_recuperado == 0
    )


def validar_campos_contabeis_quando_ha_movimento(
    evento: EventoAgrupado,
) -> list[Ocorrencia]:
    """DRO001451: lancamentos que nao sejam exclusivamente de risco tem
    que ter informacoes relativas as contas contabeis correspondentes
    (planilha oficial). Duas checagens:

    1. Rede de seguranca de consistencia interna: como calcular_totais so
       soma valores vindos de contabilizacoes ja validadas por
       BASE-CONT-OBR-001, um total nao-zero sem nenhuma contabilizacao
       seria uma inconsistencia interna do proprio programa, nao dos
       dados.
    2. A checagem real da critica oficial: cada contabilizacao com
       movimento (perda, provisao ou recuperacao diferente de zero) deve
       ter os dois pares de conta completos -- debito (Balancete +
       COSIF) e credito (Balancete + COSIF), nao apenas uma das quatro
       isoladamente. Confirmado no XML de exemplo oficial
       ("DRO - Modelo XML do Documento 5050 - Exemplo.xml"): as tres
       contabilizacoes do exemplo sempre preenchem as 4 contas juntas,
       nunca so um lado -- consistente com partida dobrada (todo
       lancamento tem debito e credito). O XSD aceita as 4 contas como
       opcionais (nao pega isso), entao a responsabilidade e local."""

    if evento.total_perda_efetiva is None:
        return []

    ocorrencias: list[Ocorrencia] = []

    tem_movimento_evento = (
        evento.total_perda_efetiva != 0
        or evento.total_provisao != 0
        or evento.total_recuperado != 0
    )
    if tem_movimento_evento and not evento.contabilizacoes:
        ocorrencias.append(
            _erro(
                evento,
                "DRO001451",
                (
                    "Evento não exclusivamente de risco exige campos "
                    "contábeis."
                ),
                "Há totais de perda/provisão/recuperação sem contabilização registrada.",
                ("valorPerdaEfetiva", "valorProvisao", "valorRecuperacao"),
            )
        )

    for contabilizacao in evento.contabilizacoes:
        tem_movimento_lancamento = (
            contabilizacao.valor_perda_efetiva != 0
            or contabilizacao.valor_provisao != 0
            or contabilizacao.valor_recuperacao != 0
        )
        if not tem_movimento_lancamento:
            continue
        par_debito_completo = (
            contabilizacao.conta_debito is not None
            and contabilizacao.conta_cosif_debito is not None
        )
        par_credito_completo = (
            contabilizacao.conta_credito is not None
            and contabilizacao.conta_cosif_credito is not None
        )
        if not (par_debito_completo and par_credito_completo):
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_PRE_PROCESSAMENTO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="DRO001451",
                    descricao=(
                        "Contabilização com movimento sem os pares "
                        "completos de conta contábil."
                    ),
                    detalhe=(
                        f"valorPerdaEfetiva={contabilizacao.valor_perda_efetiva:.2f}, "
                        f"valorProvisao={contabilizacao.valor_provisao:.2f}, "
                        f"valorRecuperacao={contabilizacao.valor_recuperacao:.2f} "
                        "exige contaBalAnaliticoDebito+contaCosifDebito e "
                        "contaBalAnaliticoCredito+contaCosifCredito "
                        "completos."
                    ),
                    linhas=(contabilizacao.numero_linha,),
                    id_evento=evento.id_evento,
                    campos=(
                        "contaBalAnaliticoDebito",
                        "contaBalAnaliticoCredito",
                        "contaCosifDebito",
                        "contaCosifCredito",
                    ),
                )
            )

    return ocorrencias


def validar_evento_apenas_risco(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO001452: evento EXCLUSIVAMENTE de risco nao deve ter
    contabilizacao."""

    if not _evento_apenas_risco(evento):
        return None
    if evento.contabilizacoes:
        return _erro(
            evento,
            "DRO001452",
            (
                "Evento exclusivamente de risco não deve ter "
                "contabilização."
            ),
            (
                f"soma(valorRisco)={_soma_risco(evento):.2f} com "
                f"{len(evento.contabilizacoes)} contabilização(ões) "
                "registrada(s)."
            ),
            ("valorRisco",),
        )
    return None


# ---------------------------------------------------------------------------
# Secao 16 - individualizacao e consolidacao
# ---------------------------------------------------------------------------


def classificar_evento(evento: EventoAgrupado) -> bool:
    """True quando o evento deve ser individualizado (secao 16).

    Cobre a critica oficial DRO001231: o limiar de R$ 1.000,00 e o risco nao
    coberto de R$ 10.000.000,00 sao os dois criterios de individualizacao;
    nao ha uma condicao de reprovacao separada da propria classificacao."""

    if not evento.consistente or evento.total_perda_efetiva is None:
        return False

    limiar_atingido = (
        evento.total_perda_efetiva + evento.total_provisao
        >= LIMIAR_INDIVIDUALIZACAO
    )
    risco_nao_coberto = _soma_risco(evento) >= LIMIAR_RISCO_NAO_COBERTO
    return limiar_atingido or risco_nao_coberto


# ---------------------------------------------------------------------------
# Orquestracao
# ---------------------------------------------------------------------------

REGRAS_UM_RESULTADO = (
    validar_ordem_datas,
    validar_descoberta_obrigatoria,
    validar_categoria_nivel2_obrigatoria,
    validar_risco_associado_obrigatorio,
    validar_ligado_risco_socioambiental_obrigatorio,
    validar_ligado_risco_cibernetico_obrigatorio,
    validar_natureza_contingencia_avaliacao,
    validar_limite_recuperacao,
    validar_natureza_para_risco,
    validar_descricao_materialidade,
    validar_provisao_avaliacao_im,
    validar_composicao_risco_total,
    validar_probabilidade_obrigatoria_individual,
    validar_probabilidade_proibida_massificada,
    validar_soma_risco_positiva,
    validar_evento_apenas_risco,
)

REGRAS_VARIOS_RESULTADOS = (
    validar_cosif_obrigatorio,
    validar_campos_contabeis_quando_ha_movimento,
    validar_conta_cosif_debito,
    validar_conta_cosif_credito,
)


def validar_evento(evento: EventoAgrupado) -> list[Ocorrencia]:
    """Roda as criticas oficiais de pre-processamento aplicaveis a 1 evento
    que so precisam do proprio evento (exclui DRO001101/DRO001102/
    DRO001103, verificadas uma vez para o documento inteiro em
    validar_unicidade_do_documento; exclui tambem DRO001321, DRO001401 e
    DRO001402, que precisam dos blocos globais de sistemas/contas e sao
    chamadas explicitamente por conversion.py)."""

    ocorrencias: list[Ocorrencia] = []
    for regra in REGRAS_UM_RESULTADO:
        resultado = regra(evento)
        if resultado is not None:
            ocorrencias.append(resultado)
    for regra in REGRAS_VARIOS_RESULTADOS:
        ocorrencias.extend(regra(evento))
    return ocorrencias


def validar_formatos_e_dominios_evento(
    evento: EventoAgrupado,
) -> list[Ocorrencia]:
    """Formato/tamanho/dominio dos campos constantes no evento, espelhando
    facetas do XSD 06/2025 que hoje so seriam pegas tarde, na validacao
    contra o XSD (etapa 22). Cada campo e checado so quando ja passou do
    estado ausente/invalido, para nao duplicar BASE-OBR-001/BASE-NULO-001.
    Chamada por conversion.py antes de validar_evento/validar_evento_pos/
    referencias/consolidacao, que sao suprimidas quando esta funcao
    encontra qualquer problema."""

    ocorrencias: list[Ocorrencia] = []

    def _campo(nome: str) -> tuple[bool, object]:
        campo = evento.linhas[0].campos.get(nome)
        if campo is None or campo.ausente or campo.invalido:
            return False, None
        return True, campo.valor

    ok, valor = _campo("idEvento")
    if ok and not _PADRAO_ID_EVENTO.fullmatch(str(valor)):
        ocorrencias.append(_erro(
            evento, "BASE-IDEVENTO-FORM-001",
            "idEvento deve ser alfanumérico, de 1 a 40 caracteres.",
            f"idEvento={valor!r} (após remoção de hífen).", ("idEvento",),
        ))

    ok, valor = _campo("categoriaNivel1")
    if ok and not _PADRAO_CATEGORIA_NIVEL1.fullmatch(str(valor)):
        ocorrencias.append(_erro(
            evento, "BASE-CATEGORIA1-FORM-001",
            "categoriaNivel1 deve ser um dígito de 1 a 8.",
            f"categoriaNivel1={valor!r}.", ("categoriaNivel1",),
        ))

    ok, valor = _campo("categoriaNivel2")
    if ok and not _PADRAO_CATEGORIA_NIVEL2.fullmatch(str(valor)):
        ocorrencias.append(_erro(
            evento, "BASE-CATEGORIA2-FORM-001",
            "categoriaNivel2 não está na lista oficial de códigos.",
            f"categoriaNivel2={valor!r}.", ("categoriaNivel2",),
        ))

    ok, valor = _campo("tipoAvaliacao")
    if ok and str(valor) not in TIPOS_AVALIACAO_VALIDOS:
        ocorrencias.append(_erro(
            evento, "BASE-AVALIACAO-FORM-001",
            "tipoAvaliacao deve ser I, M ou NA.",
            f"tipoAvaliacao={valor!r}.", ("tipoAvaliacao",),
        ))

    ok, valor = _campo("unidadeNegocio")
    if ok and not _PADRAO_UNIDADE_NEGOCIO.fullmatch(str(valor)):
        ocorrencias.append(_erro(
            evento, "BASE-UNIDADE-FORM-001",
            "unidadeNegocio deve ser um dígito de 1 a 8.",
            f"unidadeNegocio={valor!r}.", ("unidadeNegocio",),
        ))

    ok, valor = _campo("naturezaContingencia")
    if ok and str(valor) not in NATUREZAS_CONTINGENCIA_VALIDAS:
        ocorrencias.append(_erro(
            evento, "BASE-NATUREZA-FORM-001",
            "naturezaContingencia deve ser TRI, TRA, CIV ou NA.",
            f"naturezaContingencia={valor!r}.", ("naturezaContingencia",),
        ))

    ok, valor = _campo("codigoEventoOrigem")
    if ok and not _PADRAO_CODIGO_EVENTO_ORIGEM.fullmatch(str(valor)):
        ocorrencias.append(_erro(
            evento, "BASE-EVENTOORIGEM-FORM-001",
            "codigoEventoOrigem deve ser alfanumérico, de 1 a 73 caracteres.",
            f"codigoEventoOrigem={valor!r}.", ("codigoEventoOrigem",),
        ))

    ok, valor = _campo("descricaoEvento")
    if ok:
        colapsado = colapsar_espacos_para_validacao(str(valor))
        if len(colapsado) > LIMITE_DESCRICAO_EVENTO:
            ocorrencias.append(_erro(
                evento, "BASE-DESCRICAO-FORM-001",
                f"descricaoEvento excede {LIMITE_DESCRICAO_EVENTO} caracteres.",
                f"descricaoEvento tem {len(colapsado)} caracteres após "
                "colapsar espaços.",
                ("descricaoEvento",),
            ))

    ok, valor = _campo("idBacen")
    if ok and not _PADRAO_ID_BACEN.fullmatch(str(valor)):
        ocorrencias.append(_erro(
            evento, "BASE-IDBACEN-FORM-001",
            'idBacen deve ser "Z" + 7 dígitos ou "I" + 5 dígitos.',
            f"idBacen={valor!r}.", ("idBacen",),
        ))

    ok, valor = _campo("riscoAssociado")
    if ok and str(valor) not in RISCOS_ASSOCIADOS_VALIDOS:
        ocorrencias.append(_erro(
            evento, "BASE-RISCOASSOCIADO-FORM-001",
            "riscoAssociado deve ser C, M ou NA.",
            f"riscoAssociado={valor!r}.", ("riscoAssociado",),
        ))

    ok, valor = _campo("ligadoRiscoSocioAmbiental")
    if ok and str(valor) not in OPCOES_SIM_NAO:
        ocorrencias.append(_erro(
            evento, "BASE-SOCIOAMBIENTAL-FORM-001",
            "ligadoRiscoSocioAmbiental deve ser S ou N.",
            f"ligadoRiscoSocioAmbiental={valor!r}.",
            ("ligadoRiscoSocioAmbiental",),
        ))

    ok, valor = _campo("ligadoRiscoCibernetico")
    if ok and str(valor) not in OPCOES_SIM_NAO:
        ocorrencias.append(_erro(
            evento, "BASE-CIBERNETICO-FORM-001",
            "ligadoRiscoCibernetico deve ser S ou N.",
            f"ligadoRiscoCibernetico={valor!r}.", ("ligadoRiscoCibernetico",),
        ))

    ok, valor = _campo("negocioDescontinuado")
    if ok and str(valor) not in OPCOES_SIM_NAO:
        ocorrencias.append(_erro(
            evento, "BASE-NEGOCIO-FORM-001",
            "negocioDescontinuado deve ser S ou N.",
            f"negocioDescontinuado={valor!r}.", ("negocioDescontinuado",),
        ))

    return ocorrencias


def validar_unicidade_do_documento(
    eventos: dict[str, EventoAgrupado],
) -> list[Ocorrencia]:
    """DRO001101/DRO001102/DRO001103.

    Garantidas por construcao neste projeto: os eventos sao agrupados por
    idEvento em um dict (calculations.agrupar_linhas_por_evento), que nao
    pode ter chaves duplicadas; sistemas e contas sao deduplicados por
    codigo em calculations.validar_sistemas_e_contas. Nao ha condicao de
    dado que viole essas tres criticas neste desenho de dados."""

    del eventos  # Mantido no assinatura para deixar a critica documentada.
    return []


# ---------------------------------------------------------------------------
# Cabecalho (secao 7)
# ---------------------------------------------------------------------------

CODIGO_DOCUMENTO_5050 = "5050"
_PADRAO_CONGLOMERADO = re.compile(r"^C[0-9]{7}$")
TIPOS_REMESSA_VALIDOS = frozenset({"I", "S"})
OPCOES_PROVISAO_ACUMULADA_VALIDAS = frozenset({"S", "N"})


def _erro_cabecalho(
    codigo: str, descricao: str, detalhe: str, campos: tuple[str, ...]
) -> Ocorrencia:
    return Ocorrencia(
        etapa=ETAPA_PRE_PROCESSAMENTO,
        tipo=TIPO_ERRO_IMPEDITIVO,
        codigo=codigo,
        descricao=descricao,
        detalhe=detalhe,
        campos=campos,
    )


def validar_cabecalho(
    cabecalho: dict[str, CampoNormalizado],
) -> list[Ocorrencia]:
    """Validacoes de negocio do Cabecalho (secao 7), confirmadas contra
    assets/schemas/dro_5050_2025_06.xsd. Cada campo e checado em ordem de
    estado (ausente -> invalido -> dominio) antes de qualquer regex de
    dominio, para nao chamar regex com None, nao gerar mais de uma
    ocorrencia para o mesmo problema, e preservar o motivo especifico ja
    produzido pelo normalizador quando o campo ja veio INVALIDO."""

    ocorrencias: list[Ocorrencia] = []

    campo = cabecalho["codigoDocumento"]
    if campo.ausente:
        ocorrencias.append(
            _erro_cabecalho(
                "BASE-CAB-CODDOC-001",
                "codigoDocumento obrigatório.",
                "codigoDocumento ausente.",
                ("codigoDocumento",),
            )
        )
    elif campo.invalido:
        ocorrencias.append(
            _erro_cabecalho(
                "BASE-CAB-CODDOC-001",
                "codigoDocumento inválido.",
                campo.motivo or "codigoDocumento inválido.",
                ("codigoDocumento",),
            )
        )
    elif str(campo.valor) != CODIGO_DOCUMENTO_5050:
        ocorrencias.append(
            _erro_cabecalho(
                "BASE-CAB-CODDOC-001",
                'codigoDocumento deve ser "5050".',
                f"codigoDocumento={campo.valor!r}.",
                ("codigoDocumento",),
            )
        )

    campo = cabecalho["dataBase"]
    if campo.ausente:
        ocorrencias.append(
            _erro_cabecalho(
                "BASE-CAB-DATABASE-001",
                "dataBase obrigatória.",
                "dataBase ausente.",
                ("dataBase",),
            )
        )
    elif campo.invalido:
        ocorrencias.append(
            _erro_cabecalho(
                "BASE-CAB-DATABASE-001",
                "dataBase inválida.",
                campo.motivo or "dataBase inválida.",
                ("dataBase",),
            )
        )

    campo = cabecalho["codigoConglomerado"]
    if campo.ausente:
        ocorrencias.append(
            _erro_cabecalho(
                "BASE-CAB-CONGLOMERADO-001",
                "codigoConglomerado obrigatório.",
                "codigoConglomerado ausente.",
                ("codigoConglomerado",),
            )
        )
    elif campo.invalido:
        ocorrencias.append(
            _erro_cabecalho(
                "BASE-CAB-CONGLOMERADO-001",
                "codigoConglomerado inválido.",
                campo.motivo or "codigoConglomerado inválido.",
                ("codigoConglomerado",),
            )
        )
    elif not _PADRAO_CONGLOMERADO.fullmatch(str(campo.valor)):
        ocorrencias.append(
            _erro_cabecalho(
                "BASE-CAB-CONGLOMERADO-001",
                'codigoConglomerado deve ser "C" seguido de 7 dígitos.',
                f"codigoConglomerado={campo.valor!r}.",
                ("codigoConglomerado",),
            )
        )

    campo = cabecalho["cnpj"]
    if campo.ausente:
        ocorrencias.append(
            _erro_cabecalho(
                "BASE-CAB-CNPJ-001",
                "cnpj obrigatório.",
                "cnpj ausente.",
                ("cnpj",),
            )
        )
    elif campo.invalido:
        ocorrencias.append(
            _erro_cabecalho(
                "BASE-CAB-CNPJ-001",
                "cnpj inválido.",
                campo.motivo or "cnpj inválido.",
                ("cnpj",),
            )
        )

    campo = cabecalho["tipoRemessa"]
    if campo.ausente:
        ocorrencias.append(
            _erro_cabecalho(
                "BASE-CAB-REMESSA-001",
                "tipoRemessa obrigatório.",
                "tipoRemessa ausente.",
                ("tipoRemessa",),
            )
        )
    elif campo.invalido:
        ocorrencias.append(
            _erro_cabecalho(
                "BASE-CAB-REMESSA-001",
                "tipoRemessa inválido.",
                campo.motivo or "tipoRemessa inválido.",
                ("tipoRemessa",),
            )
        )
    elif campo.valor not in TIPOS_REMESSA_VALIDOS:
        ocorrencias.append(
            _erro_cabecalho(
                "BASE-CAB-REMESSA-001",
                'tipoRemessa deve ser "I" ou "S".',
                f"tipoRemessa={campo.valor!r}.",
                ("tipoRemessa",),
            )
        )

    campo = cabecalho["opcaoPorProvisaoAcumulada"]
    if campo.ausente:
        ocorrencias.append(
            _erro_cabecalho(
                "BASE-CAB-PROVACUM-001",
                "opcaoPorProvisaoAcumulada obrigatória.",
                "opcaoPorProvisaoAcumulada ausente.",
                ("opcaoPorProvisaoAcumulada",),
            )
        )
    elif campo.invalido:
        ocorrencias.append(
            _erro_cabecalho(
                "BASE-CAB-PROVACUM-001",
                "opcaoPorProvisaoAcumulada inválida.",
                campo.motivo or "opcaoPorProvisaoAcumulada inválida.",
                ("opcaoPorProvisaoAcumulada",),
            )
        )
    elif campo.valor not in OPCOES_PROVISAO_ACUMULADA_VALIDAS:
        ocorrencias.append(
            _erro_cabecalho(
                "BASE-CAB-PROVACUM-001",
                'opcaoPorProvisaoAcumulada deve ser "S" ou "N".',
                f"opcaoPorProvisaoAcumulada={campo.valor!r}.",
                ("opcaoPorProvisaoAcumulada",),
            )
        )

    return ocorrencias


def validar_codigo_conglomerado_unicad(
    cabecalho: dict[str, CampoNormalizado],
) -> Ocorrencia | None:
    """DRO001001: verifica se o codigo do conglomerado prudencial informado
    existe no cadastro local do UNICAD
    (src.regulatory_constants.CODIGOS_CONGLOMERADOS_VALIDOS).

    So executa quando codigoConglomerado ja passou pelas checagens de
    ausencia/invalidez/formato em validar_cabecalho, para nao duplicar ou
    mascarar o motivo ja reportado por BASE-CAB-CONGLOMERADO-001."""

    campo = cabecalho["codigoConglomerado"]
    if campo.ausente or campo.invalido:
        return None
    valor = str(campo.valor)
    if not _PADRAO_CONGLOMERADO.fullmatch(valor):
        return None
    if valor in CODIGOS_CONGLOMERADOS_VALIDOS:
        return None
    return _erro_cabecalho(
        "DRO001001",
        "Código do conglomerado prudencial não encontrado no cadastro UNICAD.",
        f"codigoConglomerado={valor!r} não encontrado no cadastro local do UNICAD.",
        ("codigoConglomerado",),
    )


def cabecalho_tem_data_base_valida(
    cabecalho: dict[str, CampoNormalizado],
) -> bool:
    """Usado por conversion.py para decidir se as etapas dependentes de
    semestre (P3/consolidacao) podem rodar."""

    return cabecalho["dataBase"].valido
