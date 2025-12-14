from __future__ import annotations

from dataclasses import dataclass
import json
import socket
import time
from typing import Any, Dict, Mapping, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .domain_models import HttpResponse


@dataclass(frozen=True)
class HttpRequestFailure:
    error_category: str
    message: str
    status_code: Optional[int]


class HttpClient:
    def request_json(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        payload: Optional[Mapping[str, Any]],
        timeout_seconds: int,
    ) -> Tuple[Optional[HttpResponse], Optional[HttpRequestFailure]]:
        body_bytes = None
        if payload is not None:
            body_bytes = json.dumps(payload).encode("utf-8")

        request_headers: Dict[str, str] = {
            "Accept": "application/json",
            **dict(headers),
        }
        if body_bytes is not None:
            request_headers.setdefault("Content-Type", "application/json")

        request = Request(
            url=url, data=body_bytes, headers=request_headers, method=method.upper()
        )

        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                response_body = response.read()
                response_text = response_body.decode("utf-8", errors="replace")

                json_body = None
                try:
                    parsed = json.loads(response_text)
                    if isinstance(parsed, dict):
                        json_body = parsed
                except json.JSONDecodeError:
                    json_body = None

                headers_mapping = {k: v for k, v in response.headers.items()}
                return (
                    HttpResponse(
                        status_code=int(response.status),
                        headers=headers_mapping,
                        body_text=response_text,
                        json_body=json_body,
                    ),
                    None,
                )

        except HTTPError as error:
            response_body = error.read()
            response_text = response_body.decode("utf-8", errors="replace")

            json_body = None
            try:
                parsed = json.loads(response_text)
                if isinstance(parsed, dict):
                    json_body = parsed
            except json.JSONDecodeError:
                json_body = None

            headers_mapping = (
                {k: v for k, v in error.headers.items()} if error.headers else {}
            )
            response = HttpResponse(
                status_code=int(error.code),
                headers=headers_mapping,
                body_text=response_text,
                json_body=json_body,
            )
            return response, None

        except (URLError, socket.timeout) as error:
            return None, HttpRequestFailure(
                error_category="network", message=str(error), status_code=None
            )

        except Exception as error:  # noqa: BLE001
            return None, HttpRequestFailure(
                error_category="unexpected", message=str(error), status_code=None
            )


def sleep_with_backoff(
    attempt_index: int, base_seconds: float = 0.5, max_seconds: float = 8.0
) -> None:
    delay = min(max_seconds, base_seconds * (2**attempt_index))
    time.sleep(delay)
