from __future__ import annotations

from typing import Iterable, List


def safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def to_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def truncate_models(models: Iterable[str], limit: int = 10) -> str:
    values: List[str] = list(models)
    if not values:
        return "none"

    if len(values) <= limit:
        return ", ".join(f"`{item}`" for item in values)

    shown = ", ".join(f"`{item}`" for item in values[:limit])
    return f"{shown} (+{len(values) - limit} more)"
