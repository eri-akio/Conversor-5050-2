"""Ponto de entrada do Conversor DRO 5050 (versao simples).

Sem argumentos, abre a interface desktop. Quando um caminho de planilha
Excel e informado, roda em modo terminal.

Ver docs/plano_conversor_dro_5050_simples.md para o contrato funcional
completo e docs/plano_conversor_dro_5050_simples.md secao 25 para o roadmap
de implementacao (ainda em andamento - Fase 1 concluida).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Conversor DRO 5050 - versao simples",
    )
    parser.add_argument(
        "planilha",
        nargs="?",
        type=Path,
        help="Caminho da planilha Excel de entrada (modo terminal).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Pasta de saida para o XML e o relatorio XLSX.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    if args.planilha is None:
        from src.gui import run_gui

        run_gui()
        return 0

    from src.conversion import convert

    convert(args.planilha, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
