"""
src/data/prep_data.py — Data Preparation for TigerGraph HHGOA Fraud Investigation

Authoritative Requirements:
1. Never load raw 708MB transactions.csv into RAM all at once (stream in chunks).
2. Never modify data/raw/.
3. Card ID rule:
   Within each customer, distinct card2 values = distinct cards.
   NaN card2 sorts first, then ascending numeric. Assign K1, K2, K3...
   Key: lambda x: (0 if x == 'nan' else 1, 0 if x == 'nan' else float(x))
   Verify: C08623-K2 owns transaction 3530164.
4. Output compact files to data/processed/ for TigerGraph loading.
"""

import os
import gc
import time
import csv
import pandas as pd
import numpy as np

RAW_DIR = os.path.join("data", "raw")
PROCESSED_DIR = os.path.join("data", "processed")


def derive_card_mappings(transactions_path):
    """
    Pass 1: Read minimal columns to establish card_id mapping,
    chronological sequence, prev_txn_id, and gap_min for every transaction.
    """
    print("Pass 1: Reading transaction sequence metadata...")
    t0 = time.time()
    
    cols = ["TransactionID", "customer_id", "card2", "ts"]
    chunks = []
    for chunk in pd.read_csv(transactions_path, usecols=cols, dtype={"customer_id": str, "card2": str}, chunksize=100000):
        chunks.append(chunk)
    df_meta = pd.concat(chunks, ignore_index=True)
    del chunks
    gc.collect()
    
    print(f"Read {len(df_meta)} rows in {time.time() - t0:.2f}s.")
    
    # Authoritative Card ID Derivation
    print("Deriving card IDs...")
    df_meta["fp"] = df_meta["card2"].fillna("nan")
    card_map = {}
    for cust_id, group in df_meta.groupby("customer_id"):
        unique_vals = sorted(
            group["fp"].unique(),
            key=lambda x: (0 if x == "nan" else 1, 0 if x == "nan" else float(x))
        )
        for i, val in enumerate(unique_vals, start=1):
            card_map[(cust_id, val)] = f"{cust_id}-K{i}"
            
    df_meta["card_id"] = [card_map[(c, v)] for c, v in zip(df_meta["customer_id"], df_meta["fp"])]
    
    # Sequence & Time Gaps within Card
    print("Sorting transactions chronologically by card...")
    df_meta["ts_dt"] = pd.to_datetime(df_meta["ts"])
    df_meta.sort_values(by=["card_id", "ts_dt", "TransactionID"], inplace=True)
    
    df_meta["prev_txn_id"] = df_meta.groupby("card_id")["TransactionID"].shift(1)
    df_meta["prev_ts"] = df_meta.groupby("card_id")["ts_dt"].shift(1)
    df_meta["gap_min"] = (df_meta["ts_dt"] - df_meta["prev_ts"]).dt.total_seconds() / 60.0
    
    # Build fast lookup dictionaries
    txn_card_dict = dict(zip(df_meta["TransactionID"], df_meta["card_id"]))
    txn_prev_dict = dict(zip(df_meta["TransactionID"], df_meta["prev_txn_id"]))
    txn_gap_dict = dict(zip(df_meta["TransactionID"], df_meta["gap_min"]))
    
    # Verify authoritative benchmark check
    c08623_k2 = card_map.get(("C08623", "470.0"))
    assert c08623_k2 == "C08623-K2", f"Expected C08623-K2, got {c08623_k2}"
    assert txn_card_dict.get(3530164) == "C08623-K2", f"Expected txn 3530164 to be C08623-K2, got {txn_card_dict.get(3530164)}"
    print("Verified: C08623-K2 owns transaction 3530164.")
    
    del df_meta
    gc.collect()
    print(f"Pass 1 complete in {time.time() - t0:.2f}s.")
    return txn_card_dict, txn_prev_dict, txn_gap_dict


def process_identity(identity_path):
    """
    Process identity.csv to extract DeviceProfiles and build lookup map.
    """
    print("Processing identity.csv...")
    t0 = time.time()
    df_id = pd.read_csv(identity_path)
    
    # Unique device profiles
    profile_cols = ["DeviceInfo", "id_30", "id_31", "id_33"]
    df_id["profile_key"] = (
        df_id["DeviceInfo"].fillna("").astype(str) + " | " +
        df_id["id_30"].fillna("").astype(str) + " | " +
        df_id["id_31"].fillna("").astype(str) + " | " +
        df_id["id_33"].fillna("").astype(str)
    )
    
    unique_profiles = sorted(df_id["profile_key"].unique())
    device_id_map = {p: f"D{i+1:06d}" for i, p in enumerate(unique_profiles)}
    df_id["device_id"] = df_id["profile_key"].map(device_id_map)
    
    # Create v_device.csv
    device_summary = df_id.groupby("device_id").agg({
        "DeviceInfo": "first",
        "id_30": "first",
        "id_31": "first",
        "id_33": "first",
        "DeviceType": "first"
    }).reset_index()
    device_summary.rename(columns={
        "id_30": "device_os",
        "id_31": "device_browser",
        "id_33": "device_screen",
        "DeviceInfo": "device_info",
        "DeviceType": "device_type"
    }, inplace=True)
    
    device_out = os.path.join(PROCESSED_DIR, "v_device.csv")
    device_summary.to_csv(device_out, index=False)
    print(f"Saved {len(device_summary)} devices to {device_out}.")
    
    # Build lookup map for transactions: TransactionID -> (id_15, id_23, device_id)
    id_lookup = {}
    for _, row in df_id.iterrows():
        id_lookup[row["TransactionID"]] = (
            "" if pd.isna(row["id_15"]) else str(row["id_15"]),
            "" if pd.isna(row["id_23"]) else str(row["id_23"]),
            "" if pd.isna(row["device_id"]) else str(row["device_id"])
        )
        
    del df_id, device_summary
    gc.collect()
    print(f"Identity processing complete in {time.time() - t0:.2f}s.")
    return id_lookup


def process_closed_cases(closed_cases_path):
    """
    Process closed_cases_history.csv to create v_closed_case.csv and e_case_involves_txn.csv.
    Preserves ALL 5,565 cases (both confirmed_fraud and cleared).
    """
    print("Processing closed cases history...")
    df_cases = pd.read_csv(closed_cases_path)
    print(f"Total closed cases: {len(df_cases)} (cleared: {(df_cases['outcome'] == 'cleared').sum()})")
    
    # Output v_closed_case.csv directly
    case_out = os.path.join(PROCESSED_DIR, "v_closed_case.csv")
    df_cases.to_csv(case_out, index=False)
    
    # Output e_case_involves_txn.csv
    case_txn_edges = []
    for _, row in df_cases.iterrows():
        case_id = row["case_id"]
        txn_list = []
        if pd.notna(row["txn_ids"]):
            txn_list.extend(str(row["txn_ids"]).split("|"))
        if pd.notna(row["first_fraud_txn_id"]):
            ff_id = str(row["first_fraud_txn_id"])
            if ff_id not in txn_list:
                txn_list.append(ff_id)
                
        for t_id in txn_list:
            t_id_clean = t_id.strip()
            if t_id_clean:
                case_txn_edges.append({"case_id": case_id, "TransactionID": t_id_clean})
                
    df_case_edges = pd.DataFrame(case_txn_edges).drop_duplicates()
    case_edge_out = os.path.join(PROCESSED_DIR, "e_case_involves_txn.csv")
    df_case_edges.to_csv(case_edge_out, index=False)
    print(f"Saved {len(df_cases)} cases to {case_out} and {len(df_case_edges)} involves edges to {case_edge_out}.")


def process_transactions_and_edges(transactions_path, txn_card_dict, txn_prev_dict, txn_gap_dict, id_lookup):
    """
    Pass 2: Read transactions.csv in chunks, enrich with sequence and identity,
    and stream out v_transaction.csv and all transaction-related edge files.
    """
    print("Pass 2: Streaming transactions and generating vertices/edges...")
    t0 = time.time()
    
    keep_cols = [
        "TransactionID", "customer_id", "ts", "TransactionAmt",
        "ProductCD", "addr1", "P_emaildomain", "R_emaildomain",
        "risk_score", "channel",
        "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"
    ]
    
    # Target files
    f_v_txn = open(os.path.join(PROCESSED_DIR, "v_transaction.csv"), "w", newline="", encoding="utf-8")
    f_e_owns = open(os.path.join(PROCESSED_DIR, "e_customer_owns_card.csv"), "w", newline="", encoding="utf-8")
    f_e_made = open(os.path.join(PROCESSED_DIR, "e_card_made_txn.csv"), "w", newline="", encoding="utf-8")
    f_e_next = open(os.path.join(PROCESSED_DIR, "e_txn_next.csv"), "w", newline="", encoding="utf-8")
    f_e_dev = open(os.path.join(PROCESSED_DIR, "e_txn_from_device.csv"), "w", newline="", encoding="utf-8")
    f_e_bill = open(os.path.join(PROCESSED_DIR, "e_txn_billed_in.csv"), "w", newline="", encoding="utf-8")
    f_e_mail = open(os.path.join(PROCESSED_DIR, "e_txn_purchaser_email.csv"), "w", newline="", encoding="utf-8")
    
    # Writers
    w_v_txn = csv.writer(f_v_txn)
    w_e_owns = csv.writer(f_e_owns)
    w_e_made = csv.writer(f_e_made)
    w_e_next = csv.writer(f_e_next)
    w_e_dev = csv.writer(f_e_dev)
    w_e_bill = csv.writer(f_e_bill)
    w_e_mail = csv.writer(f_e_mail)
    
    # Headers
    w_v_txn.writerow([
        "TransactionID", "card_id", "customer_id", "ts", "TransactionAmt",
        "ProductCD", "addr1", "P_emaildomain", "R_emaildomain",
        "risk_score", "channel",
        "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9",
        "id_15", "id_23", "device_id", "gap_min", "prev_txn_id"
    ])
    w_e_owns.writerow(["customer_id", "card_id"])
    w_e_made.writerow(["card_id", "TransactionID"])
    w_e_next.writerow(["from_txn_id", "to_txn_id", "gap_min"])
    w_e_dev.writerow(["TransactionID", "device_id"])
    w_e_bill.writerow(["TransactionID", "addr1"])
    w_e_mail.writerow(["TransactionID", "email_domain"])
    
    seen_owns = set()
    unique_customers = set()
    unique_cards = set()
    unique_regions = set()
    unique_emails = set()
    
    total_txns = 0
    
    for chunk in pd.read_csv(transactions_path, usecols=keep_cols, chunksize=100000):
        for row in chunk.itertuples(index=False):
            txn_id = row.TransactionID
            cust_id = row.customer_id
            card_id = txn_card_dict.get(txn_id, f"{cust_id}-K1")
            
            # Identity attributes
            id_info = id_lookup.get(txn_id, ("", "", ""))
            id_15, id_23, device_id = id_info
            
            # Sequence attributes
            prev_id = txn_prev_dict.get(txn_id)
            prev_id_str = "" if pd.isna(prev_id) else str(int(prev_id))
            gap_val = txn_gap_dict.get(txn_id)
            gap_str = "" if pd.isna(gap_val) else f"{gap_val:.4f}"
            
            # Formatted fields
            addr1_str = "" if pd.isna(row.addr1) else str(row.addr1)
            p_email = "" if pd.isna(row.P_emaildomain) else str(row.P_emaildomain)
            r_email = "" if pd.isna(row.R_emaildomain) else str(row.R_emaildomain)
            risk_str = "" if pd.isna(row.risk_score) else str(row.risk_score)
            
            # Write v_transaction.csv
            w_v_txn.writerow([
                txn_id, card_id, cust_id, row.ts, row.TransactionAmt,
                row.ProductCD, addr1_str, p_email, r_email,
                risk_str, row.channel,
                row.M1 if pd.notna(row.M1) else "",
                row.M2 if pd.notna(row.M2) else "",
                row.M3 if pd.notna(row.M3) else "",
                row.M4 if pd.notna(row.M4) else "",
                row.M5 if pd.notna(row.M5) else "",
                row.M6 if pd.notna(row.M6) else "",
                row.M7 if pd.notna(row.M7) else "",
                row.M8 if pd.notna(row.M8) else "",
                row.M9 if pd.notna(row.M9) else "",
                id_15, id_23, device_id, gap_str, prev_id_str
            ])
            
            # Track entities
            unique_customers.add(cust_id)
            unique_cards.add((card_id, cust_id))
            
            # Write edges
            if (cust_id, card_id) not in seen_owns:
                w_e_owns.writerow([cust_id, card_id])
                seen_owns.add((cust_id, card_id))
                
            w_e_made.writerow([card_id, txn_id])
            
            if prev_id_str:
                w_e_next.writerow([prev_id_str, txn_id, gap_str])
                
            if device_id:
                w_e_dev.writerow([txn_id, device_id])
                
            if addr1_str:
                w_e_bill.writerow([txn_id, addr1_str])
                unique_regions.add(addr1_str)
                
            if p_email:
                w_e_mail.writerow([txn_id, p_email])
                unique_emails.add(p_email)
                
            total_txns += 1
            
    # Close all open files
    f_v_txn.close()
    f_e_owns.close()
    f_e_made.close()
    f_e_next.close()
    f_e_dev.close()
    f_e_bill.close()
    f_e_mail.close()
    
    print(f"Streamed {total_txns} transactions in {time.time() - t0:.2f}s.")
    
    # Write entity vertex files
    print("Writing entity vertex files...")
    # v_customer.csv
    with open(os.path.join(PROCESSED_DIR, "v_customer.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["customer_id"])
        for c in sorted(unique_customers):
            w.writerow([c])
            
    # v_card.csv
    with open(os.path.join(PROCESSED_DIR, "v_card.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["card_id", "customer_id"])
        for card_id, cust_id in sorted(unique_cards):
            w.writerow([card_id, cust_id])
            
    # Optional helper vertex files for TigerGraph
    with open(os.path.join(PROCESSED_DIR, "v_billing_region.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["addr1"])
        for r in sorted(unique_regions):
            w.writerow([r])
            
    with open(os.path.join(PROCESSED_DIR, "v_email_domain.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["email_domain"])
        for e in sorted(unique_emails):
            w.writerow([e])
            
    print(f"Saved {len(unique_customers)} customers, {len(unique_cards)} cards, {len(unique_regions)} regions, {len(unique_emails)} email domains.")


def main():
    tx_path = os.path.join(RAW_DIR, "transactions.csv")
    id_path = os.path.join(RAW_DIR, "identity.csv")
    cc_path = os.path.join(RAW_DIR, "closed_cases_history.csv")
    
    assert os.path.exists(tx_path), f"Missing {tx_path}"
    assert os.path.exists(id_path), f"Missing {id_path}"
    assert os.path.exists(cc_path), f"Missing {cc_path}"
    
    print("=== STARTING DATA PREPARATION (PHASE 1) ===")
    t_start = time.time()
    
    # Step 1: Pass 1 to build card_ids and sequence
    txn_card_dict, txn_prev_dict, txn_gap_dict = derive_card_mappings(tx_path)
    
    # Step 2: Process identity.csv
    id_lookup = process_identity(id_path)
    
    # Step 3: Process closed cases
    process_closed_cases(cc_path)
    
    # Step 4: Pass 2 to stream transactions and edges
    process_transactions_and_edges(tx_path, txn_card_dict, txn_prev_dict, txn_gap_dict, id_lookup)
    
    print(f"=== DATA PREPARATION COMPLETE IN {time.time() - t_start:.2f}s ===")


if __name__ == "__main__":
    main()
