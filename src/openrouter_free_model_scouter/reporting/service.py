from __future__ import annotations

from pathlib import Path

from .analysis import (
    build_model_stats,
    build_run_snapshots,
    compute_run_deltas,
    generate_recommendations,
    select_stable_candidates,
    select_unstable_candidates,
)
from .renderer import render_report
from .timeline import read_timeline, slice_lookback


def build_report(
    *,
    xlsx_path: Path,
    output_path: Path,
    lookback_runs: int,
    top_n: int,
) -> str:
    if not xlsx_path.exists():
        raise FileNotFoundError(f"timeline workbook not found: {xlsx_path}")

    run_labels, model_statuses = read_timeline(xlsx_path)
    selected_labels, selected_statuses = slice_lookback(
        run_labels,
        model_statuses,
        lookback_runs,
    )

    snapshots = build_run_snapshots(selected_labels, selected_statuses)
    if not snapshots:
        raise ValueError("no run snapshots were parsed from the workbook")

    latest_snapshot = snapshots[-1]
    previous_snapshot = snapshots[-2] if len(snapshots) >= 2 else None

    model_stats = build_model_stats(selected_statuses)
    stable_candidates = select_stable_candidates(model_stats)
    unstable_candidates = select_unstable_candidates(model_stats)
    recovered_models, regressed_models = compute_run_deltas(
        selected_labels,
        selected_statuses,
    )

    recommendations = generate_recommendations(
        latest_snapshot=latest_snapshot,
        stable_candidates=stable_candidates,
        unstable_candidates=unstable_candidates,
    )

    report_text = render_report(
        xlsx_path=xlsx_path,
        selected_labels=selected_labels,
        snapshots=snapshots,
        latest_snapshot=latest_snapshot,
        previous_snapshot=previous_snapshot,
        stable_candidates=stable_candidates,
        unstable_candidates=unstable_candidates,
        recovered_models=recovered_models,
        regressed_models=regressed_models,
        recommendations=recommendations,
        top_n=top_n,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")
    return report_text
