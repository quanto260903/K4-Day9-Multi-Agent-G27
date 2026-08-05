"""Customer Agent — xác định customer identity và lịch sử order.

Quyền truy cập dữ liệu: customers.csv, orders.csv (qua DataStore) — không
được đụng tới order_items/payments/products.
"""

from __future__ import annotations

from src import config
from src.agents.base import BaseAgent
from src.data_store import DataStore


class CustomerAgent(BaseAgent):
    name = "CustomerAgent"

    def __init__(self, store: DataStore) -> None:
        self.store = store

    def run(self, case_id: str, order_id: str, order: dict | None) -> dict:
        customer = self.store.get_customer(order["customer_id"]) if order else None
        customer_unique_id = customer["customer_unique_id"] if customer else None

        related_order_ids: list[str] = []
        if customer_unique_id:
            all_related = self.store.get_related_order_ids(customer_unique_id, order_id)
            related_order_ids = all_related[: config.LIMITS["related_order_ids"]]

        self.log_tool(
            case_id, "get_customer_history",
            {
                "order_id": order_id,
                "customer_unique_id": customer_unique_id,
                "related_order_count": len(related_order_ids),
            },
        )

        summary = self.summarize(
            case_id,
            system=(
                "Bạn là Customer Agent trong hệ thống điều tra khiếu nại e-commerce. "
                "Tóm tắt 1-2 câu tiếng Việt về lịch sử khách hàng CHỈ dựa trên dữ liệu "
                "được cung cấp, không tự thêm order hay số liệu nào khác."
            ),
            user=(
                f"customer_unique_id={customer_unique_id}; "
                f"so_order_khac_trong_lich_su={len(related_order_ids)}."
            ),
            fallback=(
                f"Khách hàng {customer_unique_id} có {len(related_order_ids)} order khác "
                "trong lịch sử mua hàng."
            ),
        )

        return {
            "customer_unique_id": customer_unique_id,
            "related_order_ids": related_order_ids,
            "summary": summary,
        }
