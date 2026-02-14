from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Sequence

from .models import ModelStats, RunSnapshot
from .utils import to_percent, truncate_models


def format_run_table(snapshots: Sequence[RunSnapshot]) -> List[str]:
    lines = [
        "| Run | Checked | OK | 429 | FAIL | OK % | 429 % | FAIL % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for snapshot in snapshots:
        lines.append(
            "| {label} | {checked} | {ok} | {rate_limited} | {failed} | {ok_rate} | {rl_rate} | {fail_rate} |".format(
                label=snapshot.label,
                checked=snapshot.checked,
                ok=snapshot.ok,
                rate_limited=snapshot.rate_limited,
                failed=snapshot.failed,
                ok_rate=to_percent(snapshot.ok_rate),
                rl_rate=to_percent(snapshot.rate_limited_rate),
                fail_rate=to_percent(snapshot.fail_rate),
            )
        )

    return lines


def format_model_table(stats: Sequence[ModelStats]) -> List[str]:
    lines = [
        "| Model | Samples | OK % | 429 % | FAIL % | Flips | Latest |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for item in stats:
        lines.append(
            "| `{model_id}` | {samples} | {ok_rate} | {rl_rate} | {fail_rate} | {flip_count} | {latest} |".format(
                model_id=item.model_id,
                samples=item.samples,
                ok_rate=to_percent(item.ok_rate),
                rl_rate=to_percent(item.rate_limited_rate),
                fail_rate=to_percent(item.fail_rate),
                flip_count=item.flip_count,
                latest=item.latest_status,
            )
        )

    return lines


def render_report(
    *,
    xlsx_path: Path,
    selected_labels: Sequence[str],
    snapshots: Sequence[RunSnapshot],
    latest_snapshot: RunSnapshot,
    previous_snapshot: Optional[RunSnapshot],
    stable_candidates: Sequence[ModelStats],
    unstable_candidates: Sequence[ModelStats],
    recovered_models: Sequence[str],
    regressed_models: Sequence[str],
    recommendations: Sequence[str],
    top_n: int,
) -> str:
    timestamp_text = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines: List[str] = []
    lines.append("# OpenRouter Free Model Availability Report")
    lines.append("")
    lines.append(f"Generated at: {timestamp_text}")
    lines.append(f"Source workbook: `{xlsx_path}`")
    lines.append(
        f"Runs analyzed: {len(selected_labels)} (from {selected_labels[0]} to {selected_labels[-1]})"
    )
    lines.append("")

    lines.append("## Latest Run Snapshot")
    lines.append("")
    lines.append(f"- Run: `{latest_snapshot.label}`")
    lines.append(f"- Checked models: {latest_snapshot.checked}")
    lines.append(f"- OK: {latest_snapshot.ok} ({to_percent(latest_snapshot.ok_rate)})")
    lines.append(
        f"- 429: {latest_snapshot.rate_limited} ({to_percent(latest_snapshot.rate_limited_rate)})"
    )
    lines.append(
        f"- FAIL: {latest_snapshot.failed} ({to_percent(latest_snapshot.fail_rate)})"
    )
    lines.append("")

    lines.append("## Delta vs Previous Run")
    lines.append("")
    if previous_snapshot is None:
        lines.append("- Not enough history to compute deltas (need at least 2 runs).")
    else:
        lines.append(
            "- OK rate delta: {delta:+.1f}pp".format(
                delta=(latest_snapshot.ok_rate - previous_snapshot.ok_rate) * 100
            )
        )
        lines.append(
            "- 429 rate delta: {delta:+.1f}pp".format(
                delta=(latest_snapshot.rate_limited_rate - previous_snapshot.rate_limited_rate)
                * 100
            )
        )
        lines.append(f"- Recovered models: {truncate_models(recovered_models)}")
        lines.append(f"- Regressed models: {truncate_models(regressed_models)}")
    lines.append("")

    lines.append("## Multi-run Trend")
    lines.append("")
    lines.extend(format_run_table(snapshots))
    lines.append("")

    lines.append("## Stable Candidate Models")
    lines.append("")
    if stable_candidates:
        lines.extend(format_model_table(stable_candidates[:top_n]))
    else:
        lines.append("No stable candidates yet (collect more runs or reduce 429 pressure).")
    lines.append("")

    lines.append("## Unstable Models / 429 Risk")
    lines.append("")
    if unstable_candidates:
        lines.extend(format_model_table(unstable_candidates[:top_n]))
    else:
        lines.append("No high-variance models detected in the selected window.")
    lines.append("")

    lines.append("## Recommended Actions")
    lines.append("")
    for index, recommendation in enumerate(recommendations, start=1):
        lines.append(f"{index}. {recommendation}")

    return "\n".join(lines).rstrip() + "\n"
