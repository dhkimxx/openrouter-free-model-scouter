from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from ..models import Run, HealthCheck

class StatsService:
    def __init__(self, db: Session):
        self.db = db

    def get_latest_run(self) -> Optional[Run]:
        return self.db.query(Run).order_by(Run.id.desc()).first()

    def get_summary(self) -> Dict:
        latest_run = self.get_latest_run()
        if not latest_run:
            return {
                "total_models": 0,
                "healthy_count": 0,
                "degraded_count": 0,
                "down_count": 0,
                "last_updated": None
            }

        checks = self.db.query(HealthCheck).filter(HealthCheck.run_id == latest_run.id).all()
        total_models = len(checks)

        # Simple heuristic for now: OK -> healthy, others -> down
        # Ideally, we should look at history for degraded
        healthy_count = sum(1 for c in checks if c.ok)
        down_count = total_models - healthy_count

        return {
            "total_models": total_models,
            "healthy_count": healthy_count,
            "degraded_count": 0, # Placeholder
            "down_count": down_count,
            "last_updated": latest_run.run_datetime
        }

    def get_model_history(self, model_id: str, limit: int = 50) -> List[Dict]:
        query = (
            self.db.query(Run.run_datetime, HealthCheck.ok, HealthCheck.latency_ms, HealthCheck.http_status, HealthCheck.error_category)
            .join(HealthCheck, Run.id == HealthCheck.run_id)
            .filter(HealthCheck.model_id == model_id)
            .order_by(Run.id.desc())
            .limit(limit)
        )
        results = query.all()

        history = []
        for run_datetime, ok, latency, http_status, error_category in reversed(results):
            status_label = "OK"
            if not ok:
                if http_status == 429 or error_category == "rate_limited":
                    status_label = "429"
                elif http_status:
                    status_label = f"HTTP {http_status}"
                else:
                    status_label = "FAIL"

            history.append({
                "run_datetime": run_datetime,
                "ok": ok,
                "latency_ms": latency,
                "status_label": status_label
            })
        return history

    def get_models_stats(self, lookback_hours: int = 24) -> List[Dict]:
        # Get all distinct models from the latest run first
        latest_run = self.get_latest_run()
        if not latest_run:
            return []

        latest_checks = {c.model_id: c for c in self.db.query(HealthCheck).filter(HealthCheck.run_id == latest_run.id).all()}
        model_ids = list(latest_checks.keys())

        # For stats, we need history.
        # Since we don't have easy date parsing in SQLite for complex queries without extensions,
        # we'll fetch last N runs that cover approximately lookback_hours.
        # Assuming 1 run per hour, we fetch 24 runs.
        # But runs can be frequent. Let's just fetch last 100 runs and filter in python if needed,
        # or just use last 50 runs for stats.

        # Let's fetch the last 100 runs.
        runs = self.db.query(Run).order_by(Run.id.desc()).limit(100).all()
        if not runs:
            return []

        run_ids = [r.id for r in runs]

        checks = (
            self.db.query(HealthCheck)
            .filter(HealthCheck.run_id.in_(run_ids))
            .filter(HealthCheck.model_id.in_(model_ids))
            .all()
        )

        # Group by model
        model_checks = {mid: [] for mid in model_ids}
        for c in checks:
            if c.model_id in model_checks:
                model_checks[c.model_id].append(c)

        # Sort checks by run_id desc (latest first)
        for mid in model_checks:
            model_checks[mid].sort(key=lambda x: x.run_id, reverse=True)

        stats = []
        for mid, m_checks in model_checks.items():
            if not m_checks:
                continue

            total_attempts = len(m_checks)
            success_count = sum(1 for c in m_checks if c.ok)
            uptime = (success_count / total_attempts) * 100 if total_attempts > 0 else 0.0

            latencies = [c.latency_ms for c in m_checks if c.ok and c.latency_ms is not None]
            avg_latency = sum(latencies) / len(latencies) if latencies else None

            # Consecutive failures from latest
            consecutive_failures = 0
            for c in m_checks: # already sorted latest first
                if not c.ok:
                    consecutive_failures += 1
                else:
                    break

            latest_c = latest_checks.get(mid)
            latest_status = "OK"
            if latest_c:
                if not latest_c.ok:
                    if latest_c.http_status == 429:
                        latest_status = "429"
                    elif latest_c.http_status:
                        latest_status = f"HTTP {latest_c.http_status}"
                    else:
                        latest_status = "FAIL"
            else:
                 latest_status = "MISS"

            stats.append({
                "model_id": mid,
                "uptime_24h": uptime,
                "avg_latency_24h": avg_latency,
                "consecutive_failures": consecutive_failures,
                "latest_status": latest_status
            })

        return stats
