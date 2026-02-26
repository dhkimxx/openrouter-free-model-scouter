from unittest.mock import MagicMock
from openrouter_free_model_scouter.worker.scouter import ScouterWorker
from openrouter_free_model_scouter.config import AppConfig
from openrouter_free_model_scouter.domain_models import HealthcheckResult
from openrouter_free_model_scouter.models import Run, HealthCheck

def test_worker_scan(db):
    mock_client = MagicMock()

    # Instantiate worker
    worker = ScouterWorker(db, mock_client)

    # Mock services on the worker instance
    worker.catalog_service.get_free_models = MagicMock(return_value=[
        {"id": "model-a", "pricing": {"prompt": "0", "completion": "0"}}
    ])
    worker.healthcheck_service.check_models = MagicMock(return_value=[
        HealthcheckResult(
            run_id="1", timestamp_iso="2023", model_id="model-a", ok=True,
            http_status=200, latency_ms=123, attempts=1, error_category=None, error_message=None, response_preview="OK"
        )
    ])

    config = AppConfig.from_sources(
        cli_overrides={"api_key": "test"},
        env={}
    )

    run_id, results = worker.run_scan(config)

    assert run_id is not None
    assert len(results) == 1
    assert results[0].ok is True

    # Verify DB
    run = db.query(Run).first()
    assert run is not None
    checks = db.query(HealthCheck).all()
    assert len(checks) == 1
    assert checks[0].model_id == "model-a"
    assert checks[0].latency_ms == 123
