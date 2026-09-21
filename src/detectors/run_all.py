"""
src/detectors/run_all.py — Orchestrates all 8 fraud detectors

Executes each detector with card-specific context and returns structured results.
"""

import pandas as pd
from src.detectors.recurring_merchant_scan import recurring_merchant_scan
from src.detectors.card_testing_scan import card_testing_scan
from src.detectors.shared_device_scan import shared_device_scan
from src.detectors.new_device_scan import new_device_scan
from src.detectors.out_of_region_scan import out_of_region_scan
from src.detectors.cnp_burst_scan import cnp_burst_scan
from src.detectors.account_takeover_scan import account_takeover_scan
from src.detectors.shared_region_scan import shared_region_scan
from src.detectors.legitimacy_checklist import legitimacy_checklist


def run_all_detectors(card_id, txn_id, transactions_df, identity_df=None, closed_cases_df=None):
    """
    Executes all 8 deterministic fraud detectors for a specific transaction and card.
    Returns a list of 8 structured detector results.
    """
    txn_str = str(txn_id)
    curr_match = transactions_df[transactions_df["TransactionID"] == txn_str]
    if curr_match.empty:
        curr_match = transactions_df[transactions_df["TransactionID"] == txn_id]
        
    amount = 0.0
    device_id = None
    addr1 = None
    
    if not curr_match.empty:
        curr = curr_match.iloc[0]
        amount = float(curr.get("TransactionAmt", 0.0))
        device_id = curr.get("device_id")
        addr1 = curr.get("addr1")
        
    results = []

    # 1. Recurring Merchant Scan
    results.append(recurring_merchant_scan(card_id, amount, txn_str, transactions_df))

    # 2. Card Testing Scan
    results.append(card_testing_scan(card_id, txn_str, transactions_df, identity_df))

    # 3. Shared Device Scan
    results.append(shared_device_scan(device_id, card_id, transactions_df, identity_df, closed_cases_df))

    # 4. New Device Scan
    results.append(new_device_scan(txn_str, card_id, transactions_df, identity_df))

    # 5. Out of Region Scan
    results.append(out_of_region_scan(card_id, txn_str, transactions_df))

    # 6. CNP Burst Scan
    results.append(cnp_burst_scan(card_id, txn_str, transactions_df))

    # 7. Account Takeover Scan
    results.append(account_takeover_scan(card_id, txn_str, transactions_df, identity_df))

    # 8. Shared Region Scan
    results.append(shared_region_scan(addr1, card_id, transactions_df, closed_cases_df))

    return results
