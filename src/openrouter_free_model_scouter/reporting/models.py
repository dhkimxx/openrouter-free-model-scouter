from __future__ import annotations

from dataclasses import dataclass

from .utils import safe_ratio


@dataclass(frozen=True)
class RunSnapshot:
    label: str
    checked: int
    ok: int
    rate_limited: int
    failed: int

    @property
    def ok_rate(self) -> float:
        return safe_ratio(self.ok, self.checked)

    @property
    def rate_limited_rate(self) -> float:
        return safe_ratio(self.rate_limited, self.checked)

    @property
    def fail_rate(self) -> float:
        return safe_ratio(self.failed, self.checked)


@dataclass(frozen=True)
class ModelStats:
    model_id: str
    samples: int
    ok_count: int
    rate_limited_count: int
    fail_count: int
    flip_count: int
    latest_status: str

    @property
    def ok_rate(self) -> float:
        return safe_ratio(self.ok_count, self.samples)

    @property
    def rate_limited_rate(self) -> float:
        return safe_ratio(self.rate_limited_count, self.samples)

    @property
    def fail_rate(self) -> float:
        return safe_ratio(self.fail_count, self.samples)
