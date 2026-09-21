"""
src/memory/graph_memory.py — Graph Adjacency Case Retrieval

Performs 1-hop and 2-hop traversals to find closed cases connected to
the current investigation entities (device, region, customer).
Supports both pyTigerGraph connection and fast local indexed fallback.
"""

import os
import pandas as pd

PROCESSED_DIR = os.path.join("data", "processed")
CASES_PATH = os.path.join(PROCESSED_DIR, "v_closed_case.csv")
CARDS_PATH = os.path.join(PROCESSED_DIR, "v_card.csv")
DEV_TXN_PATH = os.path.join(PROCESSED_DIR, "e_txn_from_device.csv")
MADE_TXN_PATH = os.path.join(PROCESSED_DIR, "e_card_made_txn.csv")
BILL_TXN_PATH = os.path.join(PROCESSED_DIR, "e_txn_billed_in.csv")

_DF_CASES = None
_DF_CARDS = None
_DF_DEV_TXN = None
_DF_MADE = None
_DF_BILL = None


def _load_data():
    global _DF_CASES, _DF_CARDS, _DF_DEV_TXN, _DF_MADE, _DF_BILL
    if _DF_CASES is None:
        _DF_CASES = pd.read_csv(CASES_PATH)
        _DF_CARDS = pd.read_csv(CARDS_PATH)
        _DF_DEV_TXN = pd.read_csv(DEV_TXN_PATH)
        _DF_MADE = pd.read_csv(MADE_TXN_PATH)
        _DF_BILL = pd.read_csv(BILL_TXN_PATH)


def get_cases_by_device(device_id, conn=None):
    """
    Finds closed cases connected to cards that used device_id.
    Traversal: DeviceProfile -> Transaction -> Card -> ClosedCase
    """
    if not device_id or str(device_id).strip() == "" or str(device_id) == "nan":
        return []

    dev_str = str(device_id).strip()

    # Live TigerGraph traversal
    if conn is not None:
        try:
            # Query cards using this device
            res = conn.runInstalledQuery("shared_device_lookup", {"device_id": dev_str})
            if res:
                return res
        except Exception:
            pass

    # Local graph traversal fallback
    _load_data()
    # 1. Transactions using this device
    dev_txns = set(_DF_DEV_TXN[_DF_DEV_TXN["device_id"] == dev_str]["TransactionID"])
    if not dev_txns:
        return []

    # 2. Cards that made those transactions
    cards = set(_DF_MADE[_DF_MADE["TransactionID"].isin(dev_txns)]["card_id"])
    if not cards:
        return []

    # 3. Closed cases on those cards
    matched = _DF_CASES[_DF_CASES["card_id"].isin(cards)]
    results = []
    for _, row in matched.iterrows():
        results.append({
            "case_id": str(row["case_id"]),
            "outcome": str(row["outcome"]),
            "pattern": str(row["pattern"]),
            "analyst_notes": str(row["analyst_notes"]) if pd.notna(row["analyst_notes"]) else "",
            "similarity": 0.0,
            "retrieval_reason": "device_match",
            "entity_ids": [dev_str, str(row["card_id"])]
        })
    return results


def get_cases_by_region(addr1, conn=None):
    """
    Finds closed cases connected to cards that transacted in this billing region.
    Traversal: BillingRegion -> Transaction -> Card -> ClosedCase
    """
    if not addr1 or str(addr1).strip() == "" or str(addr1) == "nan":
        return []

    region_str = str(addr1).strip()

    # Local graph traversal fallback
    _load_data()
    # 1. Transactions in this region
    reg_txns = set(_DF_BILL[_DF_BILL["addr1"].astype(str) == region_str]["TransactionID"])
    if not reg_txns:
        return []

    # 2. Cards that made those transactions (limit sample for performance)
    sample_txns = list(reg_txns)[:500]
    cards = set(_DF_MADE[_DF_MADE["TransactionID"].isin(sample_txns)]["card_id"])
    if not cards:
        return []

    # 3. Closed cases on those cards
    matched = _DF_CASES[_DF_CASES["card_id"].isin(cards)]
    results = []
    for _, row in matched.head(10).iterrows():
        results.append({
            "case_id": str(row["case_id"]),
            "outcome": str(row["outcome"]),
            "pattern": str(row["pattern"]),
            "analyst_notes": str(row["analyst_notes"]) if pd.notna(row["analyst_notes"]) else "",
            "similarity": 0.0,
            "retrieval_reason": "region_match",
            "entity_ids": [region_str, str(row["card_id"])]
        })
    return results


def get_cases_by_customer(customer_id, conn=None):
    """
    Finds all prior closed cases for this customer directly.
    Traversal: Customer -> Card -> ClosedCase
    """
    if not customer_id or str(customer_id).strip() == "":
        return []

    cust_str = str(customer_id).strip()
    _load_data()

    matched = _DF_CASES[_DF_CASES["customer_id"] == cust_str]
    results = []
    for _, row in matched.iterrows():
        results.append({
            "case_id": str(row["case_id"]),
            "outcome": str(row["outcome"]),
            "pattern": str(row["pattern"]),
            "analyst_notes": str(row["analyst_notes"]) if pd.notna(row["analyst_notes"]) else "",
            "similarity": 0.0,
            "retrieval_reason": "customer_match",
            "entity_ids": [cust_str, str(row["card_id"])]
        })
    return results
