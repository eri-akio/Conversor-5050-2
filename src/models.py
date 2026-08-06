"""Modelos de dados compartilhados pelo conversor.

Ver docs/plano_conversor_dro_5050_simples.md secao 21 para o formato do
relatorio que consome Ocorrencia.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

TIPO_ERRO_IMPEDITIVO = "ERRO IMPEDITIVO"
TIPO_AVISO = "AVISO"
TIPO_FALHA_TECNICA = "FALHA TÉCNICA"

ETAPA_ESTRUTURA = "Estrutura da planilha"
ETAPA_NORMALIZACAO = "Normalização"
ETAPA_AGRUPAMENTO = "Agrupamento e cálculos"
ETAPA_PRE_PROCESSAMENTO = "Pré-processamento"
ETAPA_POS_PROCESSAMENTO = "Pós-processamento"
ETAPA_GERACAO_XML = "Geração do XML"
ETAPA_GRAVACAO_ARQUIVO = "Gravação de arquivo"
ETAPA_XSD = "Validação XSD"


@dataclass(frozen=True)
class Ocorrencia:
    """Uma linha da aba Inconsistencias do relatorio (secao 21)."""

    etapa: str
    tipo: str
    codigo: str
    descricao: str
    detalhe: str
    linhas: tuple[int, ...] = ()
    id_evento: str | None = None
    campos: tuple[str, ...] = field(default_factory=tuple)


class StatusCampo(Enum):
    """Estado de uma celula apos a normalizacao (secao 8)."""

    AUSENTE = "AUSENTE"
    INVALIDO = "INVALIDO"
    VALIDO = "VALIDO"


@dataclass(frozen=True)
class CampoNormalizado:
    """Resultado da normalizacao de uma celula."""

    nome: str
    valor_original: object
    valor: object | None
    status: StatusCampo
    motivo: str | None = None

    @property
    def ausente(self) -> bool:
        return self.status is StatusCampo.AUSENTE

    @property
    def invalido(self) -> bool:
        return self.status is StatusCampo.INVALIDO

    @property
    def valido(self) -> bool:
        return self.status is StatusCampo.VALIDO


@dataclass(frozen=True)
class LinhaNormalizada:
    """Uma linha da aba Base apos a normalizacao (Fase 3/4)."""

    numero_linha: int
    campos: dict[str, CampoNormalizado]

    def valor(self, nome: str) -> object | None:
        campo = self.campos.get(nome)
        return campo.valor if campo is not None else None

    def status(self, nome: str) -> StatusCampo:
        campo = self.campos.get(nome)
        return campo.status if campo is not None else StatusCampo.AUSENTE


@dataclass(frozen=True)
class Probabilidade:
    """Uma probabilidade de perda associada a uma linha (secao 11)."""

    numero_linha: int
    codigo: str
    valor_risco: object


@dataclass(frozen=True)
class Contabilizacao:
    """Uma contabilizacao associada a uma linha (secao 12)."""

    numero_linha: int
    data_contabilizacao: object | None
    valor_perda_efetiva: object | None
    valor_provisao: object | None
    valor_recuperacao: object | None
    fonte_recuperacao: str | None
    conta_debito: str | None
    conta_credito: str | None
    conta_cosif_debito: str | None
    conta_cosif_credito: str | None


@dataclass
class EventoAgrupado:
    """Todas as linhas de um mesmo idEvento, ja consolidadas (secao 10/15)."""

    id_evento: str
    linhas: tuple[LinhaNormalizada, ...]
    consistente: bool
    campos_conflitantes: tuple[str, ...]
    probabilidades: tuple[Probabilidade, ...]
    contabilizacoes: tuple[Contabilizacao, ...]
    total_perda_efetiva: object | None = None
    total_provisao: object | None = None
    total_recuperado: object | None = None
    valor_total_risco: object | None = None

    @property
    def numeros_linha(self) -> tuple[int, ...]:
        return tuple(linha.numero_linha for linha in self.linhas)

    def valor_evento(self, nome: str) -> object | None:
        """Valor de um campo que e igual em todas as linhas (secao 10)."""
        return self.linhas[0].valor(nome)


@dataclass(frozen=True)
class EventoConsolidado:
    """Um grupo consolidado por categoriaNivel1 (secao 16)."""

    categoria_nivel1: str
    num_eventos_total: int
    num_eventos_semestre: int
    perda_efetiva_total: object
    perda_efetiva_semestre: object
    provisao_total: object
    provisao_semestre: object


@dataclass(frozen=True)
class ResultadoConversao:
    """Resultado de 1 execucao completa (secao 4/22)."""

    status_local: str
    status_xsd: str
    ocorrencias: tuple[Ocorrencia, ...]
    caminho_xml: object | None
    caminho_relatorio: object | None
    mensagem: str
