from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
import time
from typing import List, Optional
from uuid import uuid4

from .domain_models import HealthcheckResult, ModelInfo
from .http_client import sleep_with_backoff
from .openrouter_client import OpenRouterClient


@dataclass(frozen=True)
class HealthcheckSummary:
    run_id: str
    total: int
    ok: int
    failed: int


class HealthcheckService:
    def __init__(self, openrouter_client: OpenRouterClient) -> None:
        self._openrouter_client = openrouter_client

    def check_models(
        self,
        models: List[ModelInfo],
        *,
        prompt: str,
        timeout_seconds: int,
        max_retries: int,
        concurrency: int,
        request_delay_seconds: float,
    ) -> List[HealthcheckResult]:
        run_id = str(uuid4())

        def task(index: int, model: ModelInfo) -> HealthcheckResult:
            if request_delay_seconds > 0:
                time.sleep(request_delay_seconds * index)
            return self._check_single_model(
                run_id=run_id,
                model_id=model.model_id,
                prompt=prompt,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
            )

        results: List[HealthcheckResult] = []
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
            futures = [
                executor.submit(task, index, model)
                for index, model in enumerate(models)
            ]
            for future in as_completed(futures):
                results.append(future.result())

        results.sort(key=lambda item: item.model_id)
        return results

    def _check_single_model(
        self,
        *,
        run_id: str,
        model_id: str,
        prompt: str,
        timeout_seconds: int,
        max_retries: int,
    ) -> HealthcheckResult:
        last_error_category: Optional[str] = None
        last_error_message: Optional[str] = None
        last_status: Optional[int] = None

        start_time = time.monotonic()

        for attempt in range(0, max_retries + 1):
            response, failure_message = self._openrouter_client.chat_completion(
                model_id=model_id,
                prompt=prompt,
                timeout_seconds=timeout_seconds,
            )

            if failure_message is not None:
                last_error_category = "network"
                last_error_message = failure_message
                if attempt < max_retries:
                    sleep_with_backoff(attempt)
                    continue
                return self._build_failure_result(
                    run_id=run_id,
                    model_id=model_id,
                    attempts=attempt + 1,
                    start_time=start_time,
                    http_status=None,
                    error_category=last_error_category,
                    error_message=last_error_message,
                )

            if response is None:
                last_error_category = "unexpected"
                last_error_message = "응답이 비어있음"
                if attempt < max_retries:
                    sleep_with_backoff(attempt)
                    continue
                return self._build_failure_result(
                    run_id=run_id,
                    model_id=model_id,
                    attempts=attempt + 1,
                    start_time=start_time,
                    http_status=None,
                    error_category=last_error_category,
                    error_message=last_error_message,
                )

            last_status = response.status_code

            if response.status_code == 429:
                last_error_category = "rate_limited"
                last_error_message = self._extract_error_message(response)
                if attempt < max_retries:
                    sleep_with_backoff(attempt)
                    continue
                return self._build_failure_result(
                    run_id=run_id,
                    model_id=model_id,
                    attempts=attempt + 1,
                    start_time=start_time,
                    http_status=last_status,
                    error_category=last_error_category,
                    error_message=last_error_message,
                )

            if response.status_code >= 500:
                last_error_category = "server_error"
                last_error_message = self._extract_error_message(response)
                if attempt < max_retries:
                    sleep_with_backoff(attempt)
                    continue
                return self._build_failure_result(
                    run_id=run_id,
                    model_id=model_id,
                    attempts=attempt + 1,
                    start_time=start_time,
                    http_status=last_status,
                    error_category=last_error_category,
                    error_message=last_error_message,
                )

            if response.status_code >= 400:
                last_error_category = "client_error"
                last_error_message = self._extract_error_message(response)
                return self._build_failure_result(
                    run_id=run_id,
                    model_id=model_id,
                    attempts=attempt + 1,
                    start_time=start_time,
                    http_status=last_status,
                    error_category=last_error_category,
                    error_message=last_error_message,
                )

            content_preview = self._extract_content_preview(response)
            latency_ms = int((time.monotonic() - start_time) * 1000)

            return HealthcheckResult(
                run_id=run_id,
                timestamp_iso=_now_iso(),
                model_id=model_id,
                ok=True,
                http_status=response.status_code,
                latency_ms=latency_ms,
                attempts=attempt + 1,
                error_category=None,
                error_message=None,
                response_preview=content_preview,
            )

        return self._build_failure_result(
            run_id=run_id,
            model_id=model_id,
            attempts=max_retries + 1,
            start_time=start_time,
            http_status=last_status,
            error_category=last_error_category or "unexpected",
            error_message=last_error_message or "알 수 없는 오류",
        )

    def _extract_content_preview(self, response) -> Optional[str]:
        if response.json_body is None:
            return None

        choices = response.json_body.get("choices")
        if not isinstance(choices, list) or not choices:
            return None

        first = choices[0]
        if not isinstance(first, dict):
            return None

        message = first.get("message")
        if not isinstance(message, dict):
            return None

        content = message.get("content")
        if not isinstance(content, str):
            return None

        stripped = content.strip()
        if len(stripped) > 160:
            return stripped[:160]
        return stripped

    def _extract_error_message(self, response) -> str:
        if response.json_body is None:
            return response.body_text

        error = response.json_body.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str):
                return message

        return response.body_text

    def _build_failure_result(
        self,
        *,
        run_id: str,
        model_id: str,
        attempts: int,
        start_time: float,
        http_status: Optional[int],
        error_category: str,
        error_message: str,
    ) -> HealthcheckResult:
        latency_ms = int((time.monotonic() - start_time) * 1000)
        return HealthcheckResult(
            run_id=run_id,
            timestamp_iso=_now_iso(),
            model_id=model_id,
            ok=False,
            http_status=http_status,
            latency_ms=latency_ms,
            attempts=attempts,
            error_category=error_category,
            error_message=error_message,
            response_preview=None,
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
