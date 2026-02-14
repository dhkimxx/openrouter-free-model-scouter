from __future__ import annotations

import argparse
from pathlib import Path

from .service import build_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a markdown trend report from results/history.xlsx"
    )
    parser.add_argument(
        "--xlsx-path",
        default="results/history.xlsx",
        help="Input timeline workbook path",
    )
    parser.add_argument(
        "--output-path",
        default="results/availability-report.md",
        help="Output markdown report path",
    )
    parser.add_argument(
        "--lookback-runs",
        type=int,
        default=24,
        help="How many recent runs to analyze",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Max rows in stable/unstable model tables",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        report_text = build_report(
            xlsx_path=Path(args.xlsx_path),
            output_path=Path(args.output_path),
            lookback_runs=args.lookback_runs,
            top_n=max(1, args.top_n),
        )
    except Exception as exc:  # pragma: no cover
        print(f"[ERROR] {exc}")
        raise SystemExit(1)

    output_path = Path(args.output_path)
    print(f"[OK] Report written: {output_path}")
    print(f"[INFO] {len(report_text.splitlines())} lines generated")
