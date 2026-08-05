"""Payment Agent — tổng hợp payment row và đối soát với item + freight.

Quyền truy cập: order_items.csv (price, freight_value), order_payments.csv.
Không đụng products/delivery timestamps.
"""

from __future__ import annotations

from src import config
from src.agents.base import BaseAgent
from src.data_store import DataStore


class PaymentAgent(BaseAgent):
    name = "PaymentAgent"

    def __init__(self, store: DataStore) -> None:
        self.store = store

    def run(self, case_id: str, order_id: str, items: list[dict]) -> dict:
        payments = self.store.get_payments(order_id)

        payment_total = round(
            sum(p["payment_value"] for p in payments if p.get("payment_value") is not None), 2
        )

        item_total = round(sum(i["price"] for i in items if i.get("price") is not None), 2) if items else 0.0
        freight_total = (
            round(sum(i["freight_value"] for i in items if i.get("freight_value") is not None), 2)
            if items
            else 0.0
        )

        if items:
            expected_total = round(item_total + freight_total, 2)
            difference = round(payment_total - expected_total, 2)
            reconciled = abs(difference) <= config.RECONCILIATION_TOLERANCE_BRL
        else:
            expected_total = None
            difference = None
            reconciled = None

        payment_types: list[str] = []
        for p in payments:
            payment_type = p.get("payment_type")
            if payment_type and payment_type not in payment_types:
                payment_types.append(payment_type)

        self.log_tool(
            case_id, "reconcile_payment",
            {
                "order_id": order_id,
                "payment_total_brl": payment_total,
                "expected_total_brl": expected_total,
                "difference_brl": difference,
                "reconciled": reconciled,
            },
        )

        summary = self.summarize(
            case_id,
            system=(
                "Bạn là Payment Agent. Tóm tắt 1-2 câu tiếng Việt về đối soát thanh toán "
                "CHỈ dựa trên số liệu grounded được cung cấp, không tự tính lại."
            ),
            user=(
                f"payment_total_brl={payment_total}; expected_total_brl={expected_total}; "
                f"difference_brl={difference}; reconciled={reconciled}; so_payment={len(payments)}."
            ),
            fallback=(
                f"Tổng thanh toán {payment_total} BRL, kỳ vọng {expected_total} BRL, "
                f"chênh lệch {difference} BRL, reconciled={reconciled}."
            ),
        )

        return {
            "payments": payments,
            "payment_total_brl": payment_total,
            "item_total_brl": item_total,
            "freight_total_brl": freight_total,
            "expected_total_brl": expected_total,
            "difference_brl": difference,
            "reconciled": reconciled,
            "payment_types": payment_types,
            "summary": summary,
        }
