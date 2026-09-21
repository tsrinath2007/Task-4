"""
src/detectors/legitimacy_checklist.py — Legitimacy Checklist

Returns scores (not triggers) evaluating evidence supporting legitimate activity.
Uses CARD-SPECIFIC history — never population averages.
"""

import pandas as pd
from src.detectors.recurring_merchant_scan import recurring_merchant_scan


def legitimacy_checklist(card_id, txn_id, amount, transactions_df, identity_df=None):
    txn_str = str(txn_id)
    curr_match = transactions_df[transactions_df["TransactionID"] == txn_str]
    if curr_match.empty:
        curr_match = transactions_df[transactions_df["TransactionID"] == txn_id]
    if curr_match.empty:
        return {"checks": {}, "legitimacy_score": 0, "max_score": 0}

    curr = curr_match.iloc[0]
    history = transactions_df[
        (transactions_df["card_id"] == card_id) &
        (transactions_df["TransactionID"] != txn_str)
    ].copy()

    checks = {}

    # 1. amount_within_p95
    if len(history) >= 10:
        history["TransactionAmt_num"] = pd.to_numeric(history["TransactionAmt"], errors="coerce")
        p95 = history["TransactionAmt_num"].quantile(0.95)
        checks["amount_within_p95"] = bool(float(amount) <= p95)
    else:
        checks["amount_within_p95"] = None

    # 2. familiar_product_cd
    checks["familiar_product_cd"] = bool(curr["ProductCD"] in history["ProductCD"].values)

    # 3. home_billing_region
    curr_addr1 = curr.get("addr1")
    if pd.notna(curr_addr1) and str(curr_addr1) != "" and str(curr_addr1) != "nan":
        checks["home_billing_region"] = bool(str(curr_addr1) in history["addr1"].dropna().astype(str).values)
    else:
        checks["home_billing_region"] = None

    # 4. known_device (online only — skip for ProductCD=W in-person)
    if curr["ProductCD"] == "W" or curr.get("channel") == "in_person":
        checks["known_device"] = True  # in-person having no device is normal and legitimate
    else:
        curr_dev = str(curr.get("device_id", "")).strip()
        if curr_dev and curr_dev != "nan":
            prior_devs = set(history["device_id"].dropna().astype(str).unique())
            checks["known_device"] = bool(curr_dev in prior_devs)
        else:
            checks["known_device"] = None

    # 5. consistent_m_flags
    for flag in ["M3", "M4", "M6"]:
        if flag in history.columns and flag in curr.index and pd.notna(curr[flag]):
            hist_vals = history[flag].dropna()
            if len(hist_vals) >= 5:
                mode_val = hist_vals.mode().iloc[0]
                checks[f"{flag}_consistent"] = bool(curr[flag] == mode_val)
            else:
                checks[f"{flag}_consistent"] = None

    # 6. recurring_charge
    r_res = recurring_merchant_scan(card_id, float(amount), txn_str, transactions_df)
    checks["recurring_charge"] = bool(r_res.get("triggered", False))

    # 7. normal_parallel_activity
    if len(history) >= 5 and pd.notna(curr.get("ts")):
        curr_ts = pd.to_datetime(curr["ts"])
        history["ts_dt"] = pd.to_datetime(history["ts"])
        w_start = curr_ts - pd.Timedelta(hours=48)
        w_end = curr_ts + pd.Timedelta(hours=48)
        parallel = history[(history["ts_dt"] >= w_start) & (history["ts_dt"] <= w_end)]
        checks["normal_parallel_activity"] = bool(len(parallel) > 0)
    else:
        checks["normal_parallel_activity"] = None

    score = sum(1 for v in checks.values() if v is True)
    applicable = [v for v in checks.values() if v is not None]

    return {
        "checks": checks,
        "legitimacy_score": score,
        "max_score": len(applicable)
    }
