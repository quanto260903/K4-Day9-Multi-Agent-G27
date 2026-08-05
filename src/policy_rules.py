"""EC_POLICY_V2 — rules engine thuần Python (deterministic, không LLM).

Nhận vào một "evidence bundle" đã được các domain agent tính toán sẵn (xem
architecture.md mục 4) và áp bảng quyết định trong README mục 4 theo đúng thứ
tự ưu tiên. Toàn bộ số tiền/ID sinh ra ở đây là grounded 100% từ bundle —
Policy Agent chỉ gọi LLM để bổ sung `confidence`/rationale, không đụng vào các
giá trị này.
"""

from __future__ import annotations

PRIMARY_ORDER = [
    "canceled_order_paid",
    "unavailable_order_paid",
    "late_delivery_seller",
    "late_delivery_logistics",
    "valid_split_payment",
    "unsupported_late_claim",
]

PRIMARY_TO_CAUSE = {
    "canceled_order_paid": "ORDER_CANCELED_AFTER_PAYMENT",
    "unavailable_order_paid": "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "late_delivery_seller": "SELLER_HANDOFF_AFTER_LIMIT",
    "late_delivery_logistics": "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "valid_split_payment": "MULTIPLE_PAYMENTS_RECONCILED",
    "unsupported_late_claim": "DELIVERY_WITHIN_ESTIMATE",
}

PRIMARY_TO_ACTION = {
    "canceled_order_paid": "issue_full_refund",
    "unavailable_order_paid": "issue_full_refund",
    "late_delivery_seller": "refund_freight",
    "late_delivery_logistics": "refund_freight",
    "valid_split_payment": "explain_valid_split_payment",
    "unsupported_late_claim": "reject_late_refund",
}

# Fallback khi không case nào trong bảng khớp (không nên xảy ra với dữ liệu
# hợp lệ, nhưng vẫn cần một nhánh an toàn không phát sinh refund sai).
FALLBACK_PRIMARY_ISSUE = "unsupported_late_claim"


def determine_primary_issue(bundle: dict) -> tuple[str, bool]:
    """Trả về (primary_issue, matched_cleanly)."""

    payment_total = bundle.get("payment_total_brl") or 0.0
    order_status = bundle.get("order_status")

    if order_status == "canceled" and payment_total > 0:
        return "canceled_order_paid", True
    if order_status == "unavailable" and payment_total > 0:
        return "unavailable_order_paid", True

    variance = bundle.get("delivery_variance_hours")
    late_sellers = bundle.get("late_handoff_seller_ids") or []
    if variance is not None and variance > 0 and late_sellers:
        return "late_delivery_seller", True
    if variance is not None and variance > 0 and not late_sellers:
        return "late_delivery_logistics", True

    reconciled = bundle.get("reconciled")
    payments = bundle.get("payments") or []
    if reconciled is True and len(payments) >= 2:
        return "valid_split_payment", True
    if variance is not None and variance <= 0 and reconciled is True:
        return "unsupported_late_claim", True

    return FALLBACK_PRIMARY_ISSUE, False


def determine_secondary_issues(bundle: dict) -> list[str]:
    secondary = []
    if len(bundle.get("items") or []) >= 2:
        secondary.append("multi_item_order")
    if len(bundle.get("sellers_involved") or []) >= 2:
        secondary.append("multi_seller_order")
    if len(bundle.get("payments") or []) >= 2:
        secondary.append("split_payment")
    if bundle.get("related_order_ids"):
        secondary.append("repeat_customer")
    if len(bundle.get("category_names") or []) >= 2:
        secondary.append("multiple_categories")
    return secondary


def determine_responsible_parties(primary_issue: str, bundle: dict, max_parties: int) -> list[dict]:
    if primary_issue in ("canceled_order_paid", "unavailable_order_paid"):
        return [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
    if primary_issue == "late_delivery_seller":
        sellers = bundle.get("late_handoff_seller_ids") or []
        return [{"party_type": "seller", "party_id": sid} for sid in sellers[:max_parties]]
    if primary_issue == "late_delivery_logistics":
        return [{"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}]
    return []


def determine_refund(primary_issue: str, bundle: dict) -> float:
    if primary_issue in ("canceled_order_paid", "unavailable_order_paid"):
        return round(bundle.get("payment_total_brl") or 0.0, 2)
    if primary_issue in ("late_delivery_seller", "late_delivery_logistics"):
        return round(bundle.get("freight_total_brl") or 0.0, 2)
    return 0.0


def build_resolution_actions(primary_issue: str, case_status: str, secondary_issues: list[str], max_actions: int) -> list[str]:
    actions = [PRIMARY_TO_ACTION[primary_issue]]
    if primary_issue == "late_delivery_seller":
        actions.append("review_seller_handoff")
    elif primary_issue == "late_delivery_logistics":
        actions.append("review_carrier_delay")
    # verify_refund_completion đi kèm issue_full_refund (canceled/unavailable),
    # KHÔNG áp dụng cho refund_freight — khớp ví dụ README mục 6, case
    # late_delivery_seller action_required nhưng resolution_actions không có
    # verify_refund_completion.
    if case_status == "action_required":
        actions.append("verify_refund_completion")
    if "multi_seller_order" in secondary_issues:
        actions.append("coordinate_multi_seller_case")
    if "split_payment" in secondary_issues and primary_issue != "valid_split_payment":
        actions.append("verify_payment_allocation")
    return actions[:max_actions]


def build_evidence_ids(
    order_id: str,
    bundle: dict,
    root_cause_code: str,
    responsible_parties: list[dict],
    limits: dict,
) -> list[str]:
    ids = [f"order:{order_id}"]
    for item in (bundle.get("items") or [])[: limits["item_ids"]]:
        ids.append(f"item:{order_id}:{item['order_item_id']}")
    for payment in (bundle.get("payments") or [])[: limits["payment_ids"]]:
        ids.append(f"payment:{order_id}:{payment['payment_sequential']}")
    seller_ids = [rp["party_id"] for rp in responsible_parties if rp["party_type"] == "seller"]
    for sid in seller_ids[: limits["seller_ids"]]:
        ids.append(f"seller:{sid}")
    ids.append(f"policy:{root_cause_code}")
    return ids[: limits["evidence_ids"]]


def base_confidence(matched_cleanly: bool, bundle: dict) -> float:
    if not matched_cleanly:
        return 0.35
    score = 0.95
    if bundle.get("reconciled") is None:
        score -= 0.10
    if not bundle.get("items"):
        score -= 0.15
    return round(max(0.0, min(1.0, score)), 2)


def apply_policy(order_id: str, bundle: dict, limits: dict) -> dict:
    primary_issue, matched_cleanly = determine_primary_issue(bundle)
    secondary_issues = determine_secondary_issues(bundle)
    root_cause_code = PRIMARY_TO_CAUSE[primary_issue]
    responsible_parties = determine_responsible_parties(primary_issue, bundle, limits["responsible_parties"])
    recommended_refund = determine_refund(primary_issue, bundle)
    case_status = "action_required" if recommended_refund > 0 else "no_action"
    resolution_actions = build_resolution_actions(
        primary_issue, case_status, secondary_issues, limits["resolution_actions"]
    )
    evidence_ids = build_evidence_ids(order_id, bundle, root_cause_code, responsible_parties, limits)

    return {
        "primary_issue": primary_issue,
        "matched_cleanly": matched_cleanly,
        "secondary_issues": secondary_issues,
        "case_status": case_status,
        "root_cause_analysis": {
            "ranked_causes": [{"cause_code": root_cause_code, "rank": 1}][: limits["ranked_causes"]],
            "responsible_parties": responsible_parties,
        },
        "financial_resolution": {
            "currency": "BRL",
            "recommended_refund_brl": recommended_refund,
        },
        "resolution_actions": resolution_actions,
        "evidence_ids": evidence_ids,
        "base_confidence": base_confidence(matched_cleanly, bundle),
    }
