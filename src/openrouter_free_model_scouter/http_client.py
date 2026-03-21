import asyncio
import httpx
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple

from .domain_models import HttpResponse


@dataclass(frozen=True)
class HttpRequestFailure:
    error_category: str
    message: str
    status_code: Optional[int]


class AsyncHttpClient:
    async def request_json(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        payload: Optional[Mapping[str, Any]],
        timeout_seconds: int,
    ) -> Tuple[Optional[HttpResponse], Optional[HttpRequestFailure]]:
        
        request_headers: Dict[str, str] = {
            "Accept": "application/json",
            **dict(headers),
        }
        
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=request_headers)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=request_headers, json=payload)
                else:
                    response = await client.request(method.upper(), url, headers=request_headers, json=payload)

                response_text = response.text
                json_body = None
                try:
                    json_body = response.json()
                except (ValueError, httpx.DecodingError):
                    json_body = None

                return (
                    HttpResponse(
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        body_text=response_text,
                        json_body=json_body,
                    ),
                    None,
                )

        except httpx.HTTPStatusError as error:
            response = error.response
            return (
                HttpResponse(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    body_text=response.text,
                    json_body=response.json() if "application/json" in response.headers.get("Content-Type", "") else None,
                ),
                None,
            )
        except httpx.NetworkError as error:
            return None, HttpRequestFailure(
                error_category="network", message=str(error), status_code=None
            )
        except httpx.TimeoutException as error:
            return None, HttpRequestFailure(
                error_category="timeout", message=str(error), status_code=None
            )
        except Exception as error:  # noqa: BLE001
            return None, HttpRequestFailure(
                error_category="unexpected", message=str(error), status_code=None
            )


async def async_sleep_with_backoff(
    attempt_index: int, base_seconds: float = 0.5, max_seconds: float = 8.0
) -> None:
    delay = min(max_seconds, base_seconds * (2**attempt_index))
    await asyncio.sleep(delay)
