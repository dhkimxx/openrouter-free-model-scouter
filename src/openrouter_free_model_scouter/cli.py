from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .config import (
    AppConfig,
    load_simple_dotenv_mapping,
)
from .excel_timeline_repository import ExcelTimelineRepository
from .healthcheck_service import HealthcheckService
from .http_client import HttpClient
from .model_catalog_service import ModelCatalogService
from .openrouter_client import OpenRouterClient, OpenRouterClientConfig


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command != "scan":
        parser.print_help()
        raise SystemExit(2)

    project_root = Path.cwd()
    dotenv_path = Path(args.env_file) if args.env_file else (project_root / ".env")
    dotenv_mapping = load_simple_dotenv_mapping(dotenv_path)

    cli_overrides = _build_cli_overrides(args)
    config = AppConfig.from_sources(
        cli_overrides=cli_overrides,
        env=_merge_env_with_dotenv(dotenv_mapping, _read_env()),
    )

    if config.repeat_count < 1:
        print("repeat_count는 1 이상이어야 합니다.", file=sys.stderr)
        raise SystemExit(2)

    if config.repeat_interval_minutes < 0:
        print("repeat_interval_minutes는 0 이상이어야 합니다.", file=sys.stderr)
        raise SystemExit(2)

    if not config.api_key:
        print("OPENROUTER_API_KEY 환경변수가 필요합니다.", file=sys.stderr)
        raise SystemExit(2)

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

    total_ok = 0
    total_failed = 0

    excel_repository = ExcelTimelineRepository()
    excel_repository.bootstrap_from_csv_if_needed(
        xlsx_path=config.output_xlsx_path,
        csv_path=project_root / "results" / "history.csv",
    )

    for iteration_index in range(config.repeat_count):
        if iteration_index > 0 and config.repeat_interval_minutes > 0:
            time.sleep(config.repeat_interval_minutes * 60)

        run_datetime = datetime.now()

        catalog_service = ModelCatalogService(openrouter_client=openrouter_client)
        models = catalog_service.get_free_models(
            timeout_seconds=config.timeout_seconds,
            model_id_contains=config.model_id_contains,
        )
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

        excel_repository.append_run(
            config.output_xlsx_path,
            run_datetime=run_datetime,
            results=results,
        )

        ok_count = sum(1 for item in results if item.ok)
        fail_count = len(results) - ok_count
        total_ok += ok_count
        total_failed += fail_count

        current_iteration = iteration_index + 1
        print(
            f"[{current_iteration}/{config.repeat_count}] 총 {len(results)}개 모델 체크 완료"
        )
        print(f"[{current_iteration}/{config.repeat_count}] 성공: {ok_count}")
        print(f"[{current_iteration}/{config.repeat_count}] 실패: {fail_count}")
        print(f"Excel 저장: {config.output_xlsx_path}")

    if config.fail_if_none_ok and total_ok == 0:
        raise SystemExit(3)


def _read_env() -> Dict[str, str]:
    import os

    return dict(os.environ)


def _merge_env_with_dotenv(
    dotenv_mapping: Dict[str, str], runtime_env: Dict[str, str]
) -> Dict[str, str]:
    merged: Dict[str, str] = dict(dotenv_mapping)
    for key, value in runtime_env.items():
        # Empty process env values should not shadow non-empty .env values.
        if value != "":
            merged[key] = value
        elif key not in merged:
            merged[key] = value
    return merged


def _build_cli_overrides(args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "timeout_seconds": args.timeout_seconds,
        "max_retries": args.max_retries,
        "concurrency": args.concurrency,
        "max_models": args.max_models,
        "model_id_contains": args.model_id_contains,
        "request_delay_seconds": args.request_delay_seconds,
        "repeat_count": args.repeat_count,
        "repeat_interval_minutes": args.repeat_interval_minutes,
        "prompt": args.prompt,
        "output_xlsx_path": args.output_xlsx_path,
        "fail_if_none_ok": args.fail_if_none_ok,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="openrouter-free-model-scouter")

    subparsers = parser.add_subparsers(dest="command")
    scan = subparsers.add_parser(
        "scan", help=":free 모델 목록을 가져와 헬스체크하고 Excel(xlsx)로 저장"
    )

    scan.add_argument(
        "--env-file",
        default=None,
        help=".env 파일 경로(기본: ./.env). 존재하면 환경변수로 병합 로드",
    )

    scan.add_argument(
        "--timeout-seconds",
        dest="timeout_seconds",
        type=int,
        default=None,
        help="요청 타임아웃(초)",
    )
    scan.add_argument(
        "--timeout",
        dest="timeout_seconds",
        type=int,
        default=None,
        help=argparse.SUPPRESS,
    )
    scan.add_argument(
        "--max-retries",
        dest="max_retries",
        type=int,
        default=None,
        help="재시도 횟수(429/5xx/네트워크에 대해 적용)",
    )
    scan.add_argument(
        "--retries",
        dest="max_retries",
        type=int,
        default=None,
        help=argparse.SUPPRESS,
    )

    scan.add_argument("--concurrency", type=int, default=None, help="동시 실행 수")
    scan.add_argument(
        "--max-models", type=int, default=None, help="상위 N개 모델만 체크"
    )
    scan.add_argument(
        "--model-id-contains",
        nargs="+",
        default=None,
        help="모델 ID에 특정 문자열이 포함된 모델만 체크(예: --model-id-contains mistral google)",
    )
    scan.add_argument(
        "--request-delay-seconds",
        dest="request_delay_seconds",
        type=float,
        default=None,
        help="요청 지연(초). index * delay 만큼 각 모델 체크 시작을 지연",
    )
    scan.add_argument(
        "--request-delay",
        dest="request_delay_seconds",
        type=float,
        default=None,
        help=argparse.SUPPRESS,
    )

    scan.add_argument(
        "--repeat-count",
        type=int,
        default=None,
        help="반복 실행 횟수(기본: 1)",
    )
    scan.add_argument(
        "--repeat-interval-minutes",
        type=float,
        default=None,
        help="반복 주기(분). 두 번째 실행부터 적용(기본: 0)",
    )

    scan.add_argument(
        "--healthcheck-prompt",
        dest="prompt",
        default=None,
        help="헬스체크용 테스트 프롬프트",
    )
    scan.add_argument(
        "--prompt",
        dest="prompt",
        default=None,
        help=argparse.SUPPRESS,
    )
    scan.add_argument(
        "--output-xlsx-path",
        dest="output_xlsx_path",
        default=None,
        help="Excel(xlsx) 출력 경로(기본: results/history.xlsx)",
    )
    scan.add_argument(
        "--out",
        dest="output_xlsx_path",
        default=None,
        help=argparse.SUPPRESS,
    )

    scan.add_argument(
        "--fail-if-none-ok", action="store_true", help="성공 모델이 0개면 exit code 3"
    )

    return parser
