from __future__ import annotations

from pathlib import Path
import unittest

from openrouter_free_model_scouter.reporting.analysis import (
    build_model_stats,
    build_run_snapshots,
    compute_run_deltas,
    generate_recommendations,
    select_stable_candidates,
    select_unstable_candidates,
)
from openrouter_free_model_scouter.reporting.renderer import (
    format_model_table,
    format_run_table,
    render_report,
)
from reporting_fixtures import sample_parsed_timeline


class TestReportingRenderer(unittest.TestCase):
    def test_format_tables(self) -> None:
        run_labels, model_statuses = sample_parsed_timeline()
        snapshots = build_run_snapshots(run_labels, model_statuses)
        model_stats = build_model_stats(model_statuses)

        run_lines = format_run_table(snapshots)
        model_lines = format_model_table(model_stats[:2])

        self.assertTrue(run_lines[0].startswith("| Run |"))
        self.assertGreater(len(run_lines), 2)
        self.assertTrue(model_lines[0].startswith("| Model |"))
        self.assertGreater(len(model_lines), 2)

    def test_render_report_with_delta(self) -> None:
        run_labels, model_statuses = sample_parsed_timeline()
        snapshots = build_run_snapshots(run_labels, model_statuses)
        model_stats = build_model_stats(model_statuses)
        stable_candidates = select_stable_candidates(model_stats)
        unstable_candidates = select_unstable_candidates(model_stats)
        recovered_models, regressed_models = compute_run_deltas(run_labels, model_statuses)
        recommendations = generate_recommendations(
            latest_snapshot=snapshots[-1],
            stable_candidates=stable_candidates,
            unstable_candidates=unstable_candidates,
        )

        report_text = render_report(
            xlsx_path=Path("results/history.xlsx"),
            selected_labels=run_labels,
            snapshots=snapshots,
            latest_snapshot=snapshots[-1],
            previous_snapshot=snapshots[-2],
            stable_candidates=stable_candidates,
            unstable_candidates=unstable_candidates,
            recovered_models=recovered_models,
            regressed_models=regressed_models,
            recommendations=recommendations,
            top_n=10,
        )

        self.assertIn("## Delta vs Previous Run", report_text)
        self.assertIn("- Recovered models: `a:free`", report_text)
        self.assertIn("- Regressed models: `f:free`", report_text)

    def test_render_report_without_previous_snapshot(self) -> None:
        run_labels = ["run-1"]
        model_statuses = {"a:free": ["OK"]}
        snapshots = build_run_snapshots(run_labels, model_statuses)

        report_text = render_report(
            xlsx_path=Path("results/history.xlsx"),
            selected_labels=run_labels,
            snapshots=snapshots,
            latest_snapshot=snapshots[-1],
            previous_snapshot=None,
            stable_candidates=[],
            unstable_candidates=[],
            recovered_models=[],
            regressed_models=[],
            recommendations=["Current trend is healthy. Keep the existing scan profile."],
            top_n=10,
        )

        self.assertIn("Not enough history to compute deltas", report_text)


if __name__ == "__main__":
    unittest.main()
