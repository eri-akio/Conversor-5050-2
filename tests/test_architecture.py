"""Restri??es finais da arquitetura de regras do conversor."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

MODULOS_PUROS = ("builders.py", "calculations.py", "normalizers.py")
FAMILIAS_DE_REGRA = {
    "rules_local.py": "BASE-",
    "rules_pre.py": "DRO001",
    "rule_pos.py": "DRO000",
}
PADRAO_CODIGO = re.compile(r"^(?:BASE-|DRO001|DRO000)")


def _arvore(nome: str) -> ast.Module:
    return ast.parse((SRC / nome).read_text(encoding="utf-8"), filename=nome)


def _modulos_importados(nome: str) -> set[str]:
    modulos: set[str] = set()
    for no in ast.walk(_arvore(nome)):
        if isinstance(no, ast.Import):
            modulos.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            modulos.add(no.module)
    return modulos


@pytest.mark.parametrize("nome", MODULOS_PUROS)
def test_modulos_puros_nao_dependem_de_ocorrencia(nome: str) -> None:
    arvore = _arvore(nome)
    imports_ocorrencia = [
        alias
        for no in ast.walk(arvore)
        if isinstance(no, ast.ImportFrom)
        for alias in no.names
        if alias.name == "Ocorrencia"
    ]
    chamadas_ocorrencia = [
        no
        for no in ast.walk(arvore)
        if isinstance(no, ast.Call)
        and isinstance(no.func, ast.Name)
        and no.func.id == "Ocorrencia"
    ]

    assert imports_ocorrencia == []
    assert chamadas_ocorrencia == []


@pytest.mark.parametrize(
    ("nome", "prefixo"),
    FAMILIAS_DE_REGRA.items(),
)
def test_modulo_de_regra_so_declara_sua_familia(
    nome: str, prefixo: str
) -> None:
    codigos = {
        no.value
        for no in ast.walk(_arvore(nome))
        if isinstance(no, ast.Constant)
        and isinstance(no.value, str)
        and PADRAO_CODIGO.match(no.value)
    }

    assert codigos
    assert all(codigo.startswith(prefixo) for codigo in codigos)


def test_orquestrador_nao_declara_codigos_de_regra() -> None:
    fonte = (SRC / "conversion.py").read_text(encoding="utf-8")

    assert PADRAO_CODIGO.search(fonte) is None


def test_grafo_de_dependencias_respeita_as_camadas() -> None:
    proibidos = {
        "builders.py": {"src.rules_local", "src.rules_pre", "src.rule_pos"},
        "calculations.py": {"src.builders", "src.rules_local", "src.rules_pre", "src.rule_pos"},
        "normalizers.py": {"src.rules_local", "src.rules_pre", "src.rule_pos"},
        "rules_pre.py": {"src.rules_local", "src.rule_pos"},
        "rule_pos.py": {"src.rules_local", "src.rules_pre"},
    }

    for nome, dependencias_proibidas in proibidos.items():
        assert _modulos_importados(nome).isdisjoint(dependencias_proibidas)


def test_nome_antigo_de_pos_processamento_foi_removido() -> None:
    assert not (SRC / "rules_post.py").exists()

def test_rules_pre_nao_emite_ocorrencia_na_etapa_de_agrupamento() -> None:
    fonte = (SRC / "rules_pre.py").read_text(encoding="utf-8")

    assert "ETAPA_AGRUPAMENTO" not in fonte

