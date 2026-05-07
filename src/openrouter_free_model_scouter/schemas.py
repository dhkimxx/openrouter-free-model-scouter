from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional


class RunSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_datetime: str


class HealthCheckSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    model_id: str
    ok: bool
    http_status: Optional[int] = None
    error_category: Optional[str] = None
    latency_ms: Optional[int] = None


class ModelStats(BaseModel):
    model_id: str
    uptime_24h: float
    avg_latency_24h: Optional[float]
    consecutive_failures: int
    latest_status: str  # e.g., "OK", "FAIL", "429"
    sparkline_data: List[Optional[int]] = []


class ModelHistoryPoint(BaseModel):
    run_datetime: str
    ok: bool
    latency_ms: Optional[int]
    status_label: str


class Summary(BaseModel):
    total_models: int
    healthy_count: int
    degraded_count: int
    down_count: int
    last_updated: Optional[str]


class EventItem(BaseModel):
    id: int
    run_id: int
    previous_run_id: Optional[int]
    event_datetime: str
    event_type: str
    severity: str
    model_id: str
    old_value: Optional[str]
    new_value: Optional[str]
    message: str
    metadata: dict = Field(default_factory=dict)


class EventList(BaseModel):
    items: List[EventItem]
    has_more: bool
    next_offset: int
