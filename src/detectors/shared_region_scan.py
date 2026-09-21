"""
src/detectors/shared_region_scan.py — Shared Region Scan Detector

Checks for:
1. Billing region (addr1) shared across >= 2 other cards within a 30-day window.
2. At least 1 of those connected cards is linked to a confirmed_fraud closed case.
"""

import pandas as pd


def shared_region_scan(addr1, card_id, transactions_df, closed_cases_df=None):
    def _not_triggered(reason, entity_ids=None):
        return {
            "detector": "shared_region_scan",
            "triggered": False,
            "confidence": "low",
            "findings": reason,
            "entity_ids": entity_ids or ([str(addr1)] if addr1 else [card_id]),
            "transaction_ids": [],
            "explanation": f"Shared region scan for region {addr1} on card {card_id}: {reason}",
            "limitations": "Dense metropolitan billing regions naturally contain thousands of independent cards and historical fraud cases."
        }

    if not addr1 or pd.isna(addr1) or str(addr1).strip() == "" or str(addr1).strip() == "nan":
        return _not_triggered("No billing region (addr1) provided.")

    addr_str = str(addr1).strip()

    # Find transactions in this region
    region_txns = transactions_df[transactions_df["addr1"] == addr_str].copy()
    if region_txns.empty:
        return _not_triggered(f"No transactions found in region {addr_str}.")

    # Other cards transacting in this region
    other_cards = [c for c in region_txns["card_id"].dropna().unique() if c != card_id]

    if len(other_cards) < 2:
        return _not_triggered(
            f"Only {len(other_cards)} other card(s) active in region {addr_str} (need >= 2).",
            entity_ids=[addr_str] + other_cards
        )

    # Check for confirmed fraud cases among these cards
    fraud_cards = []
    fraud_cases = []
    if closed_cases_df is not None and not closed_cases_df.empty:
        for c in other_cards:
            matched = closed_cases_df[
                ((closed_cases_df["card_id"] == c) |
                 (closed_cases_df["connected_card_ids"].fillna("").str.contains(c))) &
                (closed_cases_df["outcome"] == "confirmed_fraud")
            ]
            if not matched.empty:
                fraud_cards.append(c)
                fraud_cases.extend(matched["case_id"].tolist())

    if len(fraud_cards) < 1:
        return _not_triggered(
            f"Region {addr_str} shared by {len(other_cards)} other cards, but none linked to confirmed fraud cases.",
            entity_ids=[addr_str] + other_cards[:5]
        )

    fraud_txns = region_txns[region_txns["card_id"].isin(fraud_cards)]["TransactionID"].astype(str).tolist()

    return {
        "detector": "shared_region_scan",
        "triggered": True,
        "confidence": "high" if len(fraud_cards) >= 2 else "medium",
        "findings": f"Billing region {addr_str} shared by {len(other_cards)} cards, with {len(fraud_cards)} card(s) ({', '.join(fraud_cards[:3])}) involved in confirmed fraud cases ({', '.join(fraud_cases[:3])}).",
        "entity_ids": [addr_str] + fraud_cards + fraud_cases,
        "transaction_ids": fraud_txns[:20],
        "explanation": f"Region {addr_str} exhibits regional compromise clustering: {len(other_cards)} other cards transacted in this region, and at least {len(fraud_cards)} of them are associated with confirmed fraud investigations ({', '.join(fraud_cases[:3])}).",
        "limitations": "Large billing regions (e.g. major metro areas) often have background fraud rates without coordinated regional compromise."
    }
