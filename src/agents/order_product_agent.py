"""Order & Product Agent — item, seller, product, category của order.

Quyền truy cập: orders.csv, order_items.csv, sellers.csv, products.csv,
product_category_name_translation.csv. Không đụng payments/customers.
"""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.data_store import DataStore


class OrderProductAgent(BaseAgent):
    name = "OrderProductAgent"

    def __init__(self, store: DataStore) -> None:
        self.store = store

    def run(self, case_id: str, order_id: str) -> dict:
        items = self.store.get_items(order_id)

        sellers_involved: list[str] = []
        product_ids: list[str] = []
        category_names: list[str] = []

        for item in items:
            seller_id = item.get("seller_id")
            if seller_id and seller_id not in sellers_involved:
                sellers_involved.append(seller_id)

            product_id = item.get("product_id")
            if product_id and product_id not in product_ids:
                product_ids.append(product_id)

            product = self.store.get_product(product_id) if product_id else None
            category_name = product.get("product_category_name") if product else None
            if category_name and category_name not in category_names:
                category_names.append(category_name)

        self.log_tool(
            case_id, "get_order_items",
            {
                "order_id": order_id,
                "item_count": len(items),
                "seller_count": len(sellers_involved),
                "category_count": len(category_names),
            },
        )

        summary = self.summarize(
            case_id,
            system=(
                "Bạn là Order & Product Agent. Tóm tắt 1-2 câu tiếng Việt về order "
                "(số item, số seller, danh mục sản phẩm) CHỈ dựa trên dữ liệu cung cấp."
            ),
            user=(
                f"order_id={order_id}; so_item={len(items)}; "
                f"so_seller={len(sellers_involved)}; danh_muc={category_names}."
            ),
            fallback=(
                f"Order {order_id} có {len(items)} item từ {len(sellers_involved)} seller, "
                f"thuộc {len(category_names)} danh mục sản phẩm."
            ),
        )

        return {
            "items": items,
            "sellers_involved": sellers_involved,
            "product_ids": product_ids,
            "category_names": category_names,
            "summary": summary,
        }
