"""Coordinator Agent — nhận case, dispatch domain agent, gộp evidence bundle,
gọi Policy Agent → Verifier Agent, lắp ráp output đúng schema.
"""

from __future__ import annotations

from src import config, trace_logger
from src.agents.base import BaseAgent
from src.agents.customer_agent import CustomerAgent
from src.agents.delivery_agent import DeliveryAgent
from src.agents.order_product_agent import OrderProductAgent
from src.agents.payment_agent import PaymentAgent
from src.agents.policy_agent import PolicyAgent
from src.agents.verifier_agent import VerifierAgent
from src.data_store import DataStore

MAX_VERIFY_RETRIES = 2


class Coordinator(BaseAgent):
    name = "Coordinator"

    def __init__(self, store: DataStore) -> None:
        self.store = store
        self.customer_agent = CustomerAgent(store)
        self.order_product_agent = OrderProductAgent(store)
        self.payment_agent = PaymentAgent(store)
        self.delivery_agent = DeliveryAgent(store)
        self.policy_agent = PolicyAgent()
        self.verifier_agent = VerifierAgent(store)

    def run_case(self, case: dict) -> dict:
        case_id = case["case_id"]
        order_id = case["customer_request"]["claimed_order_id"]
        trace_logger.log(case_id, self.name, "case_start", {"order_id": order_id})

        order = self.store.get_order(order_id)
        if order is None:
            trace_logger.log(
                case_id, self.name, "error",
                {"message": f"order_id không tồn tại trong dữ liệu: {order_id}"},
            )
            return self._empty_case_output(case_id)

        self.log_handoff(case_id, "CustomerAgent", {"order_id": order_id})
        customer_result = self.customer_agent.run(case_id, order_id, order)

        self.log_handoff(case_id, "OrderProductAgent", {"order_id": order_id})
        order_product_result = self.order_product_agent.run(case_id, order_id)
        items = order_product_result["items"]

        self.log_handoff(case_id, "PaymentAgent", {"order_id": order_id})
        payment_result = self.payment_agent.run(case_id, order_id, items)

        self.log_handoff(case_id, "DeliveryAgent", {"order_id": order_id})
        delivery_result = self.delivery_agent.run(case_id, order_id, order, items)

        bundle = self._build_bundle(order, order_product_result, payment_result, delivery_result, customer_result)

        self.log_handoff(case_id, "PolicyAgent", {"order_id": order_id})
        policy_result = self.policy_agent.run(case_id, order_id, bundle, config.LIMITS)

        output = self._assemble_output(
            case_id, order_id, customer_result, order_product_result, delivery_result, payment_result, policy_result,
        )

        errors: list[str] = []
        for attempt in range(MAX_VERIFY_RETRIES + 1):
            self.log_handoff(case_id, "VerifierAgent", {"order_id": order_id, "attempt": attempt})
            errors = self.verifier_agent.verify(case_id, order_id, output, bundle)
            if not errors:
                break
            trace_logger.log(case_id, self.name, "verify_failed", {"attempt": attempt, "errors": errors})
            output = self._repair(output)
        if errors:
            trace_logger.log(case_id, self.name, "verify_exhausted", {"errors": errors})

        trace_logger.log(case_id, self.name, "case_end", {"order_id": order_id, "verified": not errors})
        return output

    def _build_bundle(self, order, order_product_result, payment_result, delivery_result, customer_result) -> dict:
        return {
            "order_status": order.get("order_status"),
            "items": order_product_result["items"],
            "payments": payment_result["payments"],
            "sellers_involved": order_product_result["sellers_involved"],
            "product_ids": order_product_result["product_ids"],
            "category_names": order_product_result["category_names"],
            "related_order_ids": customer_result["related_order_ids"],
            "payment_total_brl": payment_result["payment_total_brl"],
            "item_total_brl": payment_result["item_total_brl"],
            "freight_total_brl": payment_result["freight_total_brl"],
            "expected_total_brl": payment_result["expected_total_brl"],
            "difference_brl": payment_result["difference_brl"],
            "reconciled": payment_result["reconciled"],
            "payment_types": payment_result["payment_types"],
            "delivery_variance_hours": delivery_result["delivery_variance_hours"],
            "late_handoff_seller_ids": delivery_result["late_handoff_seller_ids"],
        }

    def _assemble_output(
        self, case_id, order_id, customer_result, order_product_result, delivery_result, payment_result, policy_result,
    ) -> dict:
        limits = config.LIMITS
        items = order_product_result["items"]
        payments = payment_result["payments"]

        item_ids = [f"{order_id}:{i['order_item_id']}" for i in items][: limits["item_ids"]]
        payment_ids = [f"{order_id}:{p['payment_sequential']}" for p in payments][: limits["payment_ids"]]
        seller_ids = order_product_result["sellers_involved"][: limits["seller_ids"]]

        return {
            "case_id": case_id,
            "case_assessment": {
                "primary_issue": policy_result["primary_issue"],
                "secondary_issues": policy_result["secondary_issues"],
                "case_status": policy_result["case_status"],
                "confidence": policy_result["confidence"],
            },
            "affected_entities": {
                "order_ids": [order_id],
                "item_ids": item_ids,
                "seller_ids": seller_ids,
                "payment_ids": payment_ids,
            },
            "customer_context": {
                "customer_unique_id": customer_result["customer_unique_id"],
                "related_order_ids": customer_result["related_order_ids"],
            },
            "product_context": {
                "product_ids": order_product_result["product_ids"][: limits["product_ids"]],
                "category_names": order_product_result["category_names"][: limits["category_names"]],
            },
            "delivery_analysis": {
                "delivered_at": delivery_result["delivered_at"],
                "estimated_delivery_at": delivery_result["estimated_delivery_at"],
                "carrier_handoff_at": delivery_result["carrier_handoff_at"],
                "delivery_variance_hours": delivery_result["delivery_variance_hours"],
                "seller_handoff_analysis": delivery_result["seller_handoff_analysis"],
                "late_handoff_seller_ids": delivery_result["late_handoff_seller_ids"],
            },
            "payment_reconciliation": {
                "currency": "BRL",
                "item_total_brl": payment_result["item_total_brl"],
                "freight_total_brl": payment_result["freight_total_brl"],
                "expected_total_brl": payment_result["expected_total_brl"],
                "payment_total_brl": payment_result["payment_total_brl"],
                "difference_brl": payment_result["difference_brl"],
                "reconciled": payment_result["reconciled"],
                "payment_types": payment_result["payment_types"],
            },
            "root_cause_analysis": policy_result["root_cause_analysis"],
            "evidence_ids": policy_result["evidence_ids"],
            "financial_resolution": policy_result["financial_resolution"],
            "resolution_actions": policy_result["resolution_actions"],
        }

    def _repair(self, output: dict) -> dict:
        """Sửa các lỗi có thể tự động khắc phục: cắt giới hạn mảng, kẹp confidence.

        Lỗi về ID không tồn tại/null-handling không được "sửa" ở đây vì chúng
        phản ánh bug logic thật cần fix ở agent nguồn, không phải che giấu.
        """
        limits = config.LIMITS
        output["affected_entities"]["order_ids"] = output["affected_entities"]["order_ids"][: limits["order_ids"]]
        output["affected_entities"]["item_ids"] = output["affected_entities"]["item_ids"][: limits["item_ids"]]
        output["affected_entities"]["seller_ids"] = output["affected_entities"]["seller_ids"][: limits["seller_ids"]]
        output["affected_entities"]["payment_ids"] = output["affected_entities"]["payment_ids"][: limits["payment_ids"]]
        output["customer_context"]["related_order_ids"] = output["customer_context"]["related_order_ids"][
            : limits["related_order_ids"]
        ]
        output["product_context"]["product_ids"] = output["product_context"]["product_ids"][: limits["product_ids"]]
        output["product_context"]["category_names"] = output["product_context"]["category_names"][
            : limits["category_names"]
        ]
        output["root_cause_analysis"]["ranked_causes"] = output["root_cause_analysis"]["ranked_causes"][
            : limits["ranked_causes"]
        ]
        output["root_cause_analysis"]["responsible_parties"] = output["root_cause_analysis"]["responsible_parties"][
            : limits["responsible_parties"]
        ]
        output["evidence_ids"] = output["evidence_ids"][: limits["evidence_ids"]]
        output["resolution_actions"] = output["resolution_actions"][: limits["resolution_actions"]]

        confidence = output["case_assessment"].get("confidence")
        if not isinstance(confidence, (int, float)):
            confidence = 0.5
        output["case_assessment"]["confidence"] = round(max(0.0, min(1.0, float(confidence))), 2)

        return output

    def _empty_case_output(self, case_id: str) -> dict:
        return {
            "case_id": case_id,
            "case_assessment": {
                "primary_issue": "unsupported_late_claim",
                "secondary_issues": [],
                "case_status": "no_action",
                "confidence": 0.0,
            },
            "affected_entities": {"order_ids": [], "item_ids": [], "seller_ids": [], "payment_ids": []},
            "customer_context": {"customer_unique_id": None, "related_order_ids": []},
            "product_context": {"product_ids": [], "category_names": []},
            "delivery_analysis": {
                "delivered_at": None,
                "estimated_delivery_at": None,
                "carrier_handoff_at": None,
                "delivery_variance_hours": None,
                "seller_handoff_analysis": [],
                "late_handoff_seller_ids": [],
            },
            "payment_reconciliation": {
                "currency": "BRL",
                "item_total_brl": 0.0,
                "freight_total_brl": 0.0,
                "expected_total_brl": None,
                "payment_total_brl": 0.0,
                "difference_brl": None,
                "reconciled": None,
                "payment_types": [],
            },
            "root_cause_analysis": {"ranked_causes": [], "responsible_parties": []},
            "evidence_ids": [],
            "financial_resolution": {"currency": "BRL", "recommended_refund_brl": 0.0},
            "resolution_actions": [],
        }
