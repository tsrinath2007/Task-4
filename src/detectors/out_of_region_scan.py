"""
src/detectors/out_of_region_scan.py — Out of Region Scan Detector

Checks for:
1. Transaction billing region (addr1) is novel for this card.
2. Parallel activity check: Normal home-region activity continues within +/- 48h.
Parallel activity = cloned card / compromise.
No parallel activity = possible legitimate travel (not triggered).
"""

import pandas as pd


def out_of_region_scan(card_id, txn_id, transactions_df):
    def _not_triggered(reason, entity_ids=None):
        return {
            "detector": "out_of_region_scan",
            "triggered": False,
            "confidence": "low",
            "findings": reason,
            "entity_ids": entity_ids or [card_id],
            "transaction_ids": [str(txn_id)],
            "explanation": f"Out of region scan for card {card_id} (txn {txn_id}): {reason}",
            "limitations": "Cardholders travel frequently; geographic divergence without simultaneous domestic activity indicates travel, not fraud."
        }

    txn_str = str(txn_id)
    curr_match = transactions_df[transactions_df["TransactionID"] == txn_str]
    if curr_match.empty:
        curr_match = transactions_df[transactions_df["TransactionID"] == txn_id]
    if curr_match.empty:
        return _not_triggered(f"Transaction {txn_id} not found.")

    curr_txn = curr_match.iloc[0]
    curr_addr1 = str(curr_txn.get("addr1", "")).strip()

    if not curr_addr1 or curr_addr1 == "nan":
        return _not_triggered("Transaction has no billing region (addr1) recorded.")

    # Get card history
    card_txns = transactions_df[
        (transactions_df["card_id"] == card_id) &
        (transactions_df["TransactionID"] != txn_str)
    ].copy()

    if len(card_txns) < 5:
        return _not_triggered("Fewer than 5 historical transactions to establish regional baseline.")

    historical_regions = set(card_txns["addr1"].dropna().astype(str).unique())
    if curr_addr1 in historical_regions:
        return _not_triggered(f"Billing region {curr_addr1} is part of cardholder's established regional history.")

    # Novel region detected. Now check for parallel activity within 48 hours
    card_txns["ts_dt"] = pd.to_datetime(card_txns["ts"])
    curr_ts = pd.to_datetime(curr_txn["ts"])

    w_start = curr_ts - pd.Timedelta(hours=48)
    w_end = curr_ts + pd.Timedelta(hours=48)

    parallel_txns = card_txns[
        (card_txns["ts_dt"] >= w_start) &
        (card_txns["ts_dt"] <= w_end) &
        (card_txns["addr1"].astype(str).isin(historical_regions))
    ]

    if parallel_txns.empty:
        return _not_triggered(
            f"Region {curr_addr1} is new, but no parallel home-region activity in 48h window (consistent with legitimate travel).",
            entity_ids=[card_id, curr_addr1]
        )

    parallel_ids = parallel_txns["TransactionID"].astype(str).tolist()
    home_regions = list(set(parallel_txns["addr1"].astype(str).unique()))

    return {
        "detector": "out_of_region_scan",
        "triggered": True,
        "confidence": "high",
        "findings": f"Purchase in new billing region {curr_addr1} while {len(parallel_ids)} home-region purchase(s) ({', '.join(home_regions)}) occurred in parallel within 48h.",
        "entity_ids": [card_id, curr_addr1] + home_regions,
        "transaction_ids": [txn_str] + parallel_ids,
        "explanation": f"Card {card_id} was used in novel region {curr_addr1}, but concurrent transactions were executed in home region(s) {home_regions} within a 48-hour window (txns: {', '.join(parallel_ids)}). Impossible co-presence indicates card cloning.",
        "limitations": "Family members or authorized secondary users sharing an account can produce concurrent physical transactions in different locations."
    }
