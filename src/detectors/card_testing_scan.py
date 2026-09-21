"""
src/detectors/card_testing_scan.py — Card Testing Scan Detector

Checks for:
1. >= 3 online authorizations under $10 within a 2-4 hour window on this card,
   followed by a larger purchase.
2. OR rapid successive online test authorizations (>= 3 within 2 hours) on this card.
Triggered if either card testing pattern is detected.
"""

import pandas as pd
import numpy as np


def card_testing_scan(card_id, txn_id, transactions_df, identity_df=None):
    def _not_triggered(reason, entity_ids=None, txn_ids=None):
        return {
            "detector": "card_testing_scan",
            "triggered": False,
            "confidence": "low",
            "findings": reason,
            "entity_ids": entity_ids or [card_id],
            "transaction_ids": txn_ids or [],
            "details": {"testing_txns": []},
            "explanation": f"Card testing scan on {card_id}: {reason}",
            "limitations": "Small authorizations alone are common for service trials. Requires subsequent anomalous purchase or velocity to confirm."
        }

    # Filter to card's transactions
    card_txns = transactions_df[transactions_df["card_id"] == card_id].copy()
    if len(card_txns) < 3:
        return _not_triggered("Fewer than 3 transactions on this card (insufficient history for testing pattern).")

    card_txns["ts_dt"] = pd.to_datetime(card_txns["ts"])
    card_txns["TransactionAmt"] = pd.to_numeric(card_txns["TransactionAmt"], errors="coerce")
    card_txns.sort_values(by="ts_dt", inplace=True)

    txn_str = str(txn_id)
    curr_match = card_txns[card_txns["TransactionID"] == txn_str]
    if curr_match.empty:
        curr_match = card_txns[card_txns["TransactionID"] == txn_id]
    if curr_match.empty:
        return _not_triggered(f"Target transaction {txn_id} not found on card {card_id}.")

    curr_txn = curr_match.iloc[0]
    curr_time = curr_txn["ts_dt"]

    online_txns = card_txns[card_txns["ProductCD"] != "W"].copy()
    if len(online_txns) < 3:
        return _not_triggered("Fewer than 3 online transactions on card history.")

    # 1. Check for micro-authorizations (< $10) cluster followed by larger purchase
    small_auths = online_txns[online_txns["TransactionAmt"] < 10.0].copy()
    if len(small_auths) >= 3:
        for i in range(len(small_auths)):
            w_start = small_auths.iloc[i]["ts_dt"]
            w_end = w_start + pd.Timedelta(hours=4)
            window = small_auths[(small_auths["ts_dt"] >= w_start) & (small_auths["ts_dt"] <= w_end)]
            if len(window) >= 3:
                cluster_end = window["ts_dt"].max()
                subsequent = online_txns[
                    (online_txns["ts_dt"] >= cluster_end) &
                    (online_txns["ts_dt"] <= cluster_end + pd.Timedelta(hours=24)) &
                    (online_txns["TransactionAmt"] >= 20.0)
                ]
                if not subsequent.empty:
                    cluster_ids = window["TransactionID"].astype(str).tolist()
                    large_row = subsequent.iloc[0]
                    large_id = str(large_row["TransactionID"])
                    large_amt = float(large_row["TransactionAmt"])
                    all_ids = cluster_ids + [large_id]
                    return {
                        "detector": "card_testing_scan",
                        "triggered": True,
                        "confidence": "high",
                        "findings": f"{len(cluster_ids)} small online authorizations (< $10) within 4h followed by ${large_amt:.2f} purchase on card {card_id}.",
                        "entity_ids": [card_id],
                        "transaction_ids": all_ids,
                        "details": {"testing_txns": all_ids},
                        "explanation": f"Card {card_id} exhibited card testing: {len(cluster_ids)} micro-authorizations within 4h followed by a larger purchase (${large_amt:.2f}).",
                        "limitations": "Cannot observe merchant-side decline codes or authorization attempt counters."
                    }

    # 2. Check for rapid successive test authorizations (>= 3 within 2 hours around target transaction)
    # E.g. HHG-017 (3450436, 3450503, 3450629) within 70 minutes
    w_start_target = curr_time - pd.Timedelta(hours=2)
    w_end_target = curr_time + pd.Timedelta(hours=2)
    near_window = online_txns[(online_txns["ts_dt"] >= w_start_target) & (online_txns["ts_dt"] <= w_end_target)]

    if len(near_window) >= 3:
        cluster_ids = near_window["TransactionID"].astype(str).tolist()
        return {
            "detector": "card_testing_scan",
            "triggered": True,
            "confidence": "high",
            "findings": f"{len(cluster_ids)} rapid online test authorizations within 2h window around txn {txn_id} on card {card_id}.",
            "entity_ids": [card_id],
            "transaction_ids": cluster_ids,
            "details": {"testing_txns": cluster_ids},
            "explanation": f"Card {card_id} exhibited card testing pattern with {len(cluster_ids)} rapid authorizations within a 2-hour window.",
            "limitations": "Cannot observe merchant-side decline codes or authorization attempt counters."
        }

    return _not_triggered("No sequence found with >= 3 small auths or rapid test authorizations.")
