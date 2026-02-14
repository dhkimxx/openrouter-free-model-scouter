from __future__ import annotations

import unittest

from openrouter_free_model_scouter.reporting.analysis import (
    build_model_stats,
    build_run_snapshots,
    compute_run_deltas,
    count_statuses,
    generate_recommendations,
    select_stable_candidates,
    select_unstable_candidates,
)
from openrouter_free_model_scouter.reporting.constants import (
    STATUS_FAIL,
    STATUS_MISSING,
    STATUS_OK,
    STATUS_RATE_LIMITED,
)
from reporting_fixtures import sample_parsed_timeline


class TestReportingAnalysis(unittest.TestCase):
    def test_count_statuses(self) -> None:
        checked, ok, rate_limited, failed = count_statuses(
            [STATUS_OK, STATUS_RATE_LIMITED, STATUS_FAIL, STATUS_MISSING]
        )
        self.assertEqual((checked, ok, rate_limited, failed), (3, 1, 1, 1))

    def test_build_run_snapshots(self) -> None:
        run_labels, model_statuses = sample_parsed_timeline()
        snapshots = build_run_snapshots(run_labels, model_statuses)

        self.assertEqual(len(snapshots), 3)
        self.assertEqual((snapshots[0].checked, snapshots[0].ok, snapshots[0].rate_limited, snapshots[0].failed), (5, 3, 1, 1))
        self.assertEqual((snapshots[1].checked, snapshots[1].ok, snapshots[1].rate_limited, snapshots[1].failed), (6, 4, 1, 1))
        self.assertEqual((snapshots[2].checked, snapshots[2].ok, snapshots[2].rate_limited, snapshots[2].failed), (5, 3, 1, 1))

    def test_model_stats_and_candidate_selection(self) -> None:
        _, model_statuses = sample_parsed_timeline()
        model_stats = build_model_stats(model_statuses)

        self.assertEqual(len(model_stats), 6)

        stable_candidates = select_stable_candidates(model_stats)
        unstable_candidates = select_unstable_candidates(model_stats)

        self.assertEqual([item.model_id for item in stable_candidates], ["e:free"])
        self.assertEqual([item.model_id for item in unstable_candidates], ["a:free", "c:free"])

    def test_compute_run_deltas(self) -> None:
        run_labels, model_statuses = sample_parsed_timeline()
        recovered, regressed = compute_run_deltas(run_labels, model_statuses)

        self.assertEqual(recovered, ["a:free"])
        self.assertEqual(regressed, ["f:free"])

    def test_generate_recommendations(self) -> None:
        run_labels, model_statuses = sample_parsed_timeline()
        snapshots = build_run_snapshots(run_labels, model_statuses)
        model_stats = build_model_stats(model_statuses)
        stable_candidates = select_stable_candidates(model_stats)
        unstable_candidates = select_unstable_candidates(model_stats)

        recommendations = generate_recommendations(
            latest_snapshot=snapshots[-1],
            stable_candidates=stable_candidates,
            unstable_candidates=unstable_candidates,
        )

        merged = "\n".join(recommendations)
        self.assertIn("Moderate 429 pressure", merged)
        self.assertIn("Non-429 failures are elevated", merged)
        self.assertIn("Prefer stable free models", merged)
        self.assertIn("Treat high-variance models", merged)


if __name__ == "__main__":
    unittest.main()
