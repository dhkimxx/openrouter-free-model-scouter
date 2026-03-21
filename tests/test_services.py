from openrouter_free_model_scouter.services.stats_service import StatsService
from openrouter_free_model_scouter.models import Run, HealthCheck
from datetime import datetime

def test_stats_service_empty(db):
    service = StatsService(db)
    summary = service.get_summary()
    assert summary["total_models"] == 0

def test_stats_service_basic(db):
    # Setup data
    run1 = Run(run_datetime="2023-01-01T10:00:00Z")
    db.add(run1)
    db.commit()

    check1 = HealthCheck(run_id=run1.id, model_id="model-a", ok=True, latency_ms=100)
    check2 = HealthCheck(run_id=run1.id, model_id="model-b", ok=False, http_status=429)
    db.add_all([check1, check2])
    db.commit()

    service = StatsService(db)
    summary = service.get_summary()
    assert summary["total_models"] == 2
    assert summary["healthy_count"] == 1
    assert summary["down_count"] == 1

    stats = service.get_models_stats()
    assert len(stats) == 2

    model_a = next(m for m in stats if m["model_id"] == "model-a")
    assert model_a["uptime_24h"] == 100.0
    assert model_a["latest_status"] == "OK"

    model_b = next(m for m in stats if m["model_id"] == "model-b")
    assert model_b["uptime_24h"] == 0.0
    assert model_b["latest_status"] == "429"

def test_history(db):
    from datetime import datetime, timedelta
    now = datetime.now()
    r1_dt = (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    r2_dt = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    run1 = Run(run_datetime=r1_dt)
    run2 = Run(run_datetime=r2_dt)
    db.add_all([run1, run2])
    db.commit()

    check1 = HealthCheck(run_id=run1.id, model_id="model-a", ok=True, latency_ms=100)
    check2 = HealthCheck(run_id=run2.id, model_id="model-a", ok=False, http_status=500)
    db.add_all([check1, check2])
    db.commit()

    service = StatsService(db)
    history = service.get_model_history("model-a", period="1d")
    assert len(history) == 2
    
    # Oldest first in results after processing
    assert history[0]["run_datetime"] == r1_dt
    assert history[0]["ok"] is True

    assert history[1]["run_datetime"] == r2_dt
    assert history[1]["ok"] is False
    assert history[1]["status_label"] == "HTTP 500"

def test_history_periods(db):
    from datetime import datetime, timedelta
    now = datetime.now()
    
    # 2 days ago (should be in 1w, not in 1d)
    r_old_dt = (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    # 1 hour ago (should be in both)
    r_new_dt = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    run_old = Run(run_datetime=r_old_dt)
    run_new = Run(run_datetime=r_new_dt)
    db.add_all([run_old, run_new])
    db.commit()

    db.add(HealthCheck(run_id=run_old.id, model_id="model-p", ok=True))
    db.add(HealthCheck(run_id=run_new.id, model_id="model-p", ok=True))
    db.commit()

    service = StatsService(db)
    
    # Check 1d
    history_1d = service.get_model_history("model-p", period="1d")
    assert len(history_1d) == 1
    assert history_1d[0]["run_datetime"] == r_new_dt

    # Check 1w
    history_1w = service.get_model_history("model-p", period="1w")
    assert len(history_1w) == 2
