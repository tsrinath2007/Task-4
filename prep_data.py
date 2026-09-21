"""
prep_data.py — Data Preparation for TigerGraph HHGOA Fraud Investigation

Rules:
1. Never load 708MB transactions.csv fully into RAM (stream in chunks).
2. Never modify data/raw/.
3. Preserve card_id derivation:
   Within each customer, distinct card2 values = distinct cards.
   NaN card2 sorts first (K1), then ascending numeric (K2, K3...).
   Verify: C08623-K2 owns transaction 3530164.
"""

import os
import gc
import pandas as pd
import numpy as np

RAW_DIR = os.path.join("data", "raw")
PROCESSED_DIR = os.path.join("data", "processed")


def build_card_mapping(transactions_path):
    """
    Pass 1 over transactions.csv to collect unique (customer_id, card2) pairs.
    Derives card_id mapping for all customers deterministically.
    """
    print("Building card_id mapping from transactions (Pass 1)...")
    customer_card2_map = {}

    for chunk in pd.read_csv(
        transactions_path,
        chunksize=100000,
        usecols=["customer_id", "card2"]
    ):
        grouped = chunk.groupby("customer_id")["card2"].unique()
        for cust_id, c2_vals in grouped.items():
            if cust_id not in customer_card2_map:
                customer_card2_map[cust_id] = set()
            for v in c2_vals:
                if pd.isna(v):
                    customer_card2_map[cust_id].add("NaN")
                else:
                    customer_card2_map[cust_id].add(float(v))

    # Build deterministic mapping
    card_mapping = {}
    for cust_id, c2_set in customer_card2_map.items():
        has_nan = "NaN" in c2_set
        numeric_vals = sorted([x for x in c2_set if x != "NaN"])
        
        sorted_vals = (["NaN"] if has_nan else []) + numeric_vals
        for i, val in enumerate(sorted_vals):
            card_mapping[(cust_id, val)] = f"{cust_id}-K{i+1}"

    print(f"Total card mappings generated: {len(card_mapping)}")
    return card_mapping


def assign_card_id(cust_id, c2_val, card_mapping):
    key = (cust_id, "NaN" if pd.isna(c2_val) else float(c2_val))
    return card_mapping.get(key, f"{cust_id}-K1")


if __name__ == "__main__":
    tx_path = os.path.join(RAW_DIR, "transactions.csv")
    if os.path.exists(tx_path):
        mapping = build_card_mapping(tx_path)
        # Verify C08623-K2 owns 3530164 (which has card2=470.0)
        c08623_k2 = assign_card_id("C08623", 470.0, mapping)
        print(f"Verification: Customer C08623 with card2=470.0 -> {c08623_k2}")
        assert c08623_k2 == "C08623-K2", f"Expected C08623-K2, got {c08623_k2}"
        print("Card ID derivation check passed.")
