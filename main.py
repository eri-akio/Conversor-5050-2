from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Conversor DRO 5050",
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
