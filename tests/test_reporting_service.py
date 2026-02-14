from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from openrouter_free_model_scouter.reporting.service import build_report
from reporting_fixtures import write_sample_timeline


class TestReportingService(unittest.TestCase):
    def test_build_report_includes_delta_and_recommendations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            xlsx_path = Path(tmp_dir) / "history.xlsx"
            output_path = Path(tmp_dir) / "availability-report.md"
            write_sample_timeline(xlsx_path)

            report_text = build_report(
                xlsx_path=xlsx_path,
                output_path=output_path,
                lookback_runs=3,
                top_n=10,
            )

            self.assertTrue(output_path.exists())
            self.assertIn("- Checked models: 5", report_text)
            self.assertIn("- Recovered models: `a:free`", report_text)
            self.assertIn("- Regressed models: `f:free`", report_text)
            self.assertIn("Moderate 429 pressure", report_text)

    def test_build_report_rejects_non_positive_lookback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            xlsx_path = Path(tmp_dir) / "history.xlsx"
            output_path = Path(tmp_dir) / "availability-report.md"
            write_sample_timeline(xlsx_path)

            with self.assertRaisesRegex(ValueError, "lookback-runs must be >= 1"):
                build_report(
                    xlsx_path=xlsx_path,
                    output_path=output_path,
                    lookback_runs=0,
                    top_n=10,
                )


if __name__ == "__main__":
    unittest.main()
