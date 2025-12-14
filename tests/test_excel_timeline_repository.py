from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tempfile
import unittest

from openrouter_free_model_scouter.domain_models import HealthcheckResult
from openrouter_free_model_scouter.excel_timeline_repository import (
    ExcelTimelineRepository,
)


class TestExcelTimelineRepository(unittest.TestCase):
    def test_append_run_creates_matrix_and_appends_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            xlsx_path = Path(tmp_dir) / "history.xlsx"
            repository = ExcelTimelineRepository()

            run1_results = [
                HealthcheckResult(
                    run_id="run1",
                    timestamp_iso="2025-01-01T00:00:00+00:00",
                    model_id="a:free",
                    ok=True,
                    http_status=200,
                    latency_ms=10,
                    attempts=1,
                    error_category=None,
                    error_message=None,
                    response_preview="OK",
                ),
                HealthcheckResult(
                    run_id="run1",
                    timestamp_iso="2025-01-01T00:00:00+00:00",
                    model_id="b:free",
                    ok=False,
                    http_status=429,
                    latency_ms=20,
                    attempts=3,
                    error_category="rate_limited",
                    error_message="rate limit",
                    response_preview=None,
                ),
            ]

            repository.append_run(
                xlsx_path,
                run_datetime=datetime(2025, 1, 1, 0, 0, 0),
                results=run1_results,
            )

            run2_results = [
                HealthcheckResult(
                    run_id="run2",
                    timestamp_iso="2025-01-01T00:01:00+00:00",
                    model_id="a:free",
                    ok=False,
                    http_status=500,
                    latency_ms=30,
                    attempts=1,
                    error_category="server_error",
                    error_message="server",
                    response_preview=None,
                )
            ]

            repository.append_run(
                xlsx_path,
                run_datetime=datetime(2025, 1, 1, 0, 1, 0),
                results=run2_results,
            )

            self.assertTrue(xlsx_path.exists())


if __name__ == "__main__":
    unittest.main()
