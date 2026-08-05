"""Policy Agent — áp EC_POLICY_V2 lên evidence bundle.

Không đọc CSV. Toàn bộ primary/secondary issue, root cause, refund, action,
evidence_ids được tính deterministic bởi `policy_rules.apply_policy` (không
LLM). LLM chỉ được dùng để đề xuất `confidence`, luôn được validate và có
fallback về `base_confidence` deterministic nếu model không khả dụng hoặc trả
giá trị ngoài [0,1].
"""

from __future__ import annotations

from src import llm_client, trace_logger
from src.agents.base import BaseAgent
from src.policy_rules import apply_policy


class PolicyAgent(BaseAgent):
    name = "PolicyAgent"

    def run(self, case_id: str, order_id: str, bundle: dict, limits: dict) -> dict:
        result = apply_policy(order_id, bundle, limits)
        confidence = self._determine_confidence(case_id, bundle, result)

        self.log_tool(
            case_id, "apply_ec_policy_v2",
            {
                "order_id": order_id,
                "primary_issue": result["primary_issue"],
                "matched_cleanly": result["matched_cleanly"],
                "case_status": result["case_status"],
                "confidence": confidence,
            },
        )

        return {**result, "confidence": confidence}

    def _determine_confidence(self, case_id: str, bundle: dict, result: dict) -> float:
        base = result["base_confidence"]
        system = (
            "Bạn là Policy Agent áp EC_POLICY_V2. primary_issue đã được rule engine xác định "
            "sẵn (KHÔNG được thay đổi). Chỉ trả về JSON {\"confidence\": <số thực 0 đến 1>} "
            "thể hiện độ tin cậy của kết luận dựa trên mức độ đầy đủ/rõ ràng của dữ liệu."
        )
        user = (
            f"primary_issue={result['primary_issue']}; matched_cleanly={result['matched_cleanly']}; "
            f"reconciled={bundle.get('reconciled')}; so_item={len(bundle.get('items') or [])}; "
            f"so_payment={len(bundle.get('payments') or [])}; base_confidence_goi_y={base}."
        )
        try:
            data = llm_client.chat_json(system, user, temperature=0.1)
            trace_logger.log(
                case_id, self.name, "llm_call",
                {"system": system, "user": user, "response": data},
            )
            value = float(data.get("confidence"))
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"confidence ngoài [0,1]: {value}")
            return round(value, 2)
        except Exception as exc:  # noqa: BLE001
            trace_logger.log(
                case_id, self.name, "llm_unavailable",
                {"error": str(exc), "fallback_used": base},
            )
            return base
