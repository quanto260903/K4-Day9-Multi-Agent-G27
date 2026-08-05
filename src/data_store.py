"""Tầng đọc dữ liệu Olist (chỉ đọc - read only).

Nạp toàn bộ CSV một lần khi khởi động, dựng index tra cứu O(1) theo order_id /
customer_id / customer_unique_id / seller_id / product_id để các agent domain
không phải quét lại 100k dòng cho mỗi case.

Đây là lớp truy cập dữ liệu duy nhất trong hệ thống: các agent KHÔNG tự đọc
CSV, mà gọi qua DataStore để đảm bảo mọi con số/ID đều grounded từ dữ liệu
gốc, không có chỗ cho LLM tự bịa.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src import config


def _read_csv(name: str) -> pd.DataFrame:
    path = config.DATA_DIR / name
    # keep_default_na=False (không na_values bổ sung): ô trống giữ nguyên là
    # chuỗi rỗng "" thay vì bị pandas suy diễn thành NaN (float), tránh lỗi
    # kiểu dữ liệu khi các agent xử lý timestamp rỗng (order chưa giao hàng).
    return pd.read_csv(path, dtype=str, keep_default_na=False)


class DataStore:
    def __init__(self) -> None:
        customers = _read_csv("olist_customers_dataset.csv")
        orders = _read_csv("olist_orders_dataset.csv")
        items = _read_csv("olist_order_items_dataset.csv")
        payments = _read_csv("olist_order_payments_dataset.csv")
        sellers = _read_csv("olist_sellers_dataset.csv")
        products = _read_csv("olist_products_dataset.csv")
        category_translation = _read_csv("product_category_name_translation.csv")

        items["price"] = pd.to_numeric(items["price"], errors="coerce")
        items["freight_value"] = pd.to_numeric(items["freight_value"], errors="coerce")
        items["order_item_id"] = pd.to_numeric(items["order_item_id"], errors="coerce").astype("Int64")
        payments["payment_value"] = pd.to_numeric(payments["payment_value"], errors="coerce")
        payments["payment_sequential"] = pd.to_numeric(payments["payment_sequential"], errors="coerce").astype("Int64")

        self._customers_by_id = {r["customer_id"]: r for r in customers.to_dict("records")}
        self._orders_by_id = {r["order_id"]: r for r in orders.to_dict("records")}
        self._sellers_by_id = {r["seller_id"]: r for r in sellers.to_dict("records")}
        self._products_by_id = {r["product_id"]: r for r in products.to_dict("records")}

        cat_map = {
            r["product_category_name"]: r["product_category_name_english"]
            for r in category_translation.to_dict("records")
        }
        self._category_translation = cat_map

        self._items_by_order: dict[str, list[dict]] = {}
        for r in items.sort_values(["order_id", "order_item_id"]).to_dict("records"):
            self._items_by_order.setdefault(r["order_id"], []).append(r)

        self._payments_by_order: dict[str, list[dict]] = {}
        for r in payments.sort_values(["order_id", "payment_sequential"]).to_dict("records"):
            self._payments_by_order.setdefault(r["order_id"], []).append(r)

        # customer_unique_id -> list of (order_id, order_purchase_timestamp), sorted chronologically
        unique_orders: dict[str, list[tuple[str, str]]] = {}
        for order_id, order in self._orders_by_id.items():
            customer = self._customers_by_id.get(order["customer_id"])
            if not customer:
                continue
            unique_id = customer["customer_unique_id"]
            ts = order.get("order_purchase_timestamp") or ""
            unique_orders.setdefault(unique_id, []).append((order_id, ts))
        for unique_id, pairs in unique_orders.items():
            pairs.sort(key=lambda p: p[1])
        self._orders_by_customer_unique_id = unique_orders

    # --- lookups ---

    def get_order(self, order_id: str) -> dict | None:
        return self._orders_by_id.get(order_id)

    def get_customer(self, customer_id: str) -> dict | None:
        return self._customers_by_id.get(customer_id)

    def get_items(self, order_id: str) -> list[dict]:
        return list(self._items_by_order.get(order_id, []))

    def get_payments(self, order_id: str) -> list[dict]:
        return list(self._payments_by_order.get(order_id, []))

    def get_seller(self, seller_id: str) -> dict | None:
        return self._sellers_by_id.get(seller_id)

    def get_product(self, product_id: str) -> dict | None:
        return self._products_by_id.get(product_id)

    def get_category_english(self, category_name: str | None) -> str | None:
        if not category_name:
            return None
        return self._category_translation.get(category_name, category_name)

    def get_related_order_ids(self, customer_unique_id: str, exclude_order_id: str) -> list[str]:
        pairs = self._orders_by_customer_unique_id.get(customer_unique_id, [])
        return [order_id for order_id, _ts in pairs if order_id != exclude_order_id]


_store: DataStore | None = None


def get_store() -> DataStore:
    global _store
    if _store is None:
        _store = DataStore()
    return _store
