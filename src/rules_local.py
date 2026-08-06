"""Regras locais do conversor, identificadas exclusivamente por BASE-* ."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Iterable

from src.calculations import calcular_intervalo_semestre
from src.models import (
    CampoNormalizado,
    ETAPA_AGRUPAMENTO,
    ETAPA_NORMALIZACAO,
    ETAPA_POS_PROCESSAMENTO,
    ETAPA_PRE_PROCESSAMENTO,
    Contabilizacao,
    EventoAgrupado,
    LinhaNormalizada,
    Ocorrencia,
    Probabilidade,
    TIPO_ERRO_IMPEDITIVO,
)
from src.normalizers import (
    CAMPOS_SEMPRE_OBRIGATORIOS,
    colapsar_espacos_para_validacao,
)

NATUREZAS_CONTINGENCIA = frozenset({"TRI", "TRA", "CIV", "OUT"})
_PADRAO_ID_EVENTO = re.compile(r"^[0-9A-Za-z]{1,40}$")
_PADRAO_CATEGORIA_NIVEL1 = re.compile(r"^[1-8]$")
_PADRAO_CATEGORIA_NIVEL2 = re.compile(
    r"^(?:11|12|21|22|31|32|33|41|42|43|44|45|51|61|71|8[1-6])$"
)
TIPOS_AVALIACAO_VALIDOS = frozenset({"I", "IE", "M", "ME", "NA"})
_PADRAO_UNIDADE_NEGOCIO = re.compile(r"^[1-8]$")
NATUREZAS_CONTINGENCIA_VALIDAS = NATUREZAS_CONTINGENCIA | {"NA"}
_PADRAO_CODIGO_EVENTO_ORIGEM = re.compile(r"^[0-9A-Za-z]{1,73}$")
LIMITE_DESCRICAO_EVENTO = 200
_PADRAO_ID_BACEN = re.compile(r"^(?:[Zz][0-9]{7}|[Ii][0-9]{5})$")
RISCOS_ASSOCIADOS_VALIDOS = frozenset({"C", "M", "NA"})
OPCOES_SIM_NAO = frozenset({"S", "N"})
CODIGO_DOCUMENTO_5050 = "5050"
_PADRAO_CONGLOMERADO = re.compile(r"^C[0-9]{7}$")
TIPOS_REMESSA_VALIDOS = frozenset({"I", "S"})
OPCOES_PROVISAO_ACUMULADA_VALIDAS = frozenset({"S", "N"})


CODIGOS_PROBABILIDADE = frozenset({"PR", "PO", "RE"})
COLUNAS_CONTABILIZACAO: tuple[str, ...] = (
    "dataContabilizacao", "contaBalAnaliticoDebito", "nomeContaDebito",
    "contaBalAnaliticoCredito", "nomeContaCredito", "contaCosifDebito",
    "contaCosifCredito", "valorPerdaEfetiva", "valorProvisao",
    "valorRecuperacao", "fonteRecuperacao",
)
CAMPOS_CONTABILIZACAO_OBRIGATORIOS = (
    "dataContabilizacao", "valorPerdaEfetiva", "valorProvisao",
    "valorRecuperacao",
)
CAMPOS_CONSTANTES_NO_EVENTO = (
    "categoriaNivel1", "categoriaNivel2", "tipoAvaliacao", "unidadeNegocio",
    "dataDescoberta", "dataOcorrencia", "naturezaContingencia",
    "codSistemaOrigem", "nomeSistema", "codigoEventoOrigem",
    "descricaoEvento", "riscoAssociado", "ligadoRiscoSocioAmbiental",
    "ligadoRiscoCibernetico", "negocioDescontinuado", "idBacen",
)
_PADRAO_COSIF = re.compile(r"^(?:[0-9]{8}|[0-9]{10})$")
_PADRAO_NOME_ASCII = re.compile(r"^[A-Za-z0-9 ]{1,70}$")
_PADRAO_COD_SISTEMA_ORIGEM = re.compile(r"^[0-9A-Za-z]{1,10}$")
_PADRAO_CONTA_BAL_ANALITICO = re.compile(r"^[0-9]{1,24}$")

@dataclass(frozen=True)
class ResultadoValidacaoLocal:
    ocorrencias: tuple[Ocorrencia, ...]
    bloqueia_regras_regulatorias: bool = False
    bloqueia_consolidacao: bool = False


def bloqueia_regras_regulatorias(
    ocorrencias_evento: Iterable[Ocorrencia],
) -> bool:
    """Qualquer erro local impeditivo bloqueia criticas oficiais."""

    return any(
        ocorrencia.tipo == TIPO_ERRO_IMPEDITIVO
        and ocorrencia.codigo.startswith("BASE-")
        for ocorrencia in ocorrencias_evento
    )


def bloqueia_consolidacao(
    ocorrencias_evento: Iterable[Ocorrencia],
) -> bool:
    """Qualquer erro local impeditivo exclui o evento da consolidacao."""

    return any(
        ocorrencia.tipo == TIPO_ERRO_IMPEDITIVO
        and ocorrencia.codigo.startswith("BASE-")
        for ocorrencia in ocorrencias_evento
    )


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


def _erro_pos(
    evento: EventoAgrupado,
    codigo: str,
    descricao: str,
    detalhe: str,
    campos: tuple[str, ...] = (),
) -> Ocorrencia:
    return Ocorrencia(
        etapa=ETAPA_POS_PROCESSAMENTO,
        tipo=TIPO_ERRO_IMPEDITIVO,
        codigo=codigo,
        descricao=descricao,
        detalhe=detalhe,
        linhas=evento.numeros_linha,
        id_evento=evento.id_evento,
        campos=campos,
    )

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

def validar_convencao_de_sinal(
    evento: EventoAgrupado,
) -> Ocorrencia | None:
    """Compatibilidade: sinais financeiros sao avaliados pelas DRO000*."""

    del evento
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
            "tipoAvaliacao deve ser I, IE, M, ME ou NA.",
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
            "naturezaContingencia deve ser TRI, TRA, CIV, OUT ou NA.",
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

def cabecalho_tem_data_base_valida(
    cabecalho: dict[str, CampoNormalizado],
) -> bool:
    """Usado por conversion.py para decidir se as etapas dependentes de
    semestre (P3/consolidacao) podem rodar."""

    return cabecalho["dataBase"].valido

def validar_datas_apos_data_base(
    evento: EventoAgrupado, data_base: str
) -> list[Ocorrencia]:
    """BASE-DATA-PERIODO-001 (regra local — nao ha codigo oficial
    equivalente): dataOcorrencia, dataDescoberta e toda dataContabilizacao
    do evento nao podem ser posteriores ao fim do semestre da dataBase. So
    deve ser chamada quando a dataBase ja foi validada (P1/P2)."""

    if not evento.consistente:
        return []

    _inicio_semestre, fim_semestre = calcular_intervalo_semestre(data_base)
    ocorrencias: list[Ocorrencia] = []

    for nome_campo in ("dataOcorrencia", "dataDescoberta"):
        valor_data = evento.valor_evento(nome_campo)
        if isinstance(valor_data, date) and valor_data > fim_semestre:
            ocorrencias.append(
                _erro_pos(
                    evento,
                    "BASE-DATA-PERIODO-001",
                    f"{nome_campo} posterior ao período da data-base.",
                    f"{nome_campo}={valor_data} > fim do semestre={fim_semestre}.",
                    (nome_campo,),
                )
            )

    datas_contabilizacao_posteriores = [
        c.data_contabilizacao
        for c in evento.contabilizacoes
        if c.data_contabilizacao is not None
        and c.data_contabilizacao > fim_semestre
    ]
    if datas_contabilizacao_posteriores:
        ocorrencias.append(
            _erro_pos(
                evento,
                "BASE-DATA-PERIODO-001",
                "dataContabilizacao posterior ao período da data-base.",
                (
                    "dataContabilizacao mais recente="
                    f"{max(datas_contabilizacao_posteriores)} > fim do "
                    f"semestre={fim_semestre}."
                ),
                ("dataContabilizacao",),
            )
        )

    return ocorrencias

# Validacoes locais da montagem. As funcoes de analise preservam a mesma
# ordem de linhas e descartam da estrutura final apenas registros invalidos.
def _analisar_probabilidades(
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


def validar_probabilidades_linhas(linhas: list[LinhaNormalizada]) -> list[Ocorrencia]:
    return _analisar_probabilidades(linhas)[1]

def _analisar_contabilizacoes(
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


def validar_contabilizacoes_linhas(linhas: list[LinhaNormalizada]) -> list[Ocorrencia]:
    return _analisar_contabilizacoes(linhas)[1]


def validar_contabilizacao_antes_pre(
    id_evento: str, contabilizacao: Contabilizacao
) -> list[Ocorrencia]:
    ocorrencias: list[Ocorrencia] = []
    linhas = (contabilizacao.numero_linha,)
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
                descricao="Contabiliza\u00e7\u00e3o com os tr\u00eas movimentos zerados.",
                detalhe=(
                    "valorPerdaEfetiva, valorProvisao e "
                    "valorRecuperacao est\u00e3o todos zerados."
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
    return ocorrencias


def validar_contabilizacao_depois_pre(
    id_evento: str, contabilizacao: Contabilizacao
) -> list[Ocorrencia]:
    linhas = (contabilizacao.numero_linha,)
    fonte = contabilizacao.fonte_recuperacao
    if contabilizacao.valor_recuperacao == 0 and fonte in ("S", "O"):
        return [
            Ocorrencia(
                etapa=ETAPA_AGRUPAMENTO,
                tipo=TIPO_ERRO_IMPEDITIVO,
                codigo="BASE-REC-FONTE-001",
                descricao=(
                    "Fonte de recupera\u00e7\u00e3o informada sem "
                    "recupera\u00e7\u00e3o efetiva."
                ),
                detalhe=(
                    "valorRecuperacao=0,00 n\u00e3o aceita "
                    f"fonteRecuperacao={fonte!r}."
                ),
                linhas=linhas,
                id_evento=id_evento,
                campos=("valorRecuperacao", "fonteRecuperacao"),
            )
        ]
    return []


def validar_referencias_linha(linha: LinhaNormalizada) -> list[Ocorrencia]:
    ocorrencias: list[Ocorrencia] = []
    for campo_cosif in ("contaCosifDebito", "contaCosifCredito"):
        valor_cosif = linha.valor(campo_cosif)
        if valor_cosif is not None and not _PADRAO_COSIF.match(str(valor_cosif)):
            ocorrencias.append(
                Ocorrencia(
                    etapa=ETAPA_AGRUPAMENTO,
                    tipo=TIPO_ERRO_IMPEDITIVO,
                    codigo="BASE-COSIF-FORM-001",
                    descricao="COSIF n\u00e3o possui 8 ou 10 d\u00edgitos.",
                    detalhe=f"{campo_cosif}={valor_cosif!r}.",
                    linhas=(linha.numero_linha,),
                    campos=(campo_cosif,),
                )
            )
    return ocorrencias

def validar_sistemas_e_contas_globais(
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


def validar_estrutura_evento(evento: EventoAgrupado) -> list[Ocorrencia]:
    """Executa as regras locais que dependem da estrutura montada."""

    ocorrencias: list[Ocorrencia] = []
    _consistente, _conflitantes, ocorrencia_conflito = verificar_consistencia(
        evento.id_evento, list(evento.linhas)
    )
    if ocorrencia_conflito is not None:
        ocorrencias.append(ocorrencia_conflito)
    ocorrencias.extend(validar_probabilidades_linhas(list(evento.linhas)))
    ocorrencias.extend(validar_contabilizacoes_linhas(list(evento.linhas)))
    if evento.consistente:
        ocorrencias.extend(
            validar_probabilidades_do_evento(
                evento.id_evento,
                evento.valor_evento("tipoAvaliacao"),
                evento.probabilidades,
            )
        )
    return ocorrencias


def validar_totais_evento(evento: EventoAgrupado) -> list[Ocorrencia]:
    """Nao amplia as convencoes de sinal definidas pelas DRO000*."""

    del evento
    return []


def validar_evento_local(
    evento: EventoAgrupado,
    ocorrencias_anteriores: Iterable[Ocorrencia] = (),
) -> ResultadoValidacaoLocal:
    """Valida formatos e explicita os bloqueios independentes do evento."""

    anteriores = tuple(ocorrencias_anteriores)
    ocorrencias_formato = (
        tuple(validar_formatos_e_dominios_evento(evento))
        if evento.consistente
        else ()
    )
    ocorrencias_locais = (*anteriores, *ocorrencias_formato)
    return ResultadoValidacaoLocal(
        ocorrencias=ocorrencias_formato,
        bloqueia_regras_regulatorias=bloqueia_regras_regulatorias(
            ocorrencias_locais
        ),
        bloqueia_consolidacao=bloqueia_consolidacao(ocorrencias_locais),
    )

