from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class ModelInfo:
    model_id: str
    name: str
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    headers: Mapping[str, str]
    body_text: str
    json_body: Optional[Mapping[str, Any]]


@dataclass(frozen=True)
class HealthcheckResult:
    run_id: str
    timestamp_iso: str
    model_id: str
    ok: bool
    http_status: Optional[int]
    latency_ms: Optional[int]
    attempts: int
    error_category: Optional[str]
    error_message: Optional[str]
    response_preview: Optional[str]
