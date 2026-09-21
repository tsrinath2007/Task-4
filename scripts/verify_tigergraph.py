"""
scripts/verify_tigergraph.py — TigerGraph Verification for HHGOA Fraud Investigation (Phase 3)

Verification Checks:
1. C08623-K2 exists as a Card vertex
2. Transaction 3530164 is connected to C08623-K2 via MADE edge
3. Customer C08623 owns at least 2 cards
4. At least 1 cleared ClosedCase exists (outcome='cleared')
5. At least 1 DeviceProfile vertex exists
6. Card C08623-K2 has at least 10 Transaction neighbors
7. Total vertex counts match processed file row counts

Connects via pyTigerGraph using environment variables:
TG_HOST, TG_USERNAME, TG_PASSWORD, TG_GRAPH_NAME
"""

import os
import sys
import json
import pandas as pd

try:
    import pyTigerGraph as tg
except ImportError:
    tg = None

PROCESSED_DIR = os.path.join("data", "processed")


def verify_live_tigergraph(host, graph_name, username, password):
    """
    Execute the 7 verification checks against a live TigerGraph instance via pyTigerGraph.
    """
    print(f"Connecting to TigerGraph at {host} (Graph: {graph_name})...")
    conn = tg.TigerGraphConnection(
        host=host,
        graphname=graph_name,
        username=username,
        password=password
    )
    
    try:
        secret = conn.createSecret()
        token = conn.getToken(secret)
    except Exception as e:
        print(f"Note on token generation: {e}")

    results = {}

    # 1. C08623-K2 exists as Card vertex
    print("\n--- Check 1: Card C08623-K2 exists ---")
    try:
        cards = conn.getVerticesById("Card", "C08623-K2")
        c1_pass = len(cards) > 0
    except Exception:
        # Fallback to query
        res = conn.runInstalledQuery("check_card_exists", {"cardId": "C08623-K2"})
        c1_pass = res[0].get("exists", False) if res else False
    results["Check 1: C08623-K2 exists as Card"] = c1_pass

    # 2. Transaction 3530164 connected to C08623-K2 via MADE edge
    print("\n--- Check 2: Transaction 3530164 connected via MADE edge ---")
    try:
        edges = conn.getEdges("Card", "C08623-K2", "MADE", "Transaction", "3530164")
        c2_pass = len(edges) > 0
    except Exception:
        res = conn.runInstalledQuery("check_txn_connected", {"cardId": "C08623-K2", "txnId": "3530164"})
        c2_pass = res[0].get("connected", False) if res else False
    results["Check 2: Transaction 3530164 connected to C08623-K2 via MADE"] = c2_pass

    # 3. Customer C08623 owns at least 2 cards
    print("\n--- Check 3: Customer C08623 owns at least 2 cards ---")
    try:
        edges = conn.getEdges("Customer", "C08623", "OWNS")
        c3_pass = len(edges) >= 2
    except Exception:
        res = conn.runInstalledQuery("check_customer_cards", {"custId": "C08623"})
        c3_pass = res[0].get("has_multiple_cards", False) if res else False
    results["Check 3: Customer C08623 owns at least 2 cards"] = c3_pass

    # 4. At least 1 cleared ClosedCase exists (outcome='cleared')
    print("\n--- Check 4: Cleared ClosedCase exists (outcome='cleared') ---")
    try:
        res = conn.runInstalledQuery("check_cleared_cases")
        c4_pass = res[0].get("cleared_exists", False) if res else False
    except Exception:
        c4_pass = False
    results["Check 4: Cleared ClosedCase exists (outcome='cleared')"] = c4_pass

    # 5. At least 1 DeviceProfile vertex exists
    print("\n--- Check 5: DeviceProfile vertex exists ---")
    try:
        dev_count = conn.getVertexCount("DeviceProfile")
        c5_pass = dev_count > 0
    except Exception:
        res = conn.runInstalledQuery("check_device_profile_exists")
        c5_pass = res[0].get("device_exists", False) if res else False
    results["Check 5: At least 1 DeviceProfile vertex exists"] = c5_pass

    # 6. Card C08623-K2 has at least 10 Transaction neighbors
    print("\n--- Check 6: Card C08623-K2 has >= 10 Transaction neighbors ---")
    try:
        edges = conn.getEdges("Card", "C08623-K2", "MADE")
        c6_pass = len(edges) >= 10
    except Exception:
        res = conn.runInstalledQuery("check_card_txns_count", {"cardId": "C08623-K2"})
        c6_pass = res[0].get("has_min_10_txns", False) if res else False
    results["Check 6: Card C08623-K2 has >= 10 Transaction neighbors"] = c6_pass

    # 7. Total vertex counts match processed file row counts
    print("\n--- Check 7: Total vertex counts match processed data ---")
    expected_counts = {
        "Customer": 13553,
        "Card": 14524,
        "Transaction": 590742,
        "DeviceProfile": 9706,
        "BillingRegion": 332,
        "EmailDomain": 59,
        "ClosedCase": 5565
    }
    
    c7_pass = True
    for v_type, expected in expected_counts.items():
        try:
            actual = conn.getVertexCount(v_type)
            print(f"  {v_type}: actual={actual:,}, expected={expected:,}")
            if actual != expected:
                c7_pass = False
        except Exception as e:
            print(f"  {v_type}: count check error ({e})")
            c7_pass = False
    results["Check 7: Total vertex counts match processed data"] = c7_pass

    return results


def verify_processed_data_baseline():
    """
    Verification against the local processed dataset (used for offline validation
    and regression testing before/alongside TigerGraph Savanna loading).
    """
    print("Verifying the 7 target rules directly on data/processed/ baseline...")
    results = {}

    # Check 1: C08623-K2 exists as Card
    df_card = pd.read_csv(os.path.join(PROCESSED_DIR, "v_card.csv"))
    c1 = (df_card["card_id"] == "C08623-K2").any()
    results["Check 1: C08623-K2 exists as Card"] = c1

    # Check 2: Transaction 3530164 connected to C08623-K2 via MADE edge
    df_made = pd.read_csv(os.path.join(PROCESSED_DIR, "e_card_made_txn.csv"))
    c2 = ((df_made["card_id"] == "C08623-K2") & (df_made["TransactionID"] == 3530164)).any()
    results["Check 2: Transaction 3530164 connected to C08623-K2 via MADE"] = c2

    # Check 3: Customer C08623 owns at least 2 cards
    df_owns = pd.read_csv(os.path.join(PROCESSED_DIR, "e_customer_owns_card.csv"))
    c3 = len(df_owns[df_owns["customer_id"] == "C08623"]) >= 2
    results["Check 3: Customer C08623 owns at least 2 cards"] = c3

    # Check 4: Cleared ClosedCase exists (outcome='cleared')
    df_cases = pd.read_csv(os.path.join(PROCESSED_DIR, "v_closed_case.csv"))
    cleared_count = (df_cases["outcome"] == "cleared").sum()
    c4 = cleared_count >= 1
    results["Check 4: Cleared ClosedCase exists (outcome='cleared')"] = c4

    # Check 5: At least 1 DeviceProfile vertex exists
    df_dev = pd.read_csv(os.path.join(PROCESSED_DIR, "v_device.csv"))
    c5 = len(df_dev) > 0
    results["Check 5: At least 1 DeviceProfile vertex exists"] = c5

    # Check 6: Card C08623-K2 has at least 10 Transaction neighbors
    c08623_k2_txns = len(df_made[df_made["card_id"] == "C08623-K2"])
    c6 = c08623_k2_txns >= 10
    results["Check 6: Card C08623-K2 has >= 10 Transaction neighbors"] = c6

    # Check 7: Total vertex counts match processed file row counts
    df_cust = pd.read_csv(os.path.join(PROCESSED_DIR, "v_customer.csv"))
    df_reg = pd.read_csv(os.path.join(PROCESSED_DIR, "v_billing_region.csv"))
    df_mail = pd.read_csv(os.path.join(PROCESSED_DIR, "v_email_domain.csv"))
    
    # We also check line count of v_transaction.csv without loading into RAM
    txn_count = 0
    with open(os.path.join(PROCESSED_DIR, "v_transaction.csv"), "r", encoding="utf-8") as f:
        next(f)
        for _ in f:
            txn_count += 1
            
    c7 = (
        len(df_cust) == 13553 and
        len(df_card) == 14524 and
        txn_count == 590742 and
        len(df_dev) == 9706 and
        len(df_reg) == 332 and
        len(df_mail) == 59 and
        len(df_cases) == 5565
    )
    results["Check 7: Total vertex counts match processed data"] = c7

    return results


def main():
    print("====================================================================")
    print("HHGOA / TigerGraph Phase 3 Verification Suite")
    print("====================================================================")

    tg_host = os.getenv("TG_HOST")
    tg_username = os.getenv("TG_USERNAME", "tigergraph")
    tg_password = os.getenv("TG_PASSWORD", "tigergraph")
    tg_graph = os.getenv("TG_GRAPH_NAME", "FraudInvestigationGraph")

    if tg_host:
        print(f"TG_HOST configured: {tg_host}")
        results = verify_live_tigergraph(tg_host, tg_graph, tg_username, tg_password)
    else:
        print("TG_HOST environment variable not set.")
        print("Running verification against processed dataset baseline...")
        print("(Set TG_HOST, TG_USERNAME, TG_PASSWORD, TG_GRAPH_NAME to test against live TigerGraph Savanna)")
        results = verify_processed_data_baseline()

    print("\n====================================================================")
    print("PHASE 3 VERIFICATION RESULTS SUMMARY")
    print("====================================================================")
    all_pass = True
    for check_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {check_name}")
        if not passed:
            all_pass = False

    print("====================================================================")
    if all_pass:
        print("ALL 7 VERIFICATIONS PASSED SUCCESSFULLY (7/7).")
    else:
        print("ONE OR MORE VERIFICATIONS FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
