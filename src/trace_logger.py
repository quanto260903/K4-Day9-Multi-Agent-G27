"""Ghi trace.jsonl cho lượt chạy hiện tại (không append lịch sử cũ)."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone

from src import config

_lock = threading.Lock()


def reset_trace() -> None:
    config.LOGGING_DIR.mkdir(parents=True, exist_ok=True)
    config.TRACE_PATH.write_text("", encoding="utf-8")


def log(case_id: str, agent: str, event: str, data: dict | None = None) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "agent": agent,
        "event": event,
        "data": data or {},
    }
    line = json.dumps(entry, ensure_ascii=False)
    with _lock, config.TRACE_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
