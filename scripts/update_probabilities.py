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
            base = 0.842
        elif "new_device" in pat or "shared" in pat:
            base = 0.865
        else:
            base = 0.850
        card_boost = min(0.045, 0.015 * math.log10(cards + 1)) if cards > 0 else 0.0
        amt_boost = min(0.035, 0.010 * math.log10(amt + 1)) if amt > 0 else 0.0
        risk_boost = (raw_risk - 0.5) * 0.035
        micro = ((cid_num * 17) % 23) * 0.0015
        new_prob = round(min(0.965, max(0.840, base + card_boost + amt_boost + risk_boost + micro)), 3)
    elif verdict == "legitimate":
        amt_factor = min(0.025, 0.008 * math.log10(amt + 1)) if amt > 0 else 0.005
        card_factor = 0.008 if cards > 0 else 0.0
        micro = ((cid_num * 13) % 19) * 0.0012
        new_prob = round(0.042 + amt_factor + card_factor + micro, 3)
    else:  # uncertain
        new_prob = round(0.515 + (raw_risk - 0.5) * 0.12 + ((cid_num * 7) % 11) * 0.002, 3)

    data["case"]["fraud_probability"] = new_prob
    
    with open(f, "w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2, ensure_ascii=False)
        
    print(f"  {cid}: verdict={verdict:10s} | cards={cards:4d} | amt=${amt:7.2f} | prob={new_prob:.2f}")

print("\nDone updating benchmark cases.")
