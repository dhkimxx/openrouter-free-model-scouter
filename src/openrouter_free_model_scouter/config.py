from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


def _parse_scalar(value: str) -> Any:
    stripped_value = value.strip()
    lowered_value = stripped_value.lower()

    if stripped_value == "":
        return None

    if lowered_value in {"null", "none", "~"}:
        return None

    if lowered_value in {"true", "false"}:
        return lowered_value == "true"

    try:
        return int(stripped_value)
    except ValueError:
        return stripped_value


def load_simple_dotenv_mapping(env_file_path: Path) -> Dict[str, str]:
    if not env_file_path.exists():
        return {}

    content = env_file_path.read_text(encoding="utf-8")
    mapping: Dict[str, str] = {}

    for line in content.splitlines():
        stripped_line = line.strip()
        if not stripped_line:
            continue
        if stripped_line.startswith("#"):
            continue

        normalized_line = stripped_line
        if normalized_line.startswith("export "):
            normalized_line = normalized_line[len("export ") :].strip()

        if "=" not in normalized_line:
            continue

        key, value = normalized_line.split("=", 1)
        normalized_key = key.strip()
        normalized_value = value.strip()

        if not normalized_key:
            continue

        if (
            len(normalized_value) >= 2
            and normalized_value[0] == normalized_value[-1]
            and normalized_value[0] in {'"', "'"}
        ):
            normalized_value = normalized_value[1:-1]

        mapping[normalized_key] = normalized_value

    return mapping


def _parse_csv_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    normalized: List[str] = []
    if isinstance(value, list):
        for item in value:
            for part in str(item).split(","):
                stripped_item = part.strip()
                if stripped_item:
                    normalized.append(stripped_item)
        return normalized

    for part in str(value).split(","):
        stripped_item = part.strip()
        if stripped_item:
            normalized.append(stripped_item)
    return normalized


@dataclass(frozen=True)
class AppConfig:
    api_key: str
    base_url: str
    http_referer: Optional[str]
    x_title: Optional[str]
    timeout_seconds: int
    max_retries: int
    concurrency: int
    max_models: Optional[int]
    model_id_contains: List[str]
    request_delay_seconds: float
    repeat_count: int
    repeat_interval_minutes: float
    prompt: str
    db_path: Path
    fail_if_none_ok: bool
    web_host: str
    web_port: int

    @staticmethod
    def from_sources(
        cli_overrides: Mapping[str, Any],
        env: Mapping[str, str],
    ) -> "AppConfig":
        def resolve(key: str, env_key: Optional[str], default: Any) -> Any:
            if key in cli_overrides and cli_overrides[key] is not None:
                return cli_overrides[key]
            if (
                env_key
                and env_key in env
                and env[env_key] is not None
                and env[env_key] != ""
            ):
                return _parse_scalar(env[env_key])
            return default

        api_key = resolve("api_key", "OPENROUTER_API_KEY", "")
        base_url = resolve(
            "base_url",
            "OPENROUTER_BASE_URL",
            "https://openrouter.ai/api/v1",
        )

        http_referer = resolve("http_referer", "OPENROUTER_HTTP_REFERER", None)
        x_title = resolve("x_title", "OPENROUTER_X_TITLE", None)

        timeout_seconds = int(
            resolve("timeout_seconds", "OPENROUTER_SCOUT_TIMEOUT_SECONDS", 20)
        )
        max_retries = int(resolve("max_retries", "OPENROUTER_SCOUT_MAX_RETRIES", 2))
        concurrency = int(resolve("concurrency", "OPENROUTER_SCOUT_CONCURRENCY", 2))

        max_models = resolve("max_models", "OPENROUTER_SCOUT_MAX_MODELS", None)
        if max_models is not None:
            max_models = int(max_models)

        model_id_contains = _parse_csv_string_list(
            resolve(
                "model_id_contains",
                "OPENROUTER_SCOUT_MODEL_ID_CONTAINS",
                None,
            )
        )

        request_delay_seconds = float(
            resolve(
                "request_delay_seconds", "OPENROUTER_SCOUT_REQUEST_DELAY_SECONDS", 0.3
            )
        )

        repeat_count = int(resolve("repeat_count", "OPENROUTER_SCOUT_REPEAT_COUNT", 1))
        repeat_interval_minutes = float(
            resolve(
                "repeat_interval_minutes",
                "OPENROUTER_SCOUT_REPEAT_INTERVAL_MINUTES",
                0.0,
            )
        )

        prompt = str(
            resolve(
                "prompt", "OPENROUTER_SCOUT_PROMPT", "Respond with the exact text: OK"
            )
        )

        db_path_value = resolve(
            "db_path",
            "OPENROUTER_SCOUT_DB_PATH",
            "results/scouter.db",
        )
        db_path = Path(str(db_path_value))

        fail_if_none_ok = bool(
            resolve("fail_if_none_ok", "OPENROUTER_SCOUT_FAIL_IF_NONE_OK", False)
        )

        web_host = str(resolve("web_host", "OPENROUTER_SCOUT_WEB_HOST", "0.0.0.0"))
        web_port = int(resolve("web_port", "OPENROUTER_SCOUT_WEB_PORT", 8000))

        return AppConfig(
            api_key=str(api_key),
            base_url=str(base_url).rstrip("/"),
            http_referer=str(http_referer) if http_referer else None,
            x_title=str(x_title) if x_title else None,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            concurrency=concurrency,
            max_models=max_models,
            model_id_contains=model_id_contains,
            request_delay_seconds=request_delay_seconds,
            repeat_count=repeat_count,
            repeat_interval_minutes=repeat_interval_minutes,
            prompt=prompt,
            db_path=db_path,
            fail_if_none_ok=fail_if_none_ok,
            web_host=web_host,
            web_port=web_port,
        )
