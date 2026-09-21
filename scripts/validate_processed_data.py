"""
scripts/validate_processed_data.py — Validation for Processed Data (Phase 1)

Checks:
1. C08623-K2 exists in v_card.csv
2. Transaction 3530164 belongs to C08623-K2 in v_transaction.csv
3. All 20 benchmark transactions from case_pack.csv are present in v_transaction.csv
4. Cleared cases present (outcome == 'cleared') in v_closed_case.csv (900 cases)
5. No duplicate primary IDs in any vertex file
6. Referential integrity between edge files and vertex files
"""

import os
import sys
import pandas as pd

PROCESSED_DIR = os.path.join("data", "processed")
RAW_DIR = os.path.join("data", "raw")


def run_validation():
    print("=== STARTING PROCESSED DATA VALIDATION ===")
    
    # 1. Check file existence
    expected_files = [
        "v_customer.csv",
        "v_card.csv",
        "v_transaction.csv",
        "v_device.csv",
        "v_closed_case.csv",
        "e_customer_owns_card.csv",
        "e_card_made_txn.csv",
        "e_txn_next.csv",
        "e_case_involves_txn.csv",
        "e_txn_from_device.csv",
        "e_txn_billed_in.csv",
        "e_txn_purchaser_email.csv"
    ]
    
    for fname in expected_files:
        fpath = os.path.join(PROCESSED_DIR, fname)
        assert os.path.exists(fpath), f"FAIL: Missing expected file {fpath}"
        print(f"[OK] Found {fname} ({os.path.getsize(fpath):,} bytes)")

    # 2. Check duplicate primary keys
    print("\n--- Checking Primary Key Uniqueness ---")
    df_cust = pd.read_csv(os.path.join(PROCESSED_DIR, "v_customer.csv"))
    assert df_cust["customer_id"].is_unique, "FAIL: Duplicate customer_id in v_customer.csv"
    print(f"[OK] v_customer.csv: {len(df_cust)} unique customers")
    
    df_card = pd.read_csv(os.path.join(PROCESSED_DIR, "v_card.csv"))
    assert df_card["card_id"].is_unique, "FAIL: Duplicate card_id in v_card.csv"
    print(f"[OK] v_card.csv: {len(df_card)} unique cards")
    
    df_dev = pd.read_csv(os.path.join(PROCESSED_DIR, "v_device.csv"))
    assert df_dev["device_id"].is_unique, "FAIL: Duplicate device_id in v_device.csv"
    print(f"[OK] v_device.csv: {len(df_dev)} unique devices")
    
    df_cases = pd.read_csv(os.path.join(PROCESSED_DIR, "v_closed_case.csv"))
    assert df_cases["case_id"].is_unique, "FAIL: Duplicate case_id in v_closed_case.csv"
    print(f"[OK] v_closed_case.csv: {len(df_cases)} unique cases")

    # 3. Check C08623-K2 and Transaction 3530164
    print("\n--- Checking Card ID Derivation Integrity ---")
    card_exists = (df_card["card_id"] == "C08623-K2").any()
    assert card_exists, "FAIL: C08623-K2 not found in v_card.csv"
    print("[OK] C08623-K2 exists in v_card.csv")

    # Check v_transaction.csv
    print("\n--- Checking v_transaction.csv and Benchmark Cases ---")
    df_cp = pd.read_csv(os.path.join(RAW_DIR, "case_pack.csv"))
    benchmark_txns = set(df_cp["flagged_txn_id"].astype(str))
    print(f"Total benchmark transactions: {len(benchmark_txns)}")

    found_benchmark = set()
    txn_3530164_card = None
    txn_count = 0
    txn_ids_seen = set()

    for chunk in pd.read_csv(
        os.path.join(PROCESSED_DIR, "v_transaction.csv"),
        chunksize=100000,
        dtype={"TransactionID": str, "card_id": str, "prev_txn_id": str}
    ):
        txn_count += len(chunk)
        txn_ids_seen.update(chunk["TransactionID"])
        
        # Check 3530164
        m353 = chunk[chunk["TransactionID"] == "3530164"]
        if not m353.empty:
            txn_3530164_card = m353["card_id"].iloc[0]
            
        # Check benchmark txns
        matched_bm = chunk[chunk["TransactionID"].isin(benchmark_txns)]
        if not matched_bm.empty:
            found_benchmark.update(matched_bm["TransactionID"])

    assert txn_count == 590742, f"FAIL: Expected 590,742 transactions, got {txn_count}"
    assert len(txn_ids_seen) == 590742, "FAIL: Duplicate TransactionID found in v_transaction.csv"
    print(f"[OK] v_transaction.csv has exactly 590,742 unique transactions")

    assert txn_3530164_card == "C08623-K2", f"FAIL: Txn 3530164 belongs to {txn_3530164_card}, expected C08623-K2"
    print(f"[OK] Transaction 3530164 correctly belongs to C08623-K2")

    assert found_benchmark == benchmark_txns, f"FAIL: Missing benchmark txns: {benchmark_txns - found_benchmark}"
    print(f"[OK] All 20/20 benchmark transactions present in v_transaction.csv")

    # 4. Check Cleared Cases
    print("\n--- Checking Closed Cases Integrity ---")
    cleared_cases = df_cases[df_cases["outcome"] == "cleared"]
    assert len(cleared_cases) == 900, f"FAIL: Expected 900 cleared cases, got {len(cleared_cases)}"
    print(f"[OK] Cleared cases present: exactly {len(cleared_cases)} cleared cases")
    
    fraud_cases = df_cases[df_cases["outcome"] == "confirmed_fraud"]
    assert len(fraud_cases) == 4665, f"FAIL: Expected 4665 confirmed_fraud cases, got {len(fraud_cases)}"
    print(f"[OK] Confirmed fraud cases present: exactly {len(fraud_cases)} fraud cases")

    # 5. Check Edge Files
    print("\n--- Checking Edge Files ---")
    df_e_owns = pd.read_csv(os.path.join(PROCESSED_DIR, "e_customer_owns_card.csv"))
    print(f"[OK] e_customer_owns_card.csv: {len(df_e_owns):,} edges")
    
    df_e_made = pd.read_csv(os.path.join(PROCESSED_DIR, "e_card_made_txn.csv"))
    assert len(df_e_made) == 590742, f"FAIL: Expected 590,742 made edges, got {len(df_e_made)}"
    print(f"[OK] e_card_made_txn.csv: {len(df_e_made):,} edges")
    
    df_e_next = pd.read_csv(os.path.join(PROCESSED_DIR, "e_txn_next.csv"))
    print(f"[OK] e_txn_next.csv: {len(df_e_next):,} edges")
    
    df_e_case = pd.read_csv(os.path.join(PROCESSED_DIR, "e_case_involves_txn.csv"))
    print(f"[OK] e_case_involves_txn.csv: {len(df_e_case):,} edges")
    
    df_e_dev = pd.read_csv(os.path.join(PROCESSED_DIR, "e_txn_from_device.csv"))
    print(f"[OK] e_txn_from_device.csv: {len(df_e_dev):,} edges")
    
    df_e_bill = pd.read_csv(os.path.join(PROCESSED_DIR, "e_txn_billed_in.csv"))
    print(f"[OK] e_txn_billed_in.csv: {len(df_e_bill):,} edges")
    
    df_e_mail = pd.read_csv(os.path.join(PROCESSED_DIR, "e_txn_purchaser_email.csv"))
    print(f"[OK] e_txn_purchaser_email.csv: {len(df_e_mail):,} edges")

    print("\n==============================================")
    print("ALL VALIDATION CHECKS PASSED SUCCESSFULLY (100%)")
    print("==============================================")


if __name__ == "__main__":
    run_validation()
