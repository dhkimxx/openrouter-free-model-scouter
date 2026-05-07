from sqlalchemy.orm import Session
from typing import List, Tuple
from ..models import Run, HealthCheck
from ..healthcheck_service import HealthcheckService
from ..model_catalog_service import ModelCatalogService
from ..openrouter_client import AsyncOpenRouterClient
from ..config import AppConfig
from ..domain_models import HealthcheckResult
from ..services.event_service import EventService
from ..time_utils import format_utc_datetime, utc_now


class ScouterWorker:
    def __init__(self, db: Session, client: AsyncOpenRouterClient):
        self.db = db
        self.client = client
        self.catalog_service = ModelCatalogService(openrouter_client=client)
        self.healthcheck_service = HealthcheckService(openrouter_client=client)

    async def run_scan(self, config: AppConfig) -> Tuple[int, List[HealthcheckResult]]:
        run_datetime = utc_now()

        models = await self.catalog_service.get_free_models(
            timeout_seconds=config.timeout_seconds,
            model_id_contains=config.model_id_contains
        )
        if config.max_models is not None:
            models = models[:config.max_models]

        results = await self.healthcheck_service.check_models(
            models,
            prompt=config.prompt,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
            concurrency=config.concurrency,
            request_delay_seconds=config.request_delay_seconds,
        )

        # Save to DB
        run_record = Run(run_datetime=format_utc_datetime(run_datetime))
        self.db.add(run_record)
        self.db.commit()

        for r in results:
            check = HealthCheck(
                run_id=run_record.id,
                model_id=r.model_id,
                ok=r.ok,
                http_status=r.http_status,
                error_category=r.error_category,
                latency_ms=r.latency_ms
            )
            self.db.add(check)
        self.db.commit()

        EventService(self.db).record_events_for_run(run_record.id, config)

        return run_record.id, results
