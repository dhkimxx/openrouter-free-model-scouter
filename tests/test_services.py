from openrouter_free_model_scouter.services.stats_service import StatsService
from openrouter_free_model_scouter.models import Run, HealthCheck
from datetime import datetime

def test_stats_service_empty(db):
    service = StatsService(db)
    summary = service.get_summary()
    assert summary["total_models"] == 0

def test_stats_service_basic(db):
    # Setup data
    run1 = Run(run_datetime="2023-01-01 10:00:00")
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
    run1 = Run(run_datetime="2023-01-01 10:00:00")
    run2 = Run(run_datetime="2023-01-01 11:00:00")
    db.add_all([run1, run2])
    db.commit()

    check1 = HealthCheck(run_id=run1.id, model_id="model-a", ok=True, latency_ms=100)
    check2 = HealthCheck(run_id=run2.id, model_id="model-a", ok=False, http_status=500)
    db.add_all([check1, check2])
    db.commit()

    service = StatsService(db)
    history = service.get_model_history("model-a")
    assert len(history) == 2
    # Oldest first?
    # StatsService code: "for ... in reversed(results)" where results are order_by(Run.id.desc())
    # results = [run2_check, run1_check]
    # reversed -> [run1_check, run2_check] (Oldest first)

    assert history[0]["run_datetime"] == "2023-01-01 10:00:00"
    assert history[0]["ok"] is True

    assert history[1]["run_datetime"] == "2023-01-01 11:00:00"
    assert history[1]["ok"] is False
    assert history[1]["status_label"] == "HTTP 500"
