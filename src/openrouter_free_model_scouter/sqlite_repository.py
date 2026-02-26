from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .domain_models import HealthcheckResult


class SqliteTimelineRepository:
    def _init_db(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_datetime TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS healthchecks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                model_id TEXT NOT NULL,
                ok BOOLEAN NOT NULL,
                http_status INTEGER,
                error_category TEXT,
                latency_ms INTEGER,
                FOREIGN KEY(run_id) REFERENCES runs(id)
            )
        """)
        conn.commit()

    def append_run(
        self,
        db_path: Path,
        *,
        run_datetime: datetime,
        results: Iterable[HealthcheckResult],
    ) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        dt_str = self._format_run_datetime(run_datetime)

        with sqlite3.connect(db_path) as conn:
            self._init_db(conn)
            cur = conn.cursor()
            cur.execute("INSERT INTO runs (run_datetime) VALUES (?)", (dt_str,))
            run_id = cur.lastrowid

            insert_data = [
                (
                    run_id,
                    r.model_id,
                    r.ok,
                    r.http_status,
                    r.error_category,
                    r.latency_ms,
                )
                for r in results
            ]
            cur.executemany("""
                INSERT INTO healthchecks 
                (run_id, model_id, ok, http_status, error_category, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?)
            """, insert_data)
            conn.commit()

    def read_timeline(self, db_path: Path) -> Tuple[List[str], Dict[str, List[str]]]:
        """
        Returns (run_labels, model_statuses) identical to the old CSV format
        so the web frontend doesn't need to change its data structure.
        """
        if not db_path.exists():
            return [], {}

        with sqlite3.connect(db_path) as conn:
            self._init_db(conn)
            cur = conn.cursor()
            cur.execute("SELECT id, run_datetime FROM runs ORDER BY id ASC")
            runs = cur.fetchall()

            if not runs:
                return [], {}

            run_labels = [row[1] for row in runs]
            run_ids = [row[0] for row in runs]
            run_index_map = {rid: idx for idx, rid in enumerate(run_ids)}

            cur.execute("SELECT run_id, model_id, ok, http_status, error_category, latency_ms FROM healthchecks")
            checks = cur.fetchall()

            # Group by model_id -> List of length (len(runs)) initialized with ""
            model_statuses: Dict[str, List[str]] = {}
            for row in checks:
                run_id, raw_model_id, ok, http_status, error_category, latency_ms = row
                model_id = str(raw_model_id)
                if model_id not in model_statuses:
                    model_statuses[model_id] = [""] * len(runs)
                
                idx = run_index_map.get(run_id)
                if idx is not None:
                    model_statuses[model_id][idx] = self._format_status_value(
                        ok=bool(ok),
                        http_status=int(http_status) if http_status else None,
                        error_category=str(error_category) if error_category else None,
                        latency_ms=int(latency_ms) if latency_ms else None
                    )

            return run_labels, model_statuses

    def _format_status_value(
        self, ok: bool, http_status: int | None, error_category: str | None, latency_ms: int | None
    ) -> str:
        if ok:
            latency_text = "" if latency_ms is None else f" ({latency_ms}ms)"
            return f"OK{latency_text}"
        
        if http_status == 429 or error_category == "rate_limited":
            return "429"
        
        if http_status is not None:
            return f"HTTP {http_status}"
            
        if error_category:
            return error_category
            
        return "FAIL"

    def _format_run_datetime(self, value: datetime) -> str:
        if value.tzinfo is not None:
            value = value.astimezone().replace(tzinfo=None)
        return value.strftime("%Y-%m-%d %H:%M:%S")
