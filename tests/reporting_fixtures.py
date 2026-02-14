from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from openpyxl import Workbook

from openrouter_free_model_scouter.reporting.constants import (
    STATUS_FAIL,
    STATUS_MISSING,
    STATUS_OK,
    STATUS_RATE_LIMITED,
)


def write_sample_timeline(xlsx_path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active

    worksheet["A1"] = "model_id"
    worksheet["B1"] = "2025-01-01 00:00:00"
    worksheet["C1"] = "2025-01-01 00:01:00"
    worksheet["D1"] = "2025-01-01 00:02:00"

    worksheet["A2"] = "a:free"
    worksheet["B2"] = "OK (100ms)"
    worksheet["C2"] = "429"
    worksheet["D2"] = "OK (80ms)"

    worksheet["A3"] = "b:free"
    worksheet["B3"] = "429"
    worksheet["C3"] = "OK (90ms)"
    worksheet["D3"] = "OK (95ms)"

    worksheet["A4"] = "c:free"
    worksheet["B4"] = "HTTP 500"
    worksheet["C4"] = "HTTP 500"
    worksheet["D4"] = "HTTP 500"

    worksheet["A5"] = "d:free"
    worksheet["C5"] = "OK (70ms)"

    worksheet["A6"] = "e:free"
    worksheet["B6"] = "OK"
    worksheet["C6"] = "OK"
    worksheet["D6"] = "OK"

    worksheet["A7"] = "f:free"
    worksheet["B7"] = "OK"
    worksheet["C7"] = "OK"
    worksheet["D7"] = "429"

    workbook.save(xlsx_path)


def sample_parsed_timeline() -> Tuple[List[str], Dict[str, List[str]]]:
    run_labels = ["run-1", "run-2", "run-3"]
    model_statuses: Dict[str, List[str]] = {
        "a:free": [STATUS_OK, STATUS_RATE_LIMITED, STATUS_OK],
        "b:free": [STATUS_RATE_LIMITED, STATUS_OK, STATUS_OK],
        "c:free": [STATUS_FAIL, STATUS_FAIL, STATUS_FAIL],
        "d:free": [STATUS_MISSING, STATUS_OK, STATUS_MISSING],
        "e:free": [STATUS_OK, STATUS_OK, STATUS_OK],
        "f:free": [STATUS_OK, STATUS_OK, STATUS_RATE_LIMITED],
    }
    return run_labels, model_statuses
