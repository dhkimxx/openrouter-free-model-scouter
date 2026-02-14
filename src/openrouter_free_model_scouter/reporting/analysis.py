from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple

from .constants import (
    MIN_MODEL_SAMPLES,
    STATUS_MISSING,
    STATUS_OK,
    STATUS_RATE_LIMITED,
    STABLE_OK_RATE_MIN,
    STABLE_RATE_LIMITED_RATE_MAX,
    UNSTABLE_FLIP_MIN,
    UNSTABLE_OK_RATE_MAX,
    UNSTABLE_RATE_LIMITED_RATE_MIN,
)
from .models import ModelStats, RunSnapshot


def count_statuses(statuses: Iterable[str]) -> Tuple[int, int, int, int]:
    ok = 0
    rate_limited = 0
    failed = 0

    for status in statuses:
        if status == STATUS_MISSING:
            continue
        if status == STATUS_OK:
            ok += 1
        elif status == STATUS_RATE_LIMITED:
            rate_limited += 1
        else:
            failed += 1

    checked = ok + rate_limited + failed
    return checked, ok, rate_limited, failed


def build_run_snapshots(
    run_labels: Sequence[str],
    model_statuses: Dict[str, List[str]],
) -> List[RunSnapshot]:
    snapshots: List[RunSnapshot] = []

    for run_index, run_label in enumerate(run_labels):
        checked, ok, rate_limited, failed = count_statuses(
            statuses[run_index] for statuses in model_statuses.values()
        )
        snapshots.append(
            RunSnapshot(
                label=run_label,
                checked=checked,
                ok=ok,
                rate_limited=rate_limited,
                failed=failed,
            )
        )

    return snapshots


def build_model_stats(model_statuses: Dict[str, List[str]]) -> List[ModelStats]:
    stats: List[ModelStats] = []

    for model_id, statuses in model_statuses.items():
        sampled_statuses = [status for status in statuses if status != STATUS_MISSING]
        if not sampled_statuses:
            continue

        ok_count = sampled_statuses.count(STATUS_OK)
        rate_limited_count = sampled_statuses.count(STATUS_RATE_LIMITED)
        fail_count = len(sampled_statuses) - ok_count - rate_limited_count
        flip_count = sum(
            1
            for previous, current in zip(sampled_statuses, sampled_statuses[1:])
            if previous != current
        )

        stats.append(
            ModelStats(
                model_id=model_id,
                samples=len(sampled_statuses),
                ok_count=ok_count,
                rate_limited_count=rate_limited_count,
                fail_count=fail_count,
                flip_count=flip_count,
                latest_status=sampled_statuses[-1],
            )
        )

    return stats


def select_stable_candidates(model_stats: Sequence[ModelStats]) -> List[ModelStats]:
    candidates = [
        item
        for item in model_stats
        if item.samples >= MIN_MODEL_SAMPLES
        and item.ok_rate >= STABLE_OK_RATE_MIN
        and item.rate_limited_rate <= STABLE_RATE_LIMITED_RATE_MAX
    ]
    candidates.sort(
        key=lambda item: (
            -item.ok_rate,
            item.rate_limited_rate,
            -item.samples,
            item.model_id,
        )
    )
    return candidates


def select_unstable_candidates(model_stats: Sequence[ModelStats]) -> List[ModelStats]:
    candidates = [
        item
        for item in model_stats
        if item.samples >= MIN_MODEL_SAMPLES
        and (
            item.flip_count >= UNSTABLE_FLIP_MIN
            or item.rate_limited_rate >= UNSTABLE_RATE_LIMITED_RATE_MIN
            or item.ok_rate <= UNSTABLE_OK_RATE_MAX
        )
    ]
    candidates.sort(
        key=lambda item: (
            -item.flip_count,
            -item.rate_limited_rate,
            item.ok_rate,
            item.model_id,
        )
    )
    return candidates


def compute_run_deltas(
    run_labels: Sequence[str],
    model_statuses: Dict[str, List[str]],
) -> Tuple[List[str], List[str]]:
    if len(run_labels) < 2:
        return [], []

    prev_index = len(run_labels) - 2
    curr_index = len(run_labels) - 1

    recovered_models: List[str] = []
    regressed_models: List[str] = []

    for model_id, statuses in model_statuses.items():
        previous_status = statuses[prev_index]
        latest_status = statuses[curr_index]

        if previous_status == STATUS_MISSING or latest_status == STATUS_MISSING:
            continue

        if previous_status != STATUS_OK and latest_status == STATUS_OK:
            recovered_models.append(model_id)
        elif previous_status == STATUS_OK and latest_status != STATUS_OK:
            regressed_models.append(model_id)

    recovered_models.sort()
    regressed_models.sort()
    return recovered_models, regressed_models


def generate_recommendations(
    latest_snapshot: RunSnapshot,
    stable_candidates: Sequence[ModelStats],
    unstable_candidates: Sequence[ModelStats],
) -> List[str]:
    recommendations: List[str] = []

    if latest_snapshot.checked == 0:
        recommendations.append(
            "No sampled models in the latest run. Verify API key and model list endpoint health."
        )
        return recommendations

    if latest_snapshot.rate_limited_rate >= 0.35:
        recommendations.append(
            "High 429 pressure: run with `--concurrency 1 --request-delay-seconds 1.0 --max-retries 3`."
        )
    elif latest_snapshot.rate_limited_rate >= 0.20:
        recommendations.append(
            "Moderate 429 pressure: reduce concurrency or add request delay (0.6s+)."
        )

    if latest_snapshot.fail_rate >= 0.20:
        recommendations.append(
            "Non-429 failures are elevated: increase timeout and inspect provider-specific errors in raw logs."
        )

    if stable_candidates:
        allowlist = ", ".join(f"`{item.model_id}`" for item in stable_candidates[:3])
        recommendations.append(
            f"Prefer stable free models as primary routing candidates: {allowlist}."
        )

    if unstable_candidates:
        watchlist = ", ".join(f"`{item.model_id}`" for item in unstable_candidates[:3])
        recommendations.append(
            f"Treat high-variance models as fallback-only until trend improves: {watchlist}."
        )

    if not recommendations:
        recommendations.append("Current trend is healthy. Keep the existing scan profile.")

    return recommendations
