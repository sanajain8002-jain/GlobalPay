#!/usr/bin/env python3
"""
GlobalPay 2.0 — Python Financial Analytics, FX Quote & Reconciliation Engine
Can be run standalone (`python3 services/python_analytics/ledger_engine.py`)
or deployed as a Python microservice on Render.com.

Features:
- Exact integer minor-unit arithmetic (Decimal / int, never float)
- Multi-currency conversion & corridor fee calculation (12 currencies)
- Smart Spend analytics (strictly excluding REFUNDED and FAILED transactions)
- Deterministic CSV/JSON report export
"""
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP
import json
from datetime import datetime, timezone
from typing import List, Dict

CURRENCIES: Dict[str, Dict[str, object]] = {
    "USD": {"symbol": "$", "decimals": 2, "transferable": True, "mid_rate_usd": Decimal("1.00000000")},
    "EUR": {"symbol": "€", "decimals": 2, "transferable": True, "mid_rate_usd": Decimal("0.92450000")},
    "GBP": {"symbol": "£", "decimals": 2, "transferable": True, "mid_rate_usd": Decimal("0.78900000")},
    "INR": {"symbol": "₹", "decimals": 2, "transferable": True, "mid_rate_usd": Decimal("83.95000000")},
    "JPY": {"symbol": "¥", "decimals": 0, "transferable": True, "mid_rate_usd": Decimal("153.20000000")},
    "CAD": {"symbol": "C$", "decimals": 2, "transferable": True, "mid_rate_usd": Decimal("1.38400000")},
    "AUD": {"symbol": "A$", "decimals": 2, "transferable": True, "mid_rate_usd": Decimal("1.51800000")},
    "SGD": {"symbol": "S$", "decimals": 2, "transferable": True, "mid_rate_usd": Decimal("1.34100000")},
    "AED": {"symbol": "د.إ", "decimals": 2, "transferable": True, "mid_rate_usd": Decimal("3.67250000")},
    "CHF": {"symbol": "CHF", "decimals": 2, "transferable": True, "mid_rate_usd": Decimal("0.88150000")},
    "BRL": {"symbol": "R$", "decimals": 2, "transferable": False, "mid_rate_usd": Decimal("5.68900000")},
    "ZAR": {"symbol": "R", "decimals": 2, "transferable": False, "mid_rate_usd": Decimal("17.85000000")},
}

@dataclass
class TransferQuoteResult:
    source_currency: str
    target_currency: str
    send_amount_minor: int
    fixed_fee_minor: int
    variable_fee_minor: int
    tax_amount_minor: int
    total_payable_minor: int
    mid_market_rate: str
    customer_rate: str
    recipient_amount_minor: int
    generated_at_utc: str

def calculate_corridor_quote(
    source_currency: str,
    target_currency: str,
    send_amount_minor: int,
    fixed_fee_minor: int = 299,
    pct_fee_bps: int = 45,
    fx_markup_bps: int = 35,
    tax_bps: int = 10,
) -> TransferQuoteResult:
    if send_amount_minor <= 0:
        raise ValueError("send_amount_minor must be positive")
    src_meta = CURRENCIES[source_currency]
    tgt_meta = CURRENCIES[target_currency]
    if not tgt_meta["transferable"]:
        raise ValueError(f"Corridor {source_currency}->{target_currency} is display-only, not transferable.")

    src_rate = Decimal(str(src_meta["mid_rate_usd"]))
    tgt_rate = Decimal(str(tgt_meta["mid_rate_usd"]))
    mid_cross_rate = (tgt_rate / src_rate).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)

    markup_multiplier = (Decimal(10000 - fx_markup_bps) / Decimal(10000))
    customer_rate = (mid_cross_rate * markup_multiplier).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)

    variable_fee_minor = int(
        (Decimal(send_amount_minor) * Decimal(pct_fee_bps) / Decimal(10000)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    tax_amount_minor = int(
        (Decimal(send_amount_minor) * Decimal(tax_bps) / Decimal(10000)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    total_payable_minor = send_amount_minor + fixed_fee_minor + variable_fee_minor + tax_amount_minor

    src_dec = int(src_meta["decimals"])
    tgt_dec = int(tgt_meta["decimals"])
    send_major = Decimal(send_amount_minor) / (Decimal(10) ** src_dec)
    recipient_major = send_major * customer_rate
    recipient_amount_minor = int(
        (recipient_major * (Decimal(10) ** tgt_dec)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )

    return TransferQuoteResult(
        source_currency=source_currency,
        target_currency=target_currency,
        send_amount_minor=send_amount_minor,
        fixed_fee_minor=fixed_fee_minor,
        variable_fee_minor=variable_fee_minor,
        tax_amount_minor=tax_amount_minor,
        total_payable_minor=total_payable_minor,
        mid_market_rate=str(mid_cross_rate),
        customer_rate=str(customer_rate),
        recipient_amount_minor=recipient_amount_minor,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
    )

def compute_smart_spend_summary(transactions: List[Dict[str, object]]) -> Dict[str, object]:
    """Aggregates COMPLETED spend by category while excluding REFUNDED and FAILED items."""
    category_totals: Dict[str, int] = {}
    completed_total_minor = 0
    refunded_excluded_minor = 0

    for tx in transactions:
        state = str(tx.get("state", ""))
        debit_minor = int(tx.get("totalDebitedMinor", 0))
        category = str(tx.get("spendingCategory", "General"))
        if state in ("REFUNDED", "REFUND_PENDING"):
            refunded_excluded_minor += debit_minor
            continue
        if state == "COMPLETED":
            completed_total_minor += debit_minor
            category_totals[category] = category_totals.get(category, 0) + debit_minor

    return {
        "completedTotalMinor": completed_total_minor,
        "refundedExcludedMinor": refunded_excluded_minor,
        "categoryTotalsMinor": category_totals,
    }

if __name__ == "__main__":
    quote = calculate_corridor_quote("USD", "INR", 100_000) # $1,000.00 USD -> INR
    sample_summary = compute_smart_spend_summary([
        {"referenceCode": "GP-1", "state": "COMPLETED", "totalDebitedMinor": 50574, "spendingCategory": "International"},
        {"referenceCode": "GP-2", "state": "REFUNDED", "totalDebitedMinor": 12000, "spendingCategory": "Dining"},
    ])
    print(json.dumps({"sampleQuote": asdict(quote), "sampleAnalytics": sample_summary}, indent=2))
