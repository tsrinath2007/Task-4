"""
Test for Phase 0 / Phase 1: Card ID Derivation Rule

Authoritative rule:
- transactions.csv has no card_id column.
- Within a customer, distinct card2 values = distinct cards.
- NaN card2 sorts first, then ascending numeric. Assign K1, K2, K3...
- Verify: C08623-K2 owns transaction 3530164. Do not change this rule.
"""

import os
import pandas as pd
import numpy as np
import pytest

RAW_TRANSACTIONS = os.path.join("data", "raw", "transactions.csv")
RAW_CASE_PACK = os.path.join("data", "raw", "case_pack.csv")


def derive_card_id_for_customer(df_customer, customer_id):
    """
    Given a dataframe of transactions for a specific customer,
    derive the card_id mapping according to the authoritative rule:
    - NaN card2 sorts first -> K1
    - Ascending numeric card2 -> K2, K3, ...
    """
    unique_card2 = df_customer["card2"].unique()
    nan_part = [x for x in unique_card2 if pd.isna(x)]
    num_part = sorted([x for x in unique_card2 if not pd.isna(x)])
    sorted_card2 = nan_part + num_part
    
    mapping = {}
    for i, val in enumerate(sorted_card2):
        k_val = f"{customer_id}-K{i+1}"
        if pd.isna(val):
            mapping["NaN"] = k_val
        else:
            mapping[val] = k_val
            
    return mapping


def test_c08623_card_id_derivation():
    assert os.path.exists(RAW_TRANSACTIONS), f"Missing {RAW_TRANSACTIONS}"
    
    # Read chunked to avoid loading 708MB into RAM
    c_chunks = []
    for chunk in pd.read_csv(
        RAW_TRANSACTIONS,
        chunksize=50000,
        usecols=["TransactionID", "customer_id", "card2", "ts", "TransactionAmt"]
    ):
        matched = chunk[chunk["customer_id"] == "C08623"]
        if not matched.empty:
            c_chunks.append(matched)
            
    assert len(c_chunks) > 0, "No transactions found for customer C08623"
    df_c08623 = pd.concat(c_chunks, ignore_index=True)
    
    # Verify card2 distribution
    card2_vals = df_c08623["card2"].unique()
    assert any(pd.isna(x) for x in card2_vals), "Expected NaN card2 for customer C08623"
    assert 470.0 in card2_vals, "Expected numeric card2 470.0 for customer C08623"
    
    mapping = derive_card_id_for_customer(df_c08623, "C08623")
    
    # NaN must sort first -> K1
    assert mapping["NaN"] == "C08623-K1"
    # 470.0 must be K2
    assert mapping[470.0] == "C08623-K2"
    
    # Verify transaction 3530164
    txn_row = df_c08623[df_c08623["TransactionID"] == 3530164]
    assert not txn_row.empty, "Transaction 3530164 not found for customer C08623"
    
    txn_card2 = txn_row["card2"].iloc[0]
    assert txn_card2 == 470.0, f"Expected card2=470.0 for txn 3530164, got {txn_card2}"
    
    assigned_card_id = mapping[txn_card2]
    assert assigned_card_id == "C08623-K2", f"Expected C08623-K2, got {assigned_card_id}"


def test_case_pack_hhg003_alignment():
    assert os.path.exists(RAW_CASE_PACK), f"Missing {RAW_CASE_PACK}"
    df_cp = pd.read_csv(RAW_CASE_PACK)
    hhg003 = df_cp[df_cp["case_id"] == "HHG-003"]
    assert not hhg003.empty, "HHG-003 not found in case_pack.csv"
    
    assert hhg003["customer_id"].iloc[0] == "C08623"
    assert hhg003["card_id"].iloc[0] == "C08623-K2"
    assert hhg003["flagged_txn_id"].iloc[0] == 3530164
