"""Criticas oficiais de pre-processamento do DRO 5050.

Quando este modulo produz uma Ocorrencia, seu codigo pertence exclusivamente
a familia DRO001*. Regras locais BASE-* ficam concentradas em rules_local.py.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from src.builders import COLUNAS_CONTABILIZACAO
from src.models import (
    CampoNormalizado,
    Contabilizacao,
    ETAPA_PRE_PROCESSAMENTO,
    EventoAgrupado,
    LinhaNormalizada,
    Ocorrencia,
    TIPO_ERRO_IMPEDITIVO,
)
from src.regulatory_constants import (
    CODIGOS_CONGLOMERADOS_VALIDOS,
    CONTAS_COSIF_VALIDAS,
    DATA_INICIO_2021,
)

LIMIAR_MATERIALIDADE = Decimal("1000000.00")

NATUREZAS_CONTINGENCIA = frozenset({"TRI", "TRA", "CIV", "OUT"})


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
            (
                "Verifica, quando informado, se a data de ocorrência é "
                "menor ou igual a data de descoberta."
            ),
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
            (
                "Verifica se o campo dataDescoberta foi devidamente "
                "informado para datas de ocorrência maiores ou iguais a "
                "1.1.2021."
            ),
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
            (
                "Verifica a obrigatoriedade de preenchimento da "
                "categoriaNivel2 para eventos cuja data de ocorrência "
                "forem maiores ou iguais a 1.1.2021 ."
            ),
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
            (
                "Verifica, quando a data de ocorrência for maior ou igual "
                "a 1.1.2021, se o campo riscoAssociado foi devidamente "
                "preenchido."
            ),
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
                "Verifica, quando a data de ocorrência for maior ou igual "
                "a 1.1.2021, se o campo ligadoRiscoSocioAmbiental foi "
                "devidamente preenchido."
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
                "Verifica, quando a data de ocorrência for maior ou igual "
                "a 1.1.2021, se o campo ligadoRIscoCibernetico foi "
                "devidamente preenchido."
            ),
            f"dataOcorrencia={ocorrencia_data}, campo ausente.",
            ("ligadoRiscoCibernetico",),
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
                "Verifica se o total recuperado (totalRecuperado ) é "
                "menor ou igual ao somatório, em valores absolutos, dos "
                "campos totalPerdaEfetiva e totalProvisao ."
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
                "Verifica, quando o campo valorTotalRisco é informado, se "
                "há informação a respeito da natureza de contingência "
                "(tributária, trabalhista e/ou cívil) ."
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
            (
                "Verifica, quando a data de ocorrência for maior ou igual "
                "a 1.1.2021 e para eventos cujo somatório do campo "
                "totalPerda Efetiva com o campo valorTotalRisco for maior "
                "ou igual a R$ 1 milhão, se o campo descricaoEvento foi "
                "devidamente preenchido ."
            ),
            f"valorMaterialidade={materialidade:.2f} >= 1.000.000,00.",
            ("descricaoEvento",),
        )
    return None


def _linhas_com_contabilizacao_iniciada(
    evento: EventoAgrupado,
) -> tuple[LinhaNormalizada, ...]:
    """Uma linha 'iniciou' contabilizacao quando qualquer campo de
    COLUNAS_CONTABILIZACAO deixou de estar ausente -- inclui campos
    invalidos (ex. valorProvisao com texto malformado). Um campo invalido
    e reportado pela etapa de normalizacao (BASE-NULO-001, via
    detectar_ausencia_e_invalidez), mas isso nao cria um objeto
    Contabilizacao em extrair_contabilizacoes -- so o campo *ausente* e
    checado ali (BASE-CONT-OBR-001), nao o *invalido* isolado."""

    return tuple(
        linha
        for linha in evento.linhas
        if any(not linha.campos[nome].ausente for nome in COLUNAS_CONTABILIZACAO)
    )


def validar_provisao_avaliacao_im(evento: EventoAgrupado) -> Ocorrencia | None:
    """DRO001302: avaliação I ou M exige tratamento coerente da provisão.

    Nao usa `evento.contabilizacoes` (lista ja filtrada por extrair_
    contabilizacoes) como evidencia de provisao informada: uma linha pode
    ter valorProvisao correto e ainda assim ser descartada por outro campo
    obrigatorio ausente (ex. dataContabilizacao), o que geraria falso
    positivo aqui. A decisao e tomada direto sobre as linhas normalizadas
    do evento (`_linhas_com_contabilizacao_iniciada`). Chamada
    separadamente por conversion.py, antes do curto-circuito de formato
    (ver validar_evento)."""

    avaliacao = evento.valor_evento("tipoAvaliacao")
    if avaliacao not in ("I", "M"):
        return None

    linhas_contabeis = _linhas_com_contabilizacao_iniciada(evento)

    if not linhas_contabeis:
        if _evento_apenas_risco(evento):
            return None
        return _erro(
            evento,
            "DRO001302",
            (
                'Verifica, caso tipoAvaliacao seja igual a "I" ou "M", se '
                "valores para totalProvisao e/ou valorProvisao foram "
                "devidamente informados."
            ),
            "Nenhuma contabilização ou provisão foi informada no evento.",
            ("tipoAvaliacao", "valorProvisao"),
        )

    linhas_com_provisao_incorreta = tuple(
        linha.numero_linha
        for linha in linhas_contabeis
        if linha.campos["valorProvisao"].ausente
        or linha.campos["valorProvisao"].invalido
    )
    if not linhas_com_provisao_incorreta:
        return None

    return Ocorrencia(
        etapa=ETAPA_PRE_PROCESSAMENTO,
        tipo=TIPO_ERRO_IMPEDITIVO,
        codigo="DRO001302",
        descricao=(
            'Verifica, caso tipoAvaliacao seja igual a "I" ou "M", se '
            "valores para totalProvisao e/ou valorProvisao foram "
            "devidamente informados."
        ),
        detalhe=(
            "Existe contabilização iniciada com valorProvisao ausente "
            "ou inválido."
        ),
        linhas=linhas_com_provisao_incorreta,
        id_evento=evento.id_evento,
        campos=("tipoAvaliacao", "valorProvisao"),
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
            (
                "Verifica se o campo valorTotalRisco , quando informado "
                "para um dado idEvento , corresponde ao somatório do "
                "campo totalProvisao com todos os lançamento informados "
                "nos campos valorRisco ."
            ),
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
            (
                "Verifica, quando a data de ocorrência for maior ou igual "
                'a 1.1.2021 e tipoAvaliacao igual a "I" (individual), se '
                "o campo probabilidadePerda foi devidamente preenchido."
            ),
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
            (
                'Verifica, quando o tipoAvaliacao for igual a "M" '
                "(massificada), a inexistência de informação no campo "
                "probabilidade de perda (probabilidadePerda ). Conforme "
                "definido, não deve ser informada probabilidade de perda "
                "para eventos com tipo de avaliação massificada."
            ),
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
            (
                "Verifica se a soma dos campos valorRisco apresenta "
                "resultado maior que zero para o seguinte contexto: a) a "
                "data de ocorrência é maior ou igual a 1.1.2021; b) o "
                'tipoAvaliacao é igual a "I" (Individualizada); c) a '
                'naturezaContingencia é diferente de "NA"; e d) foi '
                "informada probabilidadePerda ."
            ),
            f"soma(valorRisco)={_soma_risco(evento):.2f}.",
            ("valorRisco",),
        )
    return None


# ---------------------------------------------------------------------------
# Secao 13 - referencias de sistemas e contas. A coerencia global e local;
# aqui as criticas oficiais verificam as referencias feitas pelo evento.
# ---------------------------------------------------------------------------


def validar_sistema_referenciado(
    evento: EventoAgrupado, sistemas_globais: dict[str, str]
) -> Ocorrencia | None:
    """DRO001321: codSistemaOrigem informado deve existir no Bloco 3
    (bloco global de sistemas, builders.construir_mapa_sistemas) --
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
            (
                "Verifica se o código preenchido para identificação do "
                "sistema origem (codigoSistemaOrigem ) está devidamente "
                "informado no Bloco 3 - Tabela de Sistemas de Origem."
            ),
            f"codSistemaOrigem={codigo!r} não encontrado no bloco de sistemas.",
            ("codSistemaOrigem",),
        )
    return None


def validar_contas_referenciadas(
    evento: EventoAgrupado, contas_globais: dict[str, str]
) -> list[Ocorrencia]:
    """DRO001401/DRO001402: a conta interna referenciada em cada
    contabilizacao deve existir no bloco global de contas (Bloco 4,
    builders.construir_mapa_contas) -- nao precisa ter o nome
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
                    (
                        "Verifica, nos casos em que o campo "
                        "contaBalAnaliticoDebito é informado, se a "
                        "referida conta está devidamente informada no "
                        "campo codigoConta do Bloco 4 - Tabela de "
                        "Subtítulos de Nível Interno"
                    ),
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
                    (
                        "Verifica, nos casos em que o campo "
                        "contaBalAnaliticoCredito é informado, se a "
                        "referida conta está devidamente informada no "
                        "campo codigoConta do Bloco 4 - Tabela de "
                        "Subtítulos de Nível Interno"
                    ),
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
                    (
                        "Verifica, nos casos em que o campo "
                        "contaBalAnaliticoDebito é informado, se há "
                        "informação preenchida no campo contaCosifDebito "
                        "correspondente ."
                    ),
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
                    (
                        "Verifica, nos casos em que o campo "
                        "contaBalAnaliticoCredito é informado, se há "
                        "informação preenchida no campo contaCosifCredito "
                        "correspondente ."
                    ),
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
                    (
                        "Verifica, nos casos em que sejam devidos "
                        "lançamentos no campo contaCosifDebito , se foi "
                        "informada uma conta Cosif válida"
                    ),
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
                    (
                        "Verifica, nos casos em que sejam devidos "
                        "lançamentos no campo contaCosifCredito , se foi "
                        "informada uma conta Cosif válida."
                    ),
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
       ter ao menos um par correspondente completo (Balancete + COSIF).
       DRO001441 a DRO001444 continuam responsaveis por pares assimetricos.
       Nao se presume, apenas pelo XML de exemplo, que debito e credito
       sejam simultaneamente obrigatorios em todo tipo de movimento."""

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
                    "Verifica, para os casos que não se referem apenas a "
                    "lançamentos de risco, se foram devidamente "
                    "preenchidos os respectivos campos contábeis. "
                    "Lançamentos que não sejam exclusivamente de risco "
                    "têm que ter informações relativas às contas "
                    "contábeis correspondentes."
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
        if not (par_debito_completo or par_credito_completo):
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_PRE_PROCESSAMENTO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="DRO001451",
                    descricao=(
                        "Verifica, para os casos que não se referem "
                        "apenas a lançamentos de risco, se foram "
                        "devidamente preenchidos os respectivos campos "
                        "contábeis. Lançamentos que não sejam "
                        "exclusivamente de risco têm que ter informações "
                        "relativas às contas contábeis correspondentes."
                    ),
                    detalhe=(
                        f"valorPerdaEfetiva={contabilizacao.valor_perda_efetiva:.2f}, "
                        f"valorProvisao={contabilizacao.valor_provisao:.2f}, "
                        f"valorRecuperacao={contabilizacao.valor_recuperacao:.2f} "
                        "exige ao menos um par correspondente completo: "
                        "contaBalAnaliticoDebito+contaCosifDebito ou "
                        "contaBalAnaliticoCredito+contaCosifCredito."
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
    """DRO001452: evento exclusivamente de risco nao aceita bloco contabil."""

    if not _evento_apenas_risco(evento):
        return None
    linhas_com_dados_contabeis = tuple(
        linha
        for linha in evento.linhas
        if any(
            not linha.campos[nome].ausente
            for nome in COLUNAS_CONTABILIZACAO
        )
    )
    if not linhas_com_dados_contabeis:
        return None
    return Ocorrencia(
        etapa=ETAPA_PRE_PROCESSAMENTO,
        tipo=TIPO_ERRO_IMPEDITIVO,
        codigo="DRO001452",
        descricao=(
            "Verifica a inexist\u00eancia de informa\u00e7\u00e3o nos campos de "
            "informa\u00e7\u00f5es cont\u00e1beis, por indevida, nos casos de um "
            "idEvento que contenha lan\u00e7amentos relativos apenas a "
            "risco. Ou seja, n\u00e3o \u00e9 devida a informa\u00e7\u00e3o de conta "
            "cont\u00e1bil nos casos de um contexto de informa\u00e7\u00f5es "
            'exclusivas a valores em risco. O bloco XML "contabilizacao" '
            "n\u00e3o deve ser informado."
        ),
        detalhe=(
            f"soma(valorRisco)={_soma_risco(evento):.2f} com "
            f"{len(linhas_com_dados_contabeis)} linha(s) contendo "
            "informacao contabil."
        ),
        linhas=tuple(linha.numero_linha for linha in linhas_com_dados_contabeis),
        id_evento=evento.id_evento,
        campos=("valorRisco", *COLUNAS_CONTABILIZACAO),
    )


# ---------------------------------------------------------------------------
# Secao 16 - individualizacao e consolidacao
# ---------------------------------------------------------------------------


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
    validar_limite_recuperacao,
    validar_natureza_para_risco,
    validar_descricao_materialidade,
    validar_composicao_risco_total,
    validar_probabilidade_obrigatoria_individual,
    validar_probabilidade_proibida_massificada,
    validar_soma_risco_positiva,
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
    chamadas explicitamente por conversion.py).

    DRO001302 e DRO001452 sao executadas separadamente por conversion.py,
    antes do bloqueio local, porque precisam analisar diretamente as linhas
    normalizadas originais do evento."""

    ocorrencias: list[Ocorrencia] = []
    for regra in REGRAS_UM_RESULTADO:
        resultado = regra(evento)
        if resultado is not None:
            ocorrencias.append(resultado)
    for regra in REGRAS_VARIOS_RESULTADOS:
        ocorrencias.extend(regra(evento))
    return ocorrencias


def validar_unicidade_do_documento(
    eventos: dict[str, EventoAgrupado],
) -> list[Ocorrencia]:
    """DRO001101/DRO001102/DRO001103.

    Garantidas por construcao neste projeto: os eventos sao agrupados por
    idEvento em um dict (builders.agrupar_linhas_por_evento), que nao
    pode ter chaves duplicadas; sistemas e contas sao deduplicados por codigo pelos builders de mapas. Nao ha condicao de
    dado que viole essas tres criticas neste desenho de dados."""

    del eventos  # Mantido no assinatura para deixar a critica documentada.
    return []


# ---------------------------------------------------------------------------
# Cabecalho (secao 7)
# ---------------------------------------------------------------------------

_PADRAO_CONGLOMERADO = re.compile(r"^C[0-9]{7}$")


def _erro_cabecalho(
    codigo: str, descricao: str, detalhe: str, campos: tuple[str, ...]
) -> Ocorrencia:
    """Constroi uma ocorrencia oficial de pre-processamento do cabecalho."""
    return Ocorrencia(
        etapa=ETAPA_PRE_PROCESSAMENTO,
        tipo=TIPO_ERRO_IMPEDITIVO,
        codigo=codigo,
        descricao=descricao,
        detalhe=detalhe,
        campos=campos,
    )


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
        "Verifica se o código do conglomerado prudencial existe no Unicad.",
        f"codigoConglomerado={valor!r} não encontrado no cadastro local do UNICAD.",
        ("codigoConglomerado",),
    )

# Criticas oficiais extraidas da antiga montagem de eventos.
def validar_provisao_avaliacao_na(
    evento: EventoAgrupado,
) -> list[Ocorrencia]:
    """DRO001301: tipoAvaliacao=NA nao aceita provisao diferente de zero."""

    if evento.valor_evento("tipoAvaliacao") != "NA":
        return []

    ocorrencias: list[Ocorrencia] = []
    for linha in evento.linhas:
        campo_provisao = linha.campos["valorProvisao"]
        if not campo_provisao.valido or campo_provisao.valor == 0:
            continue
        ocorrencias.append(
            Ocorrencia(
                etapa=ETAPA_PRE_PROCESSAMENTO,
                tipo=TIPO_ERRO_IMPEDITIVO,
                codigo="DRO001301",
                descricao=(
                    'Para tipoAvalia\u00e7\u00e3o igual a "NA", valores de '
                    "provis\u00e3o (valorProvisao) n\u00e3o devem ser informados."
                ),
                detalhe=(
                    f"valorProvisao={campo_provisao.valor:.2f} "
                    "com tipoAvaliacao=NA."
                ),
                linhas=(linha.numero_linha,),
                id_evento=evento.id_evento,
                campos=("tipoAvaliacao", "valorProvisao"),
            )
        )
    return ocorrencias


def validar_contabilizacao_pre(
    id_evento: str,
    contabilizacao: Contabilizacao,
    data_ocorrencia: object | None,
) -> list[Ocorrencia]:
    ocorrencias: list[Ocorrencia] = []
    linhas = (contabilizacao.numero_linha,)
    if contabilizacao.valor_recuperacao > 0:
        ocorrencias.append(
            Ocorrencia(
                etapa=ETAPA_PRE_PROCESSAMENTO,
                tipo=TIPO_ERRO_IMPEDITIVO,
                codigo="DRO001411",
                descricao=(
                    "Verifica se o valorRecuperacao \u00e9 menor ou igual a zero. "
                    "Por conven\u00e7\u00e3o, valores de recupera\u00e7\u00e3o devem ser "
                    "lan\u00e7ados com sinal negativo."
                ),
                detalhe=(
                    f"valorRecuperacao={contabilizacao.valor_recuperacao:.2f}."
                ),
                linhas=linhas,
                id_evento=id_evento,
                campos=("valorRecuperacao",),
            )
        )
    fonte = contabilizacao.fonte_recuperacao
    ocorrencia_valida_a_partir_de_2021 = (
        isinstance(data_ocorrencia, date)
        and data_ocorrencia >= DATA_INICIO_2021
    )
    if (
        ocorrencia_valida_a_partir_de_2021
        and contabilizacao.valor_recuperacao < 0
        and fonte not in ("S", "O")
    ):
        ocorrencias.append(
            Ocorrencia(
                etapa=ETAPA_PRE_PROCESSAMENTO,
                tipo=TIPO_ERRO_IMPEDITIVO,
                codigo="DRO001421",
                descricao=(
                    "Verifica, quando a data de ocorr\u00eancia for maior ou igual "
                    "a 1.1.2021, se o campo fonteRecuperacao foi devidamene "
                    "informado quando h\u00e1 lan\u00e7amento referente a valor "
                    "recuperado."
                ),
                detalhe=(
                    f"dataOcorrencia={data_ocorrencia}, "
                    f"valorRecuperacao={contabilizacao.valor_recuperacao:.2f}, "
                    f"fonteRecuperacao={fonte!r}."
                ),
                linhas=linhas,
                id_evento=id_evento,
                campos=("valorRecuperacao", "fonteRecuperacao"),
            )
        )
    return ocorrencias


def validar_referencias_linha_pre(
    linha: LinhaNormalizada,
) -> list[Ocorrencia]:
    ocorrencias: list[Ocorrencia] = []
    for campo_cosif, campo_conta in (
        ("contaCosifDebito", "contaBalAnaliticoDebito"),
        ("contaCosifCredito", "contaBalAnaliticoCredito"),
    ):
        valor_cosif = linha.valor(campo_cosif)
        if valor_cosif is None or linha.valor(campo_conta) is not None:
            continue
        if campo_conta == "contaBalAnaliticoDebito":
            codigo_regra = "DRO001443"
            descricao_regra = (
                "Verifica, nos casos em que sejam devidos lan\u00e7amentos no "
                "campo contaCosifDebito, se h\u00e1 preenchimento do campo "
                "contaBalAnaliticoDebito correspondente."
            )
        else:
            codigo_regra = "DRO001444"
            descricao_regra = (
                "Verifica, nos casos em que sejam devidos lan\u00e7amentos no "
                "campo contaCosifCredito , se h\u00e1 preenchimento do campo "
                "contaBalAnaliticoCredito correspondente."
            )
        ocorrencias.append(
            Ocorrencia(
                etapa=ETAPA_PRE_PROCESSAMENTO,
                tipo=TIPO_ERRO_IMPEDITIVO,
                codigo=codigo_regra,
                descricao=descricao_regra,
                detalhe=f"{campo_cosif}={valor_cosif!r} sem {campo_conta}.",
                linhas=(linha.numero_linha,),
                id_evento=linha.valor("idEvento"),
                campos=(campo_cosif, campo_conta),
            )
        )
    return ocorrencias
