"""Delivery Agent — delivery variance và seller handoff variance.

Quyền truy cập: orders.csv (timestamps), order_items.csv (shipping_limit_date,
seller_id). Không đụng payments/products.
"""

from __future__ import annotations

from datetime import datetime

from src.agents.base import BaseAgent
from src.data_store import DataStore

_DATE_FMT = "%Y-%m-%d %H:%M:%S"


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, _DATE_FMT)
    except ValueError:
        return None


def _hours_between(later: datetime | None, earlier: datetime | None) -> float | None:
    if later is None or earlier is None:
        return None
    return round((later - earlier).total_seconds() / 3600, 2)


class DeliveryAgent(BaseAgent):
    name = "DeliveryAgent"

    def __init__(self, store: DataStore) -> None:
        self.store = store

    def run(self, case_id: str, order_id: str, order: dict | None, items: list[dict]) -> dict:
        delivered_at = order.get("order_delivered_customer_date") if order else None
        estimated_at = order.get("order_estimated_delivery_date") if order else None
        carrier_handoff_at = order.get("order_delivered_carrier_date") if order else None

        delivery_variance_hours = _hours_between(_parse_dt(delivered_at), _parse_dt(estimated_at))
        carrier_dt = _parse_dt(carrier_handoff_at)

        seller_earliest_limit: dict[str, str] = {}
        for item in items:
            seller_id = item.get("seller_id")
            limit = item.get("shipping_limit_date")
            if not seller_id or not limit:
                continue
            if seller_id not in seller_earliest_limit or limit < seller_earliest_limit[seller_id]:
                seller_earliest_limit[seller_id] = limit

        seller_handoff_analysis: list[dict] = []
        late_handoff_seller_ids: list[str] = []
        for seller_id, limit_str in seller_earliest_limit.items():
            variance = _hours_between(carrier_dt, _parse_dt(limit_str))
            late = bool(variance is not None and variance > 0)
            seller_handoff_analysis.append(
                {
                    "seller_id": seller_id,
                    "shipping_limit_at": limit_str,
                    "handoff_variance_hours": variance,
                    "late_handoff": late,
                }
            )
            if late:
                late_handoff_seller_ids.append(seller_id)

        self.log_tool(
            case_id, "compute_delivery_variance",
            {
                "order_id": order_id,
                "delivery_variance_hours": delivery_variance_hours,
                "late_handoff_seller_ids": late_handoff_seller_ids,
            },
        )

        summary = self.summarize(
            case_id,
            system=(
                "Bạn là Delivery Agent. Tóm tắt 1-2 câu tiếng Việt về tình trạng giao hàng "
                "CHỈ dựa trên số liệu grounded được cung cấp."
            ),
            user=(
                f"delivery_variance_hours={delivery_variance_hours}; "
                f"late_handoff_seller_ids={late_handoff_seller_ids}."
            ),
            fallback=(
                f"Lệch giao hàng {delivery_variance_hours} giờ so với dự kiến; "
                f"{len(late_handoff_seller_ids)} seller bàn giao trễ hạn."
            ),
        )

        return {
            "delivered_at": delivered_at,
            "estimated_delivery_at": estimated_at,
            "carrier_handoff_at": carrier_handoff_at,
            "delivery_variance_hours": delivery_variance_hours,
            "seller_handoff_analysis": seller_handoff_analysis,
            "late_handoff_seller_ids": late_handoff_seller_ids,
            "summary": summary,
        }
