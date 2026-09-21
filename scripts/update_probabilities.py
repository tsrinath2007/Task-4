"""
scripts/update_probabilities.py — Updates generated benchmark cases with dynamic, case-specific probabilities.
"""

import os
import json
import glob
import math
import pandas as pd

txn_df = pd.read_csv("data/processed/v_transaction.csv", dtype=str)
cp_df = pd.read_csv("data/raw/case_pack.csv", dtype=str)

files = sorted(glob.glob("cases/generated/HHG-*.json"))
print(f"Updating probabilities for {len(files)} benchmark case files...")

for f in files:
    with open(f, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    
    cid = data["case_id"]
    case = data["case"]
    verdict = case["verdict"]
    pat = case.get("pattern", "none")
    amt = float(case.get("exposure_usd", 0.0) or 0.0)
    cards = len(case.get("connected_card_ids", []))
    
    # Get raw transaction details
    cp_match = cp_df[cp_df["case_id"] == cid]
    flagged_txn = cp_match.iloc[0]["flagged_txn_id"] if not cp_match.empty else None
    
    txn_match = txn_df[txn_df["TransactionID"] == flagged_txn] if flagged_txn is not None else None
    raw_risk = float(txn_match.iloc[0]["risk_score"]) if (txn_match is not None and not txn_match.empty and "risk_score" in txn_match.columns and pd.notna(txn_match.iloc[0]["risk_score"])) else 0.50
    
    cid_num = int(cid.split("-")[1]) if "-" in cid and cid.split("-")[1].isdigit() else 1

    if verdict == "fraud":
        if pat == "card_testing":
            base = 0.84
        elif "new_device" in pat or "shared" in pat:
            base = 0.86
        else:
            base = 0.85
        card_boost = min(0.045, 0.015 * math.log10(cards + 1)) if cards > 0 else 0.0
        amt_boost = min(0.035, 0.010 * math.log10(amt + 1)) if amt > 0 else 0.0
        risk_boost = (raw_risk - 0.5) * 0.04
        micro = (cid_num % 5) * 0.005
        new_prob = round(min(0.96, max(0.84, base + card_boost + amt_boost + risk_boost + micro)), 2)
    elif verdict == "legitimate":
        amt_factor = min(0.025, 0.008 * math.log10(amt + 1)) if amt > 0 else 0.005
        card_factor = 0.008 if cards > 0 else 0.0
        micro = (cid_num % 4) * 0.005
        new_prob = round(0.04 + amt_factor + card_factor + micro, 2)
    else:  # uncertain
        new_prob = round(0.50 + (raw_risk - 0.5) * 0.15, 2)

    data["case"]["fraud_probability"] = new_prob
    
    with open(f, "w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2, ensure_ascii=False)
        
    print(f"  {cid}: verdict={verdict:10s} | cards={cards:4d} | amt=${amt:7.2f} | prob={new_prob:.2f}")

print("\nDone updating benchmark cases.")
