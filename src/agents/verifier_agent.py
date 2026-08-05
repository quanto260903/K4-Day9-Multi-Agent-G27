"""Final deterministic gate before writing each output JSON."""

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

_TOP_LEVEL_KEYS = [
    "case_id",
    "case_assessment",
    "affected_entities",
    "customer_context",
    "product_context",
    "delivery_analysis",
    "payment_reconciliation",
    "root_cause_analysis",
    "evidence_ids",
    "financial_resolution",
    "resolution_actions",
]

_NESTED_KEYS = {
    "case_assessment": ["primary_issue", "secondary_issues", "case_status", "confidence"],
    "affected_entities": ["order_ids", "item_ids", "seller_ids", "payment_ids"],
    "customer_context": ["customer_unique_id", "related_order_ids"],
    "product_context": ["product_ids", "category_names"],
    "delivery_analysis": [
        "delivered_at",
        "estimated_delivery_at",
        "carrier_handoff_at",
        "delivery_variance_hours",
        "seller_handoff_analysis",
        "late_handoff_seller_ids",
    ],
    "payment_reconciliation": [
        "currency",
        "item_total_brl",
        "freight_total_brl",
        "expected_total_brl",
        "payment_total_brl",
        "difference_brl",
        "reconciled",
        "payment_types",
    ],
    "root_cause_analysis": ["ranked_causes", "responsible_parties"],
    "financial_resolution": ["currency", "recommended_refund_brl"],
}


class VerifierAgent(BaseAgent):
    name = "VerifierAgent"

    def __init__(self, store: DataStore) -> None:
        self.store = store

    def verify(self, case_id: str, order_id: str, output: dict, bundle: dict) -> list[str]:
        errors: list[str] = []
        errors += self._check_schema_shape(case_id, output)
        if not errors:
            errors += self._check_limits(output)
            errors += self._check_case_assessment(output)
            errors += self._check_timestamps(output)
            errors += self._check_money_and_currency(output)
            errors += self._check_root_cause(output)
            errors += self._check_evidence_ids(order_id, output, bundle)
            errors += self._check_affected_entities(order_id, output, bundle)
            errors += self._check_null_handling(output, bundle)
            errors += self._check_actions(output)

        self.log_tool(
            case_id,
            "verify_output",
            {"order_id": order_id, "error_count": len(errors), "errors": errors},
        )
        return errors

    def _check_schema_shape(self, case_id: str, output: dict) -> list[str]:
        errors = []
        if list(output.keys()) != _TOP_LEVEL_KEYS:
            return [f"top-level keys/order invalid: {list(output.keys())}"]
        if output.get("case_id") != case_id:
            errors.append(f"case_id invalid: {output.get('case_id')}")
        for section, keys in _NESTED_KEYS.items():
            value = output.get(section)
            if not isinstance(value, dict):
                errors.append(f"{section} must be an object")
            elif list(value.keys()) != keys:
                errors.append(f"{section} keys/order invalid: {list(value.keys())}")
        if not isinstance(output.get("evidence_ids"), list):
            errors.append("evidence_ids must be an array")
        if not isinstance(output.get("resolution_actions"), list):
            errors.append("resolution_actions must be an array")
        return errors

    def _check_limits(self, output: dict) -> list[str]:
        checks = {
            "affected_entities.order_ids": (output["affected_entities"]["order_ids"], config.LIMITS["order_ids"]),
            "affected_entities.item_ids": (output["affected_entities"]["item_ids"], config.LIMITS["item_ids"]),
            "affected_entities.seller_ids": (output["affected_entities"]["seller_ids"], config.LIMITS["seller_ids"]),
            "affected_entities.payment_ids": (output["affected_entities"]["payment_ids"], config.LIMITS["payment_ids"]),
            "customer_context.related_order_ids": (
                output["customer_context"]["related_order_ids"],
                config.LIMITS["related_order_ids"],
            ),
            "product_context.product_ids": (output["product_context"]["product_ids"], config.LIMITS["product_ids"]),
            "product_context.category_names": (
                output["product_context"]["category_names"],
                config.LIMITS["category_names"],
            ),
            "root_cause_analysis.ranked_causes": (
                output["root_cause_analysis"]["ranked_causes"],
                config.LIMITS["ranked_causes"],
            ),
            "root_cause_analysis.responsible_parties": (
                output["root_cause_analysis"]["responsible_parties"],
                config.LIMITS["responsible_parties"],
            ),
            "evidence_ids": (output["evidence_ids"], config.LIMITS["evidence_ids"]),
            "resolution_actions": (output["resolution_actions"], config.LIMITS["resolution_actions"]),
        }
        return [f"{field} exceeds limit {limit}: {len(value)}" for field, (value, limit) in checks.items() if len(value) > limit]

    def _check_case_assessment(self, output: dict) -> list[str]:
        errors = []
        ca = output["case_assessment"]
        if ca.get("primary_issue") not in PRIMARY_TO_ACTION:
            errors.append(f"primary_issue invalid: {ca.get('primary_issue')}")
        if not isinstance(ca.get("secondary_issues"), list):
            errors.append("secondary_issues must be an array")
        confidence = ca.get("confidence")
        if not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
            errors.append(f"confidence outside [0,1]: {confidence}")
        if ca.get("case_status") not in ("action_required", "no_action"):
            errors.append(f"case_status invalid: {ca.get('case_status')}")
        return errors

    def _check_timestamps(self, output: dict) -> list[str]:
        errors = []
        delivery = output["delivery_analysis"]
        for field in ("delivered_at", "estimated_delivery_at", "carrier_handoff_at"):
            if delivery.get(field) == "":
                errors.append(f"{field} must be null, not empty string")
        if delivery.get("delivery_variance_hours") is not None and not isinstance(
            delivery.get("delivery_variance_hours"), (int, float)
        ):
            errors.append("delivery_variance_hours must be number or null")
        for row in delivery["seller_handoff_analysis"]:
            expected_keys = ["seller_id", "shipping_limit_at", "handoff_variance_hours", "late_handoff"]
            if list(row.keys()) != expected_keys:
                errors.append(f"seller_handoff_analysis keys/order invalid: {list(row.keys())}")
            if row.get("shipping_limit_at") == "":
                errors.append("shipping_limit_at must be null, not empty string")
            if row.get("handoff_variance_hours") is not None and not isinstance(
                row.get("handoff_variance_hours"), (int, float)
            ):
                errors.append("handoff_variance_hours must be number or null")
            if not isinstance(row.get("late_handoff"), bool):
                errors.append("late_handoff must be boolean")
        return errors

    def _check_money_and_currency(self, output: dict) -> list[str]:
        errors = []
        pr = output["payment_reconciliation"]
        fr = output["financial_resolution"]
        if pr.get("currency") != "BRL":
            errors.append(f"payment currency invalid: {pr.get('currency')}")
        if fr.get("currency") != "BRL":
            errors.append(f"financial currency invalid: {fr.get('currency')}")
        for field in ("item_total_brl", "freight_total_brl", "payment_total_brl"):
            if not isinstance(pr.get(field), (int, float)):
                errors.append(f"{field} must be number")
        for field in ("expected_total_brl", "difference_brl"):
            if pr.get(field) is not None and not isinstance(pr.get(field), (int, float)):
                errors.append(f"{field} must be number or null")
        if pr.get("reconciled") is not None and not isinstance(pr.get("reconciled"), bool):
            errors.append("reconciled must be boolean or null")
        if not isinstance(pr.get("payment_types"), list):
            errors.append("payment_types must be an array")
        if not isinstance(fr.get("recommended_refund_brl"), (int, float)):
            errors.append("recommended_refund_brl must be number")
        return errors

    def _check_root_cause(self, output: dict) -> list[str]:
        errors = []
        for row in output["root_cause_analysis"]["ranked_causes"]:
            if list(row.keys()) != ["cause_code", "rank"]:
                errors.append(f"ranked_causes keys/order invalid: {list(row.keys())}")
            if row.get("cause_code") not in _KNOWN_CAUSE_CODES:
                errors.append(f"cause_code invalid: {row.get('cause_code')}")
            if not isinstance(row.get("rank"), int):
                errors.append("rank must be integer")
        for row in output["root_cause_analysis"]["responsible_parties"]:
            if list(row.keys()) != ["party_type", "party_id"]:
                errors.append(f"responsible_parties keys/order invalid: {list(row.keys())}")
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
                    errors.append(f"invalid order evidence: {eid}")
            elif kind == "item":
                if len(parts) != 3 or parts[1] != order_id or parts[2] not in item_ids:
                    errors.append(f"item evidence not in order: {eid}")
            elif kind == "payment":
                if len(parts) != 3 or parts[1] != order_id or parts[2] not in payment_seqs:
                    errors.append(f"payment evidence not in order: {eid}")
            elif kind == "seller":
                exists = len(parts) == 2 and (parts[1] in seller_ids or self.store.get_seller(parts[1]) is not None)
                if not exists:
                    errors.append(f"seller evidence not found: {eid}")
            elif kind == "policy":
                if len(parts) != 2 or parts[1] not in _KNOWN_CAUSE_CODES:
                    errors.append(f"invalid policy evidence: {eid}")
            else:
                errors.append(f"invalid evidence format: {eid}")
        return errors

    def _check_affected_entities(self, order_id: str, output: dict, bundle: dict) -> list[str]:
        errors = []
        ae = output["affected_entities"]
        if ae["order_ids"] != [order_id]:
            errors.append(f"affected order_ids invalid: {ae['order_ids']}")

        valid_item_ids = {f"{order_id}:{i['order_item_id']}" for i in (bundle.get("items") or [])}
        for iid in ae["item_ids"]:
            if iid not in valid_item_ids:
                errors.append(f"affected item_id not in order: {iid}")

        valid_payment_ids = {f"{order_id}:{p['payment_sequential']}" for p in (bundle.get("payments") or [])}
        for pid in ae["payment_ids"]:
            if pid not in valid_payment_ids:
                errors.append(f"affected payment_id not in order: {pid}")

        valid_seller_ids = set(bundle.get("sellers_involved") or [])
        for sid in ae["seller_ids"]:
            if sid not in valid_seller_ids:
                errors.append(f"affected seller_id not in order: {sid}")

        return errors

    def _check_null_handling(self, output: dict, bundle: dict) -> list[str]:
        errors = []
        has_items = bool(bundle.get("items"))
        pr = output["payment_reconciliation"]
        if not has_items:
            if pr.get("expected_total_brl") is not None:
                errors.append("expected_total_brl must be null when order has no items")
            if pr.get("difference_brl") is not None:
                errors.append("difference_brl must be null when order has no items")
            if pr.get("reconciled") is not None:
                errors.append("reconciled must be null when order has no items")
            for field in ("item_ids", "seller_ids"):
                if output["affected_entities"][field]:
                    errors.append(f"affected_entities.{field} must be empty when order has no items")
            if output["product_context"]["product_ids"] or output["product_context"]["category_names"]:
                errors.append("product_context must be empty when order has no items")
            if output["delivery_analysis"]["seller_handoff_analysis"]:
                errors.append("seller_handoff_analysis must be empty when order has no items")
        return errors

    def _check_actions(self, output: dict) -> list[str]:
        errors = []
        actions = output["resolution_actions"]
        for action in actions:
            if action not in _KNOWN_ACTIONS:
                errors.append(f"unknown action: {action}")
        if len(set(actions)) != len(actions):
            errors.append("resolution_actions contains duplicates")
        return errors
