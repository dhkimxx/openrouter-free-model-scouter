from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
import os
import logging
from .api.endpoints import router as api_router
from .config import AppConfig, load_simple_dotenv_mapping
from .database import get_db, SessionLocal, init_db
from .worker.scouter import ScouterWorker
from .openrouter_client import OpenRouterClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_scheduled_scan():
    logger.info("Starting scheduled OpenRouter model scan...")
    # Load config from env
    from dotenv import load_dotenv

    load_dotenv()

    config = AppConfig.from_sources(cli_overrides={}, env=os.environ)
    if not config.api_key:
        logger.error("No OPENROUTER_API_KEY found. Skipping scan.")
        return

    # Import HttpClient and OpenRouterClientConfig
    from .openrouter_client import OpenRouterClient, OpenRouterClientConfig
    from .http_client import HttpClient

    db = SessionLocal()
    try:
        http_client = HttpClient()
        client_config = OpenRouterClientConfig(
            api_key=config.api_key,
            base_url=config.base_url,
            http_referer=config.http_referer,
            x_title=config.x_title,
        )
        client = OpenRouterClient(http_client=http_client, config=client_config)
        worker = ScouterWorker(db, client)
        run_id, results = worker.run_scan(config)

        success_count = sum(1 for r in results if r.ok)
        logger.info(
            f"Scan completed (Run ID: {run_id}). Checked {len(results)} models, {success_count} OK."
        )
    except Exception as e:
        logger.error(f"Error during scheduled scan: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB (creates tables if they don't exist)
    init_db()

    # Load config
    from dotenv import load_dotenv

    load_dotenv()
    config = AppConfig.from_sources(cli_overrides={}, env=os.environ)

    # Initialize Scheduler
    scheduler = BackgroundScheduler()

    # Run immediately on startup
    scheduler.add_job(run_scheduled_scan, trigger='date')

    # Schedule periodic run
    interval_hours = config.interval_hours
    logger.info(f"Scheduling automatic scans every {interval_hours} hours.")
    scheduler.add_job(run_scheduled_scan, 'interval', hours=interval_hours)

    scheduler.start()
    yield

    logger.info("Shutting down scheduler...")
    scheduler.shutdown()


app = FastAPI(title="OpenRouter Free Model Scouter", lifespan=lifespan)

app.include_router(api_router, prefix="/api")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
