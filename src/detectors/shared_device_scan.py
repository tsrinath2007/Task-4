"""
src/detectors/shared_device_scan.py — Shared Device Scan Detector

Checks for:
1. Multi-card device sharing: Device used across >= 2 other distinct cards.
2. Prior fraud linkage: Checks if any connected cards appear in closed fraud cases.
"""

import pandas as pd


def shared_device_scan(device_id, card_id, transactions_df, identity_df=None, closed_cases_df=None):
    def _not_triggered(reason, entity_ids=None):
        return {
            "detector": "shared_device_scan",
            "triggered": False,
            "confidence": "low",
            "findings": reason,
            "entity_ids": entity_ids or ([device_id] if device_id else [card_id]),
            "transaction_ids": [],
            "explanation": f"Shared device scan for device '{device_id}' and card {card_id}: {reason}",
            "limitations": "Public or shared computers (e.g. library, internet cafe) may legitimately appear on multiple accounts."
        }

    if not device_id or pd.isna(device_id) or str(device_id).strip() == "":
        return _not_triggered("No device profile associated with this transaction.")

    device_str = str(device_id).strip()

    # Find transactions using this device
    dev_txns = transactions_df[transactions_df["device_id"] == device_str].copy()
    if dev_txns.empty:
        return _not_triggered(f"No transactions found matching device {device_str}.")

    # Distinct cards using this device
    all_cards = dev_txns["card_id"].dropna().unique().tolist()
    connected_cards = [c for c in all_cards if c != card_id]

    if len(connected_cards) < 2:
        return _not_triggered(
            f"Device {device_str} used on only {len(connected_cards)} other card(s) (need >= 2 for sharing ring).",
            entity_ids=[device_str] + connected_cards
        )

    # Check closed cases for confirmed fraud on connected cards
    prior_fraud_cases = []
    if closed_cases_df is not None and not closed_cases_df.empty:
        for c_card in connected_cards:
            matched_cases = closed_cases_df[
                ((closed_cases_df["card_id"] == c_card) |
                 (closed_cases_df["connected_card_ids"].fillna("").str.contains(c_card))) &
                (closed_cases_df["outcome"] == "confirmed_fraud")
            ]
            if not matched_cases.empty:
                prior_fraud_cases.extend(matched_cases["case_id"].tolist())

    confidence = "high" if len(prior_fraud_cases) > 0 or len(connected_cards) >= 3 else "medium"

    connected_txns = dev_txns[dev_txns["card_id"].isin(connected_cards)]["TransactionID"].astype(str).tolist()

    findings_text = (
        f"Device profile {device_str} shared across {len(connected_cards)} other cards ({', '.join(connected_cards[:5])}). "
        + (f"Connected to confirmed fraud cases: {', '.join(prior_fraud_cases)}." if prior_fraud_cases else "No prior confirmed fraud cases.")
    )

    return {
        "detector": "shared_device_scan",
        "triggered": True,
        "confidence": confidence,
        "findings": findings_text,
        "entity_ids": [device_str] + connected_cards + prior_fraud_cases,
        "transaction_ids": connected_txns[:20],  # cap list for readability
        "explanation": f"Device {device_str} was identified as a shared device linking card {card_id} to {len(connected_cards)} other distinct cards. "
                       f"Traversal: Card({card_id}) -> Device({device_str}) -> Cards({len(connected_cards)})"
                       + (f" -> ClosedFraudCases({len(prior_fraud_cases)})" if prior_fraud_cases else "") + ".",
        "limitations": "Does not prove device compromise on its own without corroborating behavioral or geographical evidence."
    }
