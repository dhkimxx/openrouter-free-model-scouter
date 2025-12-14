from __future__ import annotations

from typing import Any, List, Mapping, Optional

from .domain_models import ModelInfo
from .openrouter_client import OpenRouterClient


class ModelCatalogService:
    def __init__(self, openrouter_client: OpenRouterClient) -> None:
        self._openrouter_client = openrouter_client

    def get_free_models(
        self,
        timeout_seconds: int,
        *,
        model_id_contains: Optional[List[str]] = None,
    ) -> List[ModelInfo]:
        response, failure_message = self._openrouter_client.list_models(
            timeout_seconds=timeout_seconds
        )
        if failure_message is not None:
            raise RuntimeError(f"OpenRouter 모델 목록 조회 실패: {failure_message}")
        if response is None:
            raise RuntimeError("OpenRouter 모델 목록 조회 실패: 응답이 비어있음")
        if response.status_code >= 400:
            raise RuntimeError(
                f"OpenRouter 모델 목록 조회 실패: HTTP {response.status_code} {response.body_text}"
            )
        if response.json_body is None:
            raise RuntimeError("OpenRouter 모델 목록 조회 실패: JSON 응답이 아님")

        data = response.json_body.get("data")
        if not isinstance(data, list):
            raise RuntimeError(
                "OpenRouter 모델 목록 조회 실패: data 필드가 리스트가 아님"
            )

        normalized_contains: List[str] = []
        if model_id_contains:
            normalized_contains = [
                item.strip().lower() for item in model_id_contains if item.strip()
            ]

        result: List[ModelInfo] = []
        for item in data:
            if not isinstance(item, dict):
                continue

            model_id = item.get("id")
            if not isinstance(model_id, str):
                continue

            if not model_id.endswith(":free"):
                continue

            if normalized_contains:
                lowered_model_id = model_id.lower()
                if not any(token in lowered_model_id for token in normalized_contains):
                    continue

            name = item.get("name")
            if not isinstance(name, str):
                name = model_id

            result.append(ModelInfo(model_id=model_id, name=name, raw=item))

        result.sort(key=lambda model: model.model_id)
        return result
