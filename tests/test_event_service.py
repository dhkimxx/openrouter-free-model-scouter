from openrouter_free_model_scouter.config import AppConfig
from openrouter_free_model_scouter.models import HealthCheck, ModelEvent, Run, RunMetadata
from openrouter_free_model_scouter.services.event_service import EventService, build_scan_scope_key


def _add_run(db, run_datetime: str) -> Run:
    run = Run(run_datetime=run_datetime)
    db.add(run)
    db.commit()
    return run


def _add_check(
    db,
    run_id: int,
    model_id: str,
    *,
    ok: bool,
    http_status: int | None = None,
    error_category: str | None = None,
) -> None:
    db.add(
        HealthCheck(
            run_id=run_id,
            model_id=model_id,
            ok=ok,
            http_status=http_status,
            error_category=error_category,
        )
    )
    db.commit()


def test_records_added_and_removed_for_comparable_scope(db):
    config = AppConfig.from_sources(cli_overrides={"api_key": "test"}, env={})
    scope_key = build_scan_scope_key(config)

    previous = _add_run(db, "2026-05-07T00:00:00Z")
    db.add(
        RunMetadata(
            run_id=previous.id,
            scan_scope_key=scope_key,
            model_id_contains="[]",
            max_models=None,
        )
    )
    _add_check(db, previous.id, "model-removed", ok=True)
    _add_check(db, previous.id, "model-stable", ok=True)

    current = _add_run(db, "2026-05-07T01:00:00Z")
    _add_check(db, current.id, "model-added", ok=True)
    _add_check(db, current.id, "model-stable", ok=True)

    EventService(db).record_events_for_run(current.id, config)

    events = db.query(ModelEvent).order_by(ModelEvent.event_type).all()
    assert [(event.event_type, event.model_id) for event in events] == [
        ("MODEL_ADDED", "model-added"),
        ("MODEL_REMOVED", "model-removed"),
    ]
    assert all(event.severity == "high" for event in events)


def test_skips_added_removed_when_previous_scope_differs(db):
    config = AppConfig.from_sources(cli_overrides={"api_key": "test"}, env={})

    previous = _add_run(db, "2026-05-07T00:00:00Z")
    db.add(
        RunMetadata(
            run_id=previous.id,
            scan_scope_key="different-scope",
            model_id_contains='["google"]',
            max_models=None,
        )
    )
    _add_check(db, previous.id, "model-removed", ok=True)

    current = _add_run(db, "2026-05-07T01:00:00Z")
    _add_check(db, current.id, "model-added", ok=True)

    EventService(db).record_events_for_run(current.id, config)

    assert db.query(ModelEvent).count() == 0


def test_records_degraded_health_event(db):
    config = AppConfig.from_sources(cli_overrides={"api_key": "test"}, env={})
    statuses = [
        ("2026-05-07T00:00:00Z", True, None, None),
        ("2026-05-07T01:00:00Z", False, 500, "server_error"),
        ("2026-05-07T02:00:00Z", False, 429, "rate_limited"),
        ("2026-05-07T03:00:00Z", False, 500, "server_error"),
    ]
    current_run = None
    for run_datetime, ok, http_status, error_category in statuses:
        current_run = _add_run(db, run_datetime)
        _add_check(
            db,
            current_run.id,
            "model-a",
            ok=ok,
            http_status=http_status,
            error_category=error_category,
        )

    EventService(db).record_events_for_run(current_run.id, config)

    event = db.query(ModelEvent).one()
    assert event.event_type == "MODEL_DEGRADED"
    assert event.model_id == "model-a"
    assert event.severity == "medium"
