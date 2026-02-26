from openrouter_free_model_scouter.models import Run, HealthCheck

def test_get_summary_empty(client):
    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_models"] == 0

def test_get_summary_with_data(client, db):
    run1 = Run(run_datetime="2023-01-01 10:00:00")
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
    run1 = Run(run_datetime="2023-01-01 10:00:00")
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
    run1 = Run(run_datetime="2023-01-01 10:00:00")
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
