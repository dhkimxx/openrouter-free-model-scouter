from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from openrouter_free_model_scouter.reporting.constants import (
    STATUS_FAIL,
    STATUS_MISSING,
    STATUS_OK,
    STATUS_RATE_LIMITED,
)
from openrouter_free_model_scouter.reporting.timeline import (
    parse_status,
    read_timeline,
    slice_lookback,
)
from reporting_fixtures import write_sample_timeline


class TestReportingTimeline(unittest.TestCase):
    def test_parse_status_maps_values(self) -> None:
        self.assertEqual(parse_status(None), STATUS_MISSING)
        self.assertEqual(parse_status(""), STATUS_MISSING)
        self.assertEqual(parse_status("OK (12ms)"), STATUS_OK)
        self.assertEqual(parse_status("429"), STATUS_RATE_LIMITED)
        self.assertEqual(parse_status("HTTP 500"), STATUS_FAIL)

    def test_read_timeline_returns_labels_and_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            xlsx_path = Path(tmp_dir) / "history.xlsx"
            write_sample_timeline(xlsx_path)

            run_labels, model_statuses = read_timeline(xlsx_path)

            self.assertEqual(
                run_labels,
                [
                    "2025-01-01 00:00:00",
                    "2025-01-01 00:01:00",
                    "2025-01-01 00:02:00",
                ],
            )
            self.assertEqual(model_statuses["a:free"], [STATUS_OK, STATUS_RATE_LIMITED, STATUS_OK])
            self.assertEqual(model_statuses["d:free"], [STATUS_MISSING, STATUS_OK, STATUS_MISSING])

    def test_slice_lookback(self) -> None:
        run_labels = ["r1", "r2", "r3"]
        model_statuses = {"a:free": [STATUS_OK, STATUS_FAIL, STATUS_OK]}

        sliced_labels, sliced_statuses = slice_lookback(run_labels, model_statuses, 2)

        self.assertEqual(sliced_labels, ["r2", "r3"])
        self.assertEqual(sliced_statuses["a:free"], [STATUS_FAIL, STATUS_OK])

    def test_slice_lookback_rejects_non_positive(self) -> None:
        with self.assertRaisesRegex(ValueError, "lookback-runs must be >= 1"):
            slice_lookback(["r1"], {"a:free": [STATUS_OK]}, 0)


if __name__ == "__main__":
    unittest.main()
