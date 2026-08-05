"""Chạy pipeline multi-agent cho toàn bộ case trong input/, ghi output/EC_*.json.

Usage:
    python main.py
"""

from __future__ import annotations

import json
import platform
import sys
import time

import requests

from src import config, llm_client, trace_logger
from src.agents.coordinator import Coordinator
from src.data_store import get_store

# Console Windows mặc định dùng codepage cp1252, không encode được dấu tiếng
# Việt -> ép stdout/stderr sang UTF-8 để tránh UnicodeEncodeError khi print.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


def _check_ollama() -> bool:
    try:
        resp = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        return True
    except Exception:
        return False


def _write_metadata(duration_seconds: float, case_count: int, ollama_available: bool) -> None:
    metadata = {
        "model_name": config.MODEL_NAME,
        "model_parameters_billion": config.MODEL_PARAMS_B,
        "framework": config.MODEL_FRAMEWORK,
        "runtime": config.MODEL_RUNTIME,
        "ollama_base_url": config.OLLAMA_BASE_URL,
        "ollama_available_at_run": ollama_available,
        "policy_version": config.POLICY_VERSION,
        "python_version": platform.python_version(),
        "case_count": case_count,
        "run_duration_seconds": round(duration_seconds, 2),
    }
    config.LOGGING_DIR.mkdir(parents=True, exist_ok=True)
    config.METADATA_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    trace_logger.reset_trace()

    ollama_available = _check_ollama()
    llm_client.set_available(ollama_available)
    if not ollama_available:
        print(
            f"[CẢNH BÁO] Không kết nối được Ollama tại {config.OLLAMA_BASE_URL}. "
            "Pipeline vẫn chạy nhưng mọi lời gọi LLM sẽ dùng fallback deterministic.",
            file=sys.stderr,
        )

    store = get_store()
    coordinator = Coordinator(store)

    input_files = sorted(config.INPUT_DIR.glob("EC_*.json"))
    if not input_files:
        print(f"Không tìm thấy file input nào trong {config.INPUT_DIR}", file=sys.stderr)
        sys.exit(1)

    start = time.time()
    for path in input_files:
        case = json.loads(path.read_text(encoding="utf-8"))
        output = coordinator.run_case(case)
        out_path = config.OUTPUT_DIR / path.name
        out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{path.name} -> primary_issue={output['case_assessment']['primary_issue']}")
    duration = time.time() - start

    _write_metadata(duration, len(input_files), ollama_available)
    print(f"\nHoàn tất {len(input_files)} case trong {duration:.1f}s. Metadata: {config.METADATA_PATH}")


if __name__ == "__main__":
    main()
