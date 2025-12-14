from __future__ import annotations

import unittest

from openrouter_free_model_scouter.domain_models import HttpResponse
from openrouter_free_model_scouter.model_catalog_service import ModelCatalogService


class _StubOpenRouterClient:
    def __init__(self, response: HttpResponse) -> None:
        self._response = response

    def list_models(self, timeout_seconds: int):
        return self._response, None


class TestModelCatalogService(unittest.TestCase):
    def test_get_free_models_filters_by_contains_tokens_case_insensitive(self) -> None:
        response = HttpResponse(
            status_code=200,
            headers={},
            body_text="",
            json_body={
                "data": [
                    {"id": "mistral/something:free", "name": "m1"},
                    {"id": "google/gemma-3:free", "name": "g1"},
                    {"id": "anthropic/claude:free", "name": "a1"},
                    {"id": "google/paid:model", "name": "paid"},
                    {"id": "MISTRAL/upper:free", "name": "m2"},
                ]
            },
        )
        service = ModelCatalogService(openrouter_client=_StubOpenRouterClient(response))

        models = service.get_free_models(
            timeout_seconds=10,
            model_id_contains=["mistral", "google"],
        )

        self.assertEqual(
            [item.model_id for item in models],
            [
                "MISTRAL/upper:free",
                "google/gemma-3:free",
                "mistral/something:free",
            ],
        )


if __name__ == "__main__":
    unittest.main()
