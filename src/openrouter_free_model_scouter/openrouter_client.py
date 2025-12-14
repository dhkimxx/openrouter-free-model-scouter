from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .domain_models import HttpResponse
from .http_client import HttpClient


@dataclass(frozen=True)
class OpenRouterClientConfig:
    api_key: str
    base_url: str
    http_referer: Optional[str]
    x_title: Optional[str]


class OpenRouterClient:
    def __init__(self, http_client: HttpClient, config: OpenRouterClientConfig) -> None:
        self._http_client = http_client
        self._config = config

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Authorization": f"Bearer {self._config.api_key}",
            "User-Agent": "openrouter-free-model-scouter/0.1.0",
        }
        if self._config.http_referer:
            headers["HTTP-Referer"] = self._config.http_referer
        if self._config.x_title:
            headers["X-Title"] = self._config.x_title
        return headers

    def list_models(
        self, timeout_seconds: int
    ) -> Tuple[Optional[HttpResponse], Optional[str]]:
        url = f"{self._config.base_url}/models"
        response, failure = self._http_client.request_json(
            method="GET",
            url=url,
            headers=self._build_headers(),
            payload=None,
            timeout_seconds=timeout_seconds,
        )
        if failure is not None:
            return None, failure.message
        return response, None

    def chat_completion(
        self,
        model_id: str,
        prompt: str,
        timeout_seconds: int,
    ) -> Tuple[Optional[HttpResponse], Optional[str]]:
        url = f"{self._config.base_url}/chat/completions"
        payload: Mapping[str, Any] = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 32,
            "temperature": 0,
            "stream": False,
        }

        response, failure = self._http_client.request_json(
            method="POST",
            url=url,
            headers=self._build_headers(),
            payload=payload,
            timeout_seconds=timeout_seconds,
        )
        if failure is not None:
            return None, failure.message
        return response, None
