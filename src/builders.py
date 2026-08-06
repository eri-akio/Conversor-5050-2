"""Construcao deterministica das estruturas intermediarias do conversor."""

from __future__ import annotations

from decimal import Decimal

from src.calculations import (
    calcular_intervalo_semestre,
    calcular_totais,
    classificar_evento,
)
from src.models import (
    Contabilizacao,
    EventoAgrupado,
    EventoConsolidado,
    LinhaNormalizada,
    Probabilidade,
)
from src.normalizers import (
    maiusculizar_campo,
    normalizar_codigo_rotulado,
    normalizar_data,
    normalizar_decimal,
    normalizar_removendo_caracteres,
    normalizar_texto,
)
from src.reader import ALIAS_CANONICO_POR_NOME_ANTIGO, BASE_COLUNAS

COLUNAS_DATA = ("dataDescoberta", "dataOcorrencia", "dataContabilizacao")
COLUNAS_DECIMAL = (
    "valorRisco", "valorPerdaEfetiva", "valorProvisao", "valorRecuperacao",
)
COLUNAS_CODIGO_ROTULADO = (
    "categoriaNivel1", "categoriaNivel2", "tipoAvaliacao",
    "naturezaContingencia", "idBacen", "probabilidadePerda",
)
COLUNAS_SEM_HIFEN = ("idEvento",)
COLUNAS_SEM_PONTO_E_HIFEN = (
    "contaBalAnaliticoDebito", "contaBalAnaliticoCredito",
    "contaCosifDebito", "contaCosifCredito",
)
COLUNAS_MAIUSCULAS = frozenset({
    "tipoAvaliacao", "naturezaContingencia", "riscoAssociado",
    "ligadoRiscoSocioAmbiental", "ligadoRiscoCibernetico",
    "negocioDescontinuado", "probabilidadePerda", "fonteRecuperacao",
})
CAMPOS_CONSTANTES_NO_EVENTO = (
    "categoriaNivel1", "categoriaNivel2", "tipoAvaliacao", "unidadeNegocio",
    "dataDescoberta", "dataOcorrencia", "naturezaContingencia",
    "codSistemaOrigem", "nomeSistema", "codigoEventoOrigem",
    "descricaoEvento", "riscoAssociado", "ligadoRiscoSocioAmbiental",
    "ligadoRiscoCibernetico", "negocioDescontinuado", "idBacen",
)
CODIGOS_PROBABILIDADE = frozenset({"PR", "PO", "RE"})
COLUNAS_CONTABILIZACAO = (
    "dataContabilizacao", "contaBalAnaliticoDebito", "nomeContaDebito",
    "contaBalAnaliticoCredito", "nomeContaCredito", "contaCosifDebito",
    "contaCosifCredito", "valorPerdaEfetiva", "valorProvisao",
    "valorRecuperacao", "fonteRecuperacao",
)
CAMPOS_CONTABILIZACAO_OBRIGATORIOS = (
    "dataContabilizacao", "valorPerdaEfetiva", "valorProvisao",
    "valorRecuperacao",
)

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


def identificar_campos_conflitantes(
    linhas: list[LinhaNormalizada],
) -> tuple[str, ...]:
    """Identifica campos de nivel do evento com estados/valores divergentes."""
    return tuple(
        nome for nome in CAMPOS_CONSTANTES_NO_EVENTO
        if len({(linha.status(nome), linha.valor(nome)) for linha in linhas}) > 1
    )


def construir_probabilidades_validas(
    linhas: list[LinhaNormalizada],
) -> tuple[Probabilidade, ...]:
    probabilidades: list[Probabilidade] = []
    for linha in linhas:
        codigo = linha.campos["probabilidadePerda"]
        valor = linha.campos["valorRisco"]
        if codigo.invalido or valor.invalido:
            continue
        if codigo.valido and str(codigo.valor) not in CODIGOS_PROBABILIDADE:
            continue
        if codigo.valido and valor.valido:
            probabilidades.append(Probabilidade(
                numero_linha=linha.numero_linha,
                codigo=str(codigo.valor),
                valor_risco=valor.valor,
            ))
    return tuple(probabilidades)


def construir_contabilizacoes_validas(
    linhas: list[LinhaNormalizada],
) -> tuple[Contabilizacao, ...]:
    contabilizacoes: list[Contabilizacao] = []
    for linha in linhas:
        if not any(linha.campos[nome].valido for nome in COLUNAS_CONTABILIZACAO):
            continue
        if any(linha.campos[nome].invalido for nome in COLUNAS_CONTABILIZACAO):
            continue
        if any(
            linha.campos[nome].ausente
            for nome in CAMPOS_CONTABILIZACAO_OBRIGATORIOS
        ):
            continue
        contabilizacoes.append(Contabilizacao(
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
        ))
    return tuple(contabilizacoes)


def montar_evento(
    id_evento: str, linhas: list[LinhaNormalizada]
) -> EventoAgrupado:
    """Constroi o evento preservando todas as linhas normalizadas originais."""
    conflitantes = identificar_campos_conflitantes(linhas)
    evento = EventoAgrupado(
        id_evento=id_evento,
        linhas=tuple(linhas),
        consistente=not conflitantes,
        campos_conflitantes=conflitantes,
        probabilidades=construir_probabilidades_validas(linhas),
        contabilizacoes=construir_contabilizacoes_validas(linhas),
    )
    totais = calcular_totais(evento)
    if totais is not None:
        evento.total_perda_efetiva = totais.perda_efetiva
        evento.total_provisao = totais.provisao
        evento.total_recuperado = totais.recuperado
        evento.valor_total_risco = totais.valor_total_risco
    return evento


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

def consolidar_eventos(
    eventos: dict[str, EventoAgrupado], data_base: str
) -> dict[str, EventoConsolidado]:
    """Constroi os consolidados preservando a ordem de entrada."""

    inicio_semestre, fim_semestre = calcular_intervalo_semestre(data_base)
    por_categoria: dict[str, list[EventoAgrupado]] = {}
    for evento in eventos.values():
        if not evento.consistente or evento.total_perda_efetiva is None:
            continue
        if classificar_evento(evento):
            continue
        categoria = evento.valor_evento("categoriaNivel1")
        if categoria is None:
            continue
        por_categoria.setdefault(str(categoria), []).append(evento)

    consolidados: dict[str, EventoConsolidado] = {}
    for categoria, eventos_da_categoria in por_categoria.items():
        perda_total = sum(
            (e.total_perda_efetiva for e in eventos_da_categoria),
            Decimal("0.00"),
        )
        provisao_total = sum(
            (e.total_provisao for e in eventos_da_categoria), Decimal("0.00")
        )
        perda_semestre = Decimal("0.00")
        provisao_semestre = Decimal("0.00")
        num_semestre = 0
        for evento in eventos_da_categoria:
            datas_contabilizacao = []
            for contabilizacao in evento.contabilizacoes:
                data_contabilizacao = contabilizacao.data_contabilizacao
                if data_contabilizacao is None:
                    continue
                datas_contabilizacao.append(data_contabilizacao)
                if inicio_semestre <= data_contabilizacao <= fim_semestre:
                    perda_semestre += contabilizacao.valor_perda_efetiva
                    provisao_semestre += contabilizacao.valor_provisao

            if (
                datas_contabilizacao
                and inicio_semestre
                <= min(datas_contabilizacao)
                <= fim_semestre
            ):
                num_semestre += 1

        consolidados[categoria] = EventoConsolidado(
            categoria_nivel1=categoria,
            num_eventos_total=len(eventos_da_categoria),
            num_eventos_semestre=num_semestre,
            perda_efetiva_total=perda_total,
            perda_efetiva_semestre=perda_semestre,
            provisao_total=provisao_total,
            provisao_semestre=provisao_semestre,
        )
    return consolidados
