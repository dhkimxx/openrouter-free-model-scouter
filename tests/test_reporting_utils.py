from __future__ import annotations

import unittest

from openrouter_free_model_scouter.reporting.utils import (
    safe_ratio,
    to_percent,
    truncate_models,
)


class TestReportingUtils(unittest.TestCase):
    def test_safe_ratio_handles_zero_denominator(self) -> None:
        self.assertEqual(safe_ratio(1, 0), 0.0)
        self.assertEqual(safe_ratio(0, 10), 0.0)
        self.assertEqual(safe_ratio(3, 4), 0.75)

    def test_to_percent_formats_one_decimal(self) -> None:
        self.assertEqual(to_percent(0.0), "0.0%")
        self.assertEqual(to_percent(0.448), "44.8%")

    def test_truncate_models_handles_limits(self) -> None:
        self.assertEqual(truncate_models([]), "none")
        self.assertEqual(truncate_models(["a:free", "b:free"]), "`a:free`, `b:free`")
        self.assertEqual(
            truncate_models(["a", "b", "c"], limit=2),
            "`a`, `b` (+1 more)",
        )


if __name__ == "__main__":
    unittest.main()
