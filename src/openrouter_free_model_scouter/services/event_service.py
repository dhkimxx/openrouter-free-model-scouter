from __future__ import annotations

import json
from datetime import timedelta
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from ..config import AppConfig
from ..models import HealthCheck, ModelEvent, Run, RunMetadata
from ..time_utils import format_utc_datetime, utc_now

IMPORTANT_EVENT_TYPES = {"MODEL_ADDED", "MODEL_REMOVED"}
HEALTH_EVENT_TYPES = {
    "MODEL_DEGRADED",
    "MODEL_RECOVERED",
    "MODEL_RATE_LIMITED",
    "MODEL_FLAPPING",
}
EVENT_RETENTION_DAYS = 30
RATE_LIMIT_RATIO_THRESHOLD = 0.30
RATE_LIMIT_MIN_SAMPLES = 3
FLAPPING_CHANGE_THRESHOLD = 5


class EventService:
    def __init__(self, db: Session):
        self.db = db

    def record_events_for_run(self, run_id: int, config: AppConfig) -> None:
        run = self.db.query(Run).filter(Run.id == run_id).first()
        if run is None:
            return

        self._delete_expired_events()
        current_scope_key = build_scan_scope_key(config)
        self._upsert_run_metadata(run_id, config, current_scope_key)

        previous_meta = (
            self.db.query(RunMetadata)
            .filter(RunMetadata.run_id != run_id)
            .filter(RunMetadata.scan_scope_key == current_scope_key)
            .order_by(RunMetadata.run_id.desc())
            .first()
        )

        current_statuses = self._status_map_for_run(run_id)
        if previous_meta is not None:
            previous_statuses = self._status_map_for_run(previous_meta.run_id)
            self._record_model_list_events(
                run=run,
                previous_run_id=previous_meta.run_id,
                current_models=set(current_statuses.keys()),
                previous_models=set(previous_statuses.keys()),
                scope_key=current_scope_key,
            )

        self._record_health_events(run=run, current_statuses=current_statuses)
        self.db.commit()

    def list_events(
        self,
        *,
        event_group: str = "important",
        period: str = "30d",
        limit: int = 5,
        offset: int = 0,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)

        query = self.db.query(ModelEvent)
        if event_group == "important":
            query = query.filter(ModelEvent.event_type.in_(IMPORTANT_EVENT_TYPES))
        elif event_group == "health":
            query = query.filter(ModelEvent.event_type.in_(HEALTH_EVENT_TYPES))

        if model_id:
            query = query.filter(ModelEvent.model_id == model_id)

        since = self._since_for_period(period)
        if since is not None:
            query = query.filter(ModelEvent.event_datetime >= since)

        total_window = query.order_by(ModelEvent.id.desc()).offset(offset).limit(limit + 1).all()
        items = total_window[:limit]

        return {
            "items": [self._event_to_dict(item) for item in items],
            "has_more": len(total_window) > limit,
            "next_offset": offset + len(items),
        }

    def _delete_expired_events(self) -> None:
        cutoff = format_utc_datetime(utc_now() - timedelta(days=EVENT_RETENTION_DAYS))
        self.db.query(ModelEvent).filter(ModelEvent.event_datetime < cutoff).delete()

    def _upsert_run_metadata(
        self, run_id: int, config: AppConfig, scan_scope_key: str
    ) -> None:
        existing = self.db.query(RunMetadata).filter(RunMetadata.run_id == run_id).first()
        model_id_contains = json.dumps(sorted(config.model_id_contains))
        if existing is None:
            self.db.add(
                RunMetadata(
                    run_id=run_id,
                    scan_scope_key=scan_scope_key,
                    model_id_contains=model_id_contains,
                    max_models=config.max_models,
                )
            )
            return

        existing.scan_scope_key = scan_scope_key
        existing.model_id_contains = model_id_contains
        existing.max_models = config.max_models

    def _record_model_list_events(
        self,
        *,
        run: Run,
        previous_run_id: int,
        current_models: set[str],
        previous_models: set[str],
        scope_key: str,
    ) -> None:
        for model_id in sorted(current_models - previous_models):
            self._add_event(
                run=run,
                previous_run_id=previous_run_id,
                event_type="MODEL_ADDED",
                severity="high",
                model_id=model_id,
                old_value=None,
                new_value="present",
                message="Added to OpenRouter free model list",
                metadata={"scan_scope_key": scope_key},
            )

        for model_id in sorted(previous_models - current_models):
            self._add_event(
                run=run,
                previous_run_id=previous_run_id,
                event_type="MODEL_REMOVED",
                severity="high",
                model_id=model_id,
                old_value="present",
                new_value=None,
                message="Removed from latest comparable free-model scan",
                metadata={"scan_scope_key": scope_key},
            )

    def _record_health_events(
        self, *, run: Run, current_statuses: Dict[str, str]
    ) -> None:
        since_24h = format_utc_datetime(utc_now() - timedelta(days=1))
        for model_id in sorted(current_statuses.keys()):
            recent_latest_first = self._recent_statuses(model_id, limit=8)
            if len(recent_latest_first) >= 4:
                first_three = recent_latest_first[:3]
                prior = recent_latest_first[3]
                if all(not _is_ok(status) for status in first_three) and _is_ok(prior):
                    self._add_event(
                        run=run,
                        previous_run_id=None,
                        event_type="MODEL_DEGRADED",
                        severity="medium",
                        model_id=model_id,
                        old_value=prior,
                        new_value=first_three[0],
                        message="3 consecutive non-OK checks",
                        metadata={"recent_statuses": first_three},
                    )

            if len(recent_latest_first) >= 3:
                first_two = recent_latest_first[:2]
                prior = recent_latest_first[2]
                if all(_is_ok(status) for status in first_two) and not _is_ok(prior):
                    self._add_event(
                        run=run,
                        previous_run_id=None,
                        event_type="MODEL_RECOVERED",
                        severity="medium",
                        model_id=model_id,
                        old_value=prior,
                        new_value=first_two[0],
                        message="2 consecutive OK checks after a non-OK state",
                        metadata={"recent_statuses": first_two},
                    )

            recent_24h = self._recent_statuses_since(model_id, since_24h)
            if len(recent_24h) >= RATE_LIMIT_MIN_SAMPLES:
                current_ratio = _ratio(recent_24h, "429")
                previous_ratio = _ratio(recent_24h[:-1], "429")
                if (
                    current_ratio >= RATE_LIMIT_RATIO_THRESHOLD
                    and previous_ratio < RATE_LIMIT_RATIO_THRESHOLD
                ):
                    self._add_event(
                        run=run,
                        previous_run_id=None,
                        event_type="MODEL_RATE_LIMITED",
                        severity="medium",
                        model_id=model_id,
                        old_value=None,
                        new_value="429",
                        message="429 ratio reached 30% over the last 24 hours",
                        metadata={
                            "ratio": round(current_ratio, 3),
                            "samples": len(recent_24h),
                        },
                    )

                current_changes = _status_changes(recent_24h)
                previous_changes = _status_changes(recent_24h[:-1])
                if (
                    current_changes >= FLAPPING_CHANGE_THRESHOLD
                    and previous_changes < FLAPPING_CHANGE_THRESHOLD
                ):
                    self._add_event(
                        run=run,
                        previous_run_id=None,
                        event_type="MODEL_FLAPPING",
                        severity="low",
                        model_id=model_id,
                        old_value=None,
                        new_value=str(current_changes),
                        message="5 or more status changes over the last 24 hours",
                        metadata={
                            "status_changes": current_changes,
                            "samples": len(recent_24h),
                        },
                    )

    def _add_event(
        self,
        *,
        run: Run,
        previous_run_id: Optional[int],
        event_type: str,
        severity: str,
        model_id: str,
        old_value: Optional[str],
        new_value: Optional[str],
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        fingerprint = ":".join([event_type, str(previous_run_id or ""), str(run.id), model_id])
        exists = (
            self.db.query(ModelEvent)
            .filter(ModelEvent.fingerprint == fingerprint)
            .first()
        )
        if exists is not None:
            return

        self.db.add(
            ModelEvent(
                run_id=run.id,
                previous_run_id=previous_run_id,
                event_datetime=run.run_datetime,
                event_type=event_type,
                severity=severity,
                model_id=model_id,
                old_value=old_value,
                new_value=new_value,
                message=message,
                metadata_json=json.dumps(metadata or {}, sort_keys=True),
                fingerprint=fingerprint,
            )
        )

    def _status_map_for_run(self, run_id: int) -> Dict[str, str]:
        checks = self.db.query(HealthCheck).filter(HealthCheck.run_id == run_id).all()
        return {check.model_id: status_label(check) for check in checks}

    def _recent_statuses(self, model_id: str, *, limit: int) -> List[str]:
        checks = (
            self.db.query(HealthCheck)
            .filter(HealthCheck.model_id == model_id)
            .order_by(HealthCheck.run_id.desc())
            .limit(limit)
            .all()
        )
        return [status_label(check) for check in checks]

    def _recent_statuses_since(self, model_id: str, since: str) -> List[str]:
        rows = (
            self.db.query(HealthCheck)
            .join(Run, Run.id == HealthCheck.run_id)
            .filter(HealthCheck.model_id == model_id)
            .filter(Run.run_datetime >= since)
            .order_by(Run.id.asc())
            .all()
        )
        return [status_label(check) for check in rows]

    def _since_for_period(self, period: str) -> Optional[str]:
        if period == "all":
            return None
        if period == "7d":
            delta = timedelta(days=7)
        elif period == "1d":
            delta = timedelta(days=1)
        else:
            delta = timedelta(days=EVENT_RETENTION_DAYS)
        return format_utc_datetime(utc_now() - delta)

    def _event_to_dict(self, event: ModelEvent) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        if event.metadata_json:
            try:
                parsed = json.loads(event.metadata_json)
                if isinstance(parsed, dict):
                    metadata = parsed
            except json.JSONDecodeError:
                metadata = {}

        return {
            "id": event.id,
            "run_id": event.run_id,
            "previous_run_id": event.previous_run_id,
            "event_datetime": event.event_datetime,
            "event_type": event.event_type,
            "severity": event.severity,
            "model_id": event.model_id,
            "old_value": event.old_value,
            "new_value": event.new_value,
            "message": event.message,
            "metadata": metadata,
        }


def build_scan_scope_key(config: AppConfig) -> str:
    contains = ",".join(sorted(token.lower() for token in config.model_id_contains))
    max_models = "all" if config.max_models is None else str(config.max_models)
    return f"contains={contains}|max_models={max_models}"


def status_label(check: HealthCheck) -> str:
    if check.ok:
        return "OK"
    if check.http_status == 429 or check.error_category == "rate_limited":
        return "429"
    if check.http_status is not None:
        return f"HTTP {check.http_status}"
    if check.error_category:
        return check.error_category
    return "FAIL"


def _is_ok(status: str) -> bool:
    return status == "OK"


def _ratio(values: Sequence[str], target: str) -> float:
    if not values:
        return 0.0
    return sum(1 for value in values if value == target) / len(values)


def _status_changes(values: Sequence[str]) -> int:
    if len(values) < 2:
        return 0
    return sum(1 for previous, current in zip(values, values[1:]) if previous != current)
