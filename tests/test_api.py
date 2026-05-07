from openrouter_free_model_scouter.models import HealthCheck, ModelEvent, Run
from datetime import datetime, timezone

def test_get_summary_empty(client):
    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_models"] == 0

def test_get_summary_with_data(client, db):
    run1 = Run(run_datetime="2023-01-01T10:00:00Z")
    db.add(run1)
    db.commit()
    check1 = HealthCheck(run_id=run1.id, model_id="model-a", ok=True, latency_ms=100)
    db.add(check1)
    db.commit()

    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_models"] == 1
    assert data["healthy_count"] == 1

def test_get_models(client, db):
    run1 = Run(run_datetime="2023-01-01T10:00:00Z")
    db.add(run1)
    db.commit()
    check1 = HealthCheck(run_id=run1.id, model_id="model-a", ok=True, latency_ms=100)
    db.add(check1)
    db.commit()

    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["model_id"] == "model-a"

def test_get_model_history(client, db):
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run1 = Run(run_datetime=now_str)
    db.add(run1)
    db.commit()
    check1 = HealthCheck(run_id=run1.id, model_id="google/gemma", ok=True, latency_ms=100)
    db.add(check1)
    db.commit()

    # Test with slashed model_id
    response = client.get("/api/models/google/gemma/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["ok"] is True


def test_get_events_filters_important(client, db):
    run1 = Run(run_datetime=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    db.add(run1)
    db.commit()
    db.add_all(
        [
            ModelEvent(
                run_id=run1.id,
                previous_run_id=None,
                event_datetime=run1.run_datetime,
                event_type="MODEL_ADDED",
                severity="high",
                model_id="model-important",
                old_value=None,
                new_value="present",
                message="Added to OpenRouter free model list",
                metadata_json="{}",
                fingerprint="test-important",
            ),
            ModelEvent(
                run_id=run1.id,
                previous_run_id=None,
                event_datetime=run1.run_datetime,
                event_type="MODEL_DEGRADED",
                severity="medium",
                model_id="model-health",
                old_value="OK",
                new_value="429",
                message="3 consecutive non-OK checks",
                metadata_json="{}",
                fingerprint="test-health",
            ),
        ]
    )
    db.commit()

    response = client.get("/api/events?type=important&limit=5")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["event_type"] == "MODEL_ADDED"
    assert data["items"][0]["model_id"] == "model-important"
