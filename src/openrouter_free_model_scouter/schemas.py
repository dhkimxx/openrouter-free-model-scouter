from pydantic import BaseModel
from typing import List, Optional

class RunSchema(BaseModel):
    id: int
    run_datetime: str

    class Config:
        from_attributes = True

class HealthCheckSchema(BaseModel):
    id: int
    run_id: int
    model_id: str
    ok: bool
    http_status: Optional[int] = None
    error_category: Optional[str] = None
    latency_ms: Optional[int] = None

    class Config:
        from_attributes = True

class ModelStats(BaseModel):
    model_id: str
    uptime_24h: float
    avg_latency_24h: Optional[float]
    consecutive_failures: int
    latest_status: str  # e.g., "OK", "FAIL", "429"

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
