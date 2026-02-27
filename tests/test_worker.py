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
    worker.catalog_service.get_free_models = MagicMock(
        return_value=[{"id": "model-a", "pricing": {"prompt": "0", "completion": "0"}}]
    )
    worker.healthcheck_service.check_models = MagicMock(
        return_value=[
            HealthcheckResult(
                run_id="1",
                timestamp_iso="2023",
                model_id="model-a",
                ok=True,
                http_status=200,
                latency_ms=123,
                attempts=1,
                error_category=None,
                error_message=None,
                response_preview="OK",
            )
        ]
    )

    config = AppConfig.from_sources(cli_overrides={"api_key": "test"}, env={})

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


def test_worker_scan_errors(db):
    mock_client = MagicMock()
    worker = ScouterWorker(db, mock_client)

    worker.catalog_service.get_free_models = MagicMock(
        return_value=[
            {"id": "model-429", "pricing": {"prompt": "0", "completion": "0"}},
            {"id": "model-500", "pricing": {"prompt": "0", "completion": "0"}},
        ]
    )
    worker.healthcheck_service.check_models = MagicMock(
        return_value=[
            HealthcheckResult(
                run_id="1",
                timestamp_iso="2023",
                model_id="model-429",
                ok=False,
                http_status=429,
                latency_ms=None,
                attempts=1,
                error_category="rate_limited",
                error_message="Too Many Requests",
                response_preview=None,
            ),
            HealthcheckResult(
                run_id="1",
                timestamp_iso="2023",
                model_id="model-500",
                ok=False,
                http_status=500,
                latency_ms=None,
                attempts=1,
                error_category="server_error",
                error_message="Internal Server Error",
                response_preview=None,
            ),
        ]
    )

    config = AppConfig.from_sources(cli_overrides={"api_key": "test"}, env={})
    run_id, results = worker.run_scan(config)

    assert len(results) == 2

    checks = db.query(HealthCheck).all()
    assert len(checks) == 2  # Fixture provides a clean DB context per test

    # Just filter by run_id
    checks = db.query(HealthCheck).filter(HealthCheck.run_id == run_id).all()
    assert len(checks) == 2

    check_429 = next(c for c in checks if c.model_id == "model-429")
    assert check_429.ok is False
    assert check_429.http_status == 429
    assert check_429.error_category == "rate_limited"

    check_500 = next(c for c in checks if c.model_id == "model-500")
    assert check_500.ok is False
    assert check_500.http_status == 500
    assert check_500.error_category == "server_error"
