"""
src/detectors/cnp_burst_scan.py — Card-Not-Present Burst Scan Detector

Checks for:
1. Online transactions in a 48h window around txn_id.
2. Anomalous burst: 2+ online transactions exceeding card-specific p95 amount
   OR using a ProductCD never seen in the cardholder's history.
Card-specific baselines only — never global population averages.
"""

import pandas as pd
import numpy as np


def cnp_burst_scan(card_id, txn_id, transactions_df):
    def _not_triggered(reason, entity_ids=None):
        return {
            "detector": "cnp_burst_scan",
            "triggered": False,
            "confidence": "low",
            "findings": reason,
            "entity_ids": entity_ids or [card_id],
            "transaction_ids": [str(txn_id)],
            "explanation": f"CNP burst scan on card {card_id} (txn {txn_id}): {reason}",
            "limitations": "Cardholders occasionally make multiple large holiday or electronics purchases online in a single weekend."
        }

    txn_str = str(txn_id)
    curr_match = transactions_df[transactions_df["TransactionID"] == txn_str]
    if curr_match.empty:
        curr_match = transactions_df[transactions_df["TransactionID"] == txn_id]
    if curr_match.empty:
        return _not_triggered(f"Transaction {txn_id} not found.")

    curr_txn = curr_match.iloc[0]

    # Filter to card history
    card_txns = transactions_df[transactions_df["card_id"] == card_id].copy()
    if len(card_txns) < 5:
        return _not_triggered("Fewer than 5 historical transactions to compute card-specific p95 baseline.")

    card_txns["ts_dt"] = pd.to_datetime(card_txns["ts"])
    card_txns["TransactionAmt"] = pd.to_numeric(card_txns["TransactionAmt"], errors="coerce")

    # Card-specific baselines (prior to 48h window)
    curr_ts = pd.to_datetime(curr_txn["ts"])
    w_start = curr_ts - pd.Timedelta(hours=48)
    w_end = curr_ts + pd.Timedelta(hours=48)

    prior_history = card_txns[card_txns["ts_dt"] < w_start]
    baseline_df = prior_history if len(prior_history) >= 5 else card_txns[card_txns["TransactionID"] != txn_str]

    p95_amt = baseline_df["TransactionAmt"].quantile(0.95)
    known_products = set(baseline_df["ProductCD"].dropna().unique())

    # Window online transactions
    window_txns = card_txns[
        (card_txns["ts_dt"] >= w_start) &
        (card_txns["ts_dt"] <= w_end) &
        (card_txns["ProductCD"] != "W")
    ].copy()

    if len(window_txns) < 2:
        return _not_triggered(f"Only {len(window_txns)} online transaction(s) in 48h window (need >= 2 for burst).")

    # Check anomalies
    anomalous_txns = []
    has_amount_anomaly = False
    has_product_anomaly = False

    for _, row in window_txns.iterrows():
        amt = float(row["TransactionAmt"])
        prod = row["ProductCD"]
        is_amt_anom = amt > p95_amt
        is_prod_anom = prod not in known_products

        if is_amt_anom or is_prod_anom:
            anomalous_txns.append(str(row["TransactionID"]))
            if is_amt_anom:
                has_amount_anomaly = True
            if is_prod_anom:
                has_product_anomaly = True

    if len(anomalous_txns) < 2:
        return _not_triggered(
            f"Only {len(anomalous_txns)} anomalous online transaction in window (p95=${p95_amt:.2f}, known products={known_products})."
        )

    confidence = "high" if (has_amount_anomaly and has_product_anomaly) else "medium"
    if len(card_txns) < 5:
        confidence = "low"

    return {
        "detector": "cnp_burst_scan",
        "triggered": True,
        "confidence": confidence,
        "findings": f"Burst of {len(anomalous_txns)} anomalous online transactions in 48h exceeding card p95 (${p95_amt:.2f}) or in unfamiliar product codes.",
        "entity_ids": [card_id],
        "transaction_ids": anomalous_txns,
        "explanation": f"Card {card_id} experienced a card-not-present burst: {len(anomalous_txns)} online transactions within 48h were anomalous compared to cardholder's baseline (p95: ${p95_amt:.2f}, prior products: {known_products}). "
                       f"Amount anomaly: {has_amount_anomaly}, Product anomaly: {has_product_anomaly}.",
        "limitations": "Legitimate major spending sprees or seasonal shopping can mimic CNP bursts."
    }
