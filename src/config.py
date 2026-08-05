"""Cấu hình toàn cục cho hệ thống multi-agent.

Model name và parameter size khai báo cứng ở đây (không đặt trong .env) theo
đúng yêu cầu đề bài: "model name không ghi vào .env, cho vào code để chấm".
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
INPUT_DIR = ROOT_DIR / "input"
OUTPUT_DIR = ROOT_DIR / "output"
LOGGING_DIR = ROOT_DIR / "logging"
TRACE_PATH = LOGGING_DIR / "trace.jsonl"
METADATA_PATH = LOGGING_DIR / "metadata.json"

# --- Ollama (local, <=10B params) ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Model dùng chung cho toàn bộ agent. Đổi tại đây nếu pull model khác.
MODEL_NAME = "qwen2.5:7b-instruct"
MODEL_PARAMS_B = 7.0
MODEL_FRAMEWORK = "Ollama"
MODEL_RUNTIME = "local"

LLM_TIMEOUT_SECONDS = 60
LLM_MAX_RETRIES = 2

# --- Policy ---
POLICY_VERSION = "EC_POLICY_V2"
RECONCILIATION_TOLERANCE_BRL = 0.10

# --- Output limits (theo README mục 6) ---
LIMITS = {
    "order_ids": 5,
    "item_ids": 5,
    "seller_ids": 3,
    "payment_ids": 5,
    "related_order_ids": 5,
    "product_ids": 5,
    "category_names": 5,
    "ranked_causes": 3,
    "responsible_parties": 3,
    "evidence_ids": 20,
    "resolution_actions": 5,
}
