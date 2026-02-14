from __future__ import annotations

import unittest

from openrouter_free_model_scouter.reporting.cli import build_parser


class TestReportingCli(unittest.TestCase):
    def test_build_parser_defaults(self) -> None:
        parser = build_parser()
        args = parser.parse_args([])

        self.assertEqual(args.xlsx_path, "results/history.xlsx")
        self.assertEqual(args.output_path, "results/availability-report.md")
        self.assertEqual(args.lookback_runs, 24)
        self.assertEqual(args.top_n, 10)


if __name__ == "__main__":
    unittest.main()
