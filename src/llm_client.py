"""Client gọi model local qua Ollama.

Mọi agent dùng chung client này để gọi `config.MODEL_NAME` (<=10B params).
Client KHÔNG được dùng để tính toán số tiền/ngày giờ hay tự sinh evidence ID
— các agent chỉ nhờ LLM cho phần diễn giải/rationale/confidence, còn số liệu
grounded luôn lấy từ `DataStore` (xem src/data_store.py).
"""

from __future__ import annotations

import json
import time

import requests

from src import config


class LLMError(Exception):
    """LLM không khả dụng hoặc trả về nội dung không hợp lệ."""


_available = True


def set_available(value: bool) -> None:
    """Đánh dấu Ollama khả dụng hay không (health-check 1 lần lúc khởi động).

    Tránh việc mỗi agent phải retry/timeout riêng lẻ hàng trăm lần khi Ollama
    chắc chắn không chạy — giúp lần chạy fallback-only nhanh hơn nhiều.
    """
    global _available
    _available = value


def chat(system: str, user: str, *, json_mode: bool = False, temperature: float = 0.2) -> str:
    if not _available:
        raise LLMError("Ollama đã được đánh dấu không khả dụng ở đầu phiên chạy")

    url = f"{config.OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": config.MODEL_NAME,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": temperature},
    }
    if json_mode:
        payload["format"] = "json"

    last_err: Exception | None = None
    for attempt in range(config.LLM_MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=payload, timeout=config.LLM_TIMEOUT_SECONDS)
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
        except Exception as exc:  # noqa: BLE001 - muốn bắt mọi lỗi mạng/HTTP để retry
            last_err = exc
            if attempt < config.LLM_MAX_RETRIES:
                time.sleep(0.5 * (attempt + 1))
    raise LLMError(f"Ollama call thất bại sau {config.LLM_MAX_RETRIES + 1} lần thử: {last_err}")


def chat_json(system: str, user: str, *, temperature: float = 0.2) -> dict:
    raw = chat(system, user, json_mode=True, temperature=temperature)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Model không trả về JSON hợp lệ: {exc}. Raw: {raw[:200]!r}") from exc
