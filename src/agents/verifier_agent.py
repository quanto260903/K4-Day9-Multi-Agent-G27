"""Verifier Agent — cổng chặn cuối trước khi ghi output.

Kiểm tra bằng CODE xác định (không LLM) vì case fail hard-gate bị 0 điểm:
- Mọi evidence ID phải dựng được từ evidence bundle / dữ liệu gốc.
- affected_entities không chứa ID không tồn tại trong order.
- Giới hạn số lượng phần tử trong từng mảng.
- confidence trong [0,1], case_status hợp lệ.
- Null-handling đúng khi order không có item.
- resolution_actions nằm trong danh sách hợp lệ, không trùng lặp.
"""

from __future__ import annotations

from src import config
from src.agents.base import BaseAgent
from src.data_store import DataStore
from src.policy_rules import PRIMARY_TO_ACTION, PRIMARY_TO_CAUSE

_KNOWN_CAUSE_CODES = set(PRIMARY_TO_CAUSE.values())
_KNOWN_ACTIONS = set(PRIMARY_TO_ACTION.values()) | {
    "review_seller_handoff",
    "review_carrier_delay",
    "verify_refund_completion",
    "coordinate_multi_seller_case",
    "verify_payment_allocation",
}


class VerifierAgent(BaseAgent):
    name = "VerifierAgent"

    def __init__(self, store: DataStore) -> None:
        self.store = store

    def verify(self, case_id: str, order_id: str, output: dict, bundle: dict) -> list[str]:
        errors: list[str] = []
        errors += self._check_limits(output)
        errors += self._check_case_assessment(output)
        errors += self._check_evidence_ids(order_id, output, bundle)
        errors += self._check_affected_entities(order_id, output, bundle)
        errors += self._check_null_handling(output, bundle)
        errors += self._check_actions(output)

        self.log_tool(
            case_id, "verify_output",
            {"order_id": order_id, "error_count": len(errors), "errors": errors},
        )
        return errors

    def _check_limits(self, output: dict) -> list[str]:
        errors = []
        checks = {
            "affected_entities.order_ids": (output["affected_entities"]["order_ids"], config.LIMITS["order_ids"]),
            "affected_entities.item_ids": (output["affected_entities"]["item_ids"], config.LIMITS["item_ids"]),
            "affected_entities.seller_ids": (output["affected_entities"]["seller_ids"], config.LIMITS["seller_ids"]),
            "affected_entities.payment_ids": (output["affected_entities"]["payment_ids"], config.LIMITS["payment_ids"]),
            "customer_context.related_order_ids": (
                output["customer_context"]["related_order_ids"], config.LIMITS["related_order_ids"],
            ),
            "product_context.product_ids": (output["product_context"]["product_ids"], config.LIMITS["product_ids"]),
            "product_context.category_names": (
                output["product_context"]["category_names"], config.LIMITS["category_names"],
            ),
            "root_cause_analysis.ranked_causes": (
                output["root_cause_analysis"]["ranked_causes"], config.LIMITS["ranked_causes"],
            ),
            "root_cause_analysis.responsible_parties": (
                output["root_cause_analysis"]["responsible_parties"], config.LIMITS["responsible_parties"],
            ),
            "evidence_ids": (output["evidence_ids"], config.LIMITS["evidence_ids"]),
            "resolution_actions": (output["resolution_actions"], config.LIMITS["resolution_actions"]),
        }
        for field, (value, limit) in checks.items():
            if len(value) > limit:
                errors.append(f"{field} vượt giới hạn {limit}: {len(value)}")
        return errors

    def _check_case_assessment(self, output: dict) -> list[str]:
        errors = []
        ca = output["case_assessment"]
        confidence = ca.get("confidence")
        if not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
            errors.append(f"confidence ngoài [0,1]: {confidence}")
        if ca.get("case_status") not in ("action_required", "no_action"):
            errors.append(f"case_status không hợp lệ: {ca.get('case_status')}")
        return errors

    def _check_evidence_ids(self, order_id: str, output: dict, bundle: dict) -> list[str]:
        errors = []
        item_ids = {str(i["order_item_id"]) for i in (bundle.get("items") or [])}
        payment_seqs = {str(p["payment_sequential"]) for p in (bundle.get("payments") or [])}
        seller_ids = set(bundle.get("sellers_involved") or [])

        for eid in output["evidence_ids"]:
            parts = eid.split(":")
            kind = parts[0]
            if kind == "order":
                if len(parts) != 2 or parts[1] != order_id:
                    errors.append(f"evidence order sai định dạng/ID: {eid}")
            elif kind == "item":
                if len(parts) != 3 or parts[1] != order_id or parts[2] not in item_ids:
                    errors.append(f"evidence item không tồn tại trong order: {eid}")
            elif kind == "payment":
                if len(parts) != 3 or parts[1] != order_id or parts[2] not in payment_seqs:
                    errors.append(f"evidence payment không tồn tại trong order: {eid}")
            elif kind == "seller":
                exists = len(parts) == 2 and (parts[1] in seller_ids or self.store.get_seller(parts[1]) is not None)
                if not exists:
                    errors.append(f"evidence seller không tồn tại: {eid}")
            elif kind == "policy":
                if len(parts) != 2 or parts[1] not in _KNOWN_CAUSE_CODES:
                    errors.append(f"evidence policy code không hợp lệ: {eid}")
            else:
                errors.append(f"evidence sai định dạng: {eid}")
        return errors

    def _check_affected_entities(self, order_id: str, output: dict, bundle: dict) -> list[str]:
        errors = []
        ae = output["affected_entities"]
        if ae["order_ids"] != [order_id]:
            errors.append(f"affected_entities.order_ids sai: {ae['order_ids']}")

        valid_item_ids = {f"{order_id}:{i['order_item_id']}" for i in (bundle.get("items") or [])}
        for iid in ae["item_ids"]:
            if iid not in valid_item_ids:
                errors.append(f"affected_entities.item_ids không tồn tại trong order: {iid}")

        valid_payment_ids = {f"{order_id}:{p['payment_sequential']}" for p in (bundle.get("payments") or [])}
        for pid in ae["payment_ids"]:
            if pid not in valid_payment_ids:
                errors.append(f"affected_entities.payment_ids không tồn tại trong order: {pid}")

        valid_seller_ids = set(bundle.get("sellers_involved") or [])
        for sid in ae["seller_ids"]:
            if sid not in valid_seller_ids:
                errors.append(f"affected_entities.seller_ids không tồn tại trong order: {sid}")

        return errors

    def _check_null_handling(self, output: dict, bundle: dict) -> list[str]:
        errors = []
        has_items = bool(bundle.get("items"))
        pr = output["payment_reconciliation"]
        if not has_items:
            if pr.get("expected_total_brl") is not None:
                errors.append("expected_total_brl phải null khi order không có item")
            if pr.get("difference_brl") is not None:
                errors.append("difference_brl phải null khi order không có item")
            if pr.get("reconciled") is not None:
                errors.append("reconciled phải null khi order không có item")
            for field in ("item_ids", "seller_ids"):
                if output["affected_entities"][field]:
                    errors.append(f"affected_entities.{field} phải rỗng khi order không có item")
        return errors

    def _check_actions(self, output: dict) -> list[str]:
        errors = []
        actions = output["resolution_actions"]
        for action in actions:
            if action not in _KNOWN_ACTIONS:
                errors.append(f"action không nằm trong danh sách hợp lệ: {action}")
        if len(set(actions)) != len(actions):
            errors.append("resolution_actions có phần tử trùng lặp")
        return errors
