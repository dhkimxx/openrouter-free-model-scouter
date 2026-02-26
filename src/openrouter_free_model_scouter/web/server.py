from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..sqlite_repository import SqliteTimelineRepository

_HERE = Path(__file__).parent

app = FastAPI(title="OpenRouter Free Model Scouter")
templates = Jinja2Templates(directory=str(_HERE / "templates"))

# Mount static files
_static_dir = _HERE / "static"
_static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# Shared state for background scan progress
_scan_state: Dict[str, Any] = {"running": False, "last_run": None, "error": None}


def _get_db_path() -> Path:
    import os
    return Path(os.environ.get("OPENROUTER_SCOUT_DB_PATH", "results/scouter.db"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/status")
async def api_status():
    db_path = _get_db_path()
    if not db_path.exists():
        return JSONResponse({"run_labels": [], "models": [], "scan_state": _scan_state})

    try:
        repo = SqliteTimelineRepository()
        run_labels, model_statuses = repo.read_timeline(db_path)
    except Exception as exc:
        return JSONResponse({"error": str(exc), "scan_state": _scan_state}, status_code=500)

    # Build a list of model objects with their statuses
    models: List[Dict[str, Any]] = []
    for model_id, statuses in model_statuses.items():
        # normalize
        normalized = []
        for s in statuses:
            if not s:
                normalized.append("MISS")
            elif s.startswith("OK"):
                normalized.append("OK")
            elif s == "429":
                normalized.append("429")
            else:
                normalized.append("FAIL")

        ok_count = normalized.count("OK")
        total = len(normalized)
        models.append({
            "model_id": model_id,
            "statuses": statuses,
            "normalized": normalized,
            "ok_rate": round(ok_count / total, 3) if total else 0,
            "latest": statuses[-1] if statuses else "",
        })

    # Sort: first by latest status (OK first), then by ok_rate
    def sort_key(m):
        latest = m["normalized"][-1] if m["normalized"] else ""
        status_order = {"OK": 0, "429": 1, "MISS": 2}.get(latest, 1)
        return (status_order, -m["ok_rate"], m["model_id"])

    models.sort(key=sort_key)

    return JSONResponse({
        "run_labels": run_labels,
        "models": models,
        "scan_state": _scan_state,
    })


@app.post("/api/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    if _scan_state["running"]:
        return JSONResponse({"message": "scan already in progress"}, status_code=409)
    background_tasks.add_task(_run_scan_task)
    return JSONResponse({"message": "scan started"})


def _run_scan_task():
    """Runs a single healthcheck scan in a background thread."""
    import os
    import sys

    global _scan_state
    _scan_state["running"] = True
    _scan_state["error"] = None
    _scan_state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        from ..config import AppConfig, load_simple_dotenv_mapping
        from ..healthcheck_service import HealthcheckService
        from ..http_client import HttpClient
        from ..model_catalog_service import ModelCatalogService
        from ..openrouter_client import OpenRouterClient, OpenRouterClientConfig

        project_root = Path.cwd()
        dotenv_path = project_root / ".env"
        dotenv_mapping = load_simple_dotenv_mapping(dotenv_path)
        env = {**dotenv_mapping, **dict(os.environ)}

        config = AppConfig.from_sources(cli_overrides={}, env=env)
        if not config.api_key:
            _scan_state["error"] = "OPENROUTER_API_KEY not set"
            return

        http_client = HttpClient()
        openrouter_client = OpenRouterClient(
            http_client=http_client,
            config=OpenRouterClientConfig(
                api_key=config.api_key,
                base_url=config.base_url,
                http_referer=config.http_referer,
                x_title=config.x_title,
            ),
        )

        catalog_service = ModelCatalogService(openrouter_client=openrouter_client)
        models = catalog_service.get_free_models(timeout_seconds=config.timeout_seconds)
        if config.max_models is not None:
            models = models[: config.max_models]

        healthcheck_service = HealthcheckService(openrouter_client=openrouter_client)
        results = healthcheck_service.check_models(
            models,
            prompt=config.prompt,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
            concurrency=config.concurrency,
            request_delay_seconds=config.request_delay_seconds,
        )

        repo = SqliteTimelineRepository()
        repo.append_run(config.db_path, run_datetime=datetime.now(), results=results)

    except Exception as exc:
        _scan_state["error"] = str(exc)
    finally:
        _scan_state["running"] = False


def run_server():
    """Entry point to start the web server."""
    import os
    import uvicorn

    host = os.environ.get("OPENROUTER_SCOUT_WEB_HOST", "0.0.0.0")
    port = int(os.environ.get("OPENROUTER_SCOUT_WEB_PORT", "8000"))
    print(f"Starting OpenRouter Free Model Scouter web server at http://{host}:{port}")
    uvicorn.run(
        "openrouter_free_model_scouter.web.server:app",
        host=host,
        port=port,
        reload=False,
    )
