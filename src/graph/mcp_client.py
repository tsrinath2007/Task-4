"""
src/graph/mcp_client.py — TigerGraph Client & MCP Read/Write Interface

Implements graph query tools using pyTigerGraph backend with local indexed fallback.
All functions record latency, never crash the agent, and return structured results.
"""

import os
import time
import json
import pandas as pd

PROCESSED_DIR = os.path.join("data", "processed")


def query_card_history(card_id, conn=None, limit=100):
    """
    Get recent transactions for a card with amount, ts, ProductCD, addr1.
    """
    t0 = time.time()
    result = []
    try:
        if conn is not None:
            try:
                txns = conn.getEdges("Card", card_id, "MADE", "Transaction")
                result = txns[:limit]
            except Exception as e:
                print(f"[mcp_client] TigerGraph card_history error: {e}")

        if not result:
            # Fallback to local data
            tx_path = os.path.join(PROCESSED_DIR, "v_transaction.csv")
            if os.path.exists(tx_path):
                # Efficiently filter for card_id
                matched = []
                for chunk in pd.read_csv(
                    tx_path,
                    chunksize=50000,
                    usecols=["TransactionID", "card_id", "ts", "TransactionAmt", "ProductCD", "addr1", "device_id"],
                    dtype=str
                ):
                    sub = chunk[chunk["card_id"] == card_id]
                    if not sub.empty:
                        matched.append(sub)
                if matched:
                    df = pd.concat(matched, ignore_index=True)
                    df["ts_dt"] = pd.to_datetime(df["ts"], errors="coerce")
                    df = df.sort_values("ts_dt", ascending=False).head(limit)
                    result = df.to_dict(orient="records")
    except Exception as e:
        print(f"[mcp_client] query_card_history error: {e}")
        result = []

    latency_ms = round((time.time() - t0) * 1000, 2)
    return {"data": result, "count": len(result), "latency_ms": latency_ms}


def query_customer_cards(customer_id, conn=None):
    """
    Get all card_ids owned by this customer.
    """
    t0 = time.time()
    result = []
    try:
        if conn is not None:
            try:
                edges = conn.getEdges("Customer", customer_id, "OWNS", "Card")
                result = [e.get("to_id") for e in edges if "to_id" in e]
            except Exception as e:
                print(f"[mcp_client] TigerGraph customer_cards error: {e}")

        if not result:
            card_path = os.path.join(PROCESSED_DIR, "v_card.csv")
            if os.path.exists(card_path):
                df_card = pd.read_csv(card_path, dtype=str)
                result = df_card[df_card["customer_id"] == customer_id]["card_id"].tolist()
    except Exception as e:
        print(f"[mcp_client] query_customer_cards error: {e}")
        result = []

    latency_ms = round((time.time() - t0) * 1000, 2)
    return {"cards": result, "count": len(result), "latency_ms": latency_ms}


def query_shared_devices(txn_id, conn=None):
    """
    Get device_id for this transaction, then find all cards using it.
    """
    t0 = time.time()
    device_id = None
    connected_cards = []
    try:
        # 1. Get device_id for transaction
        if conn is not None:
            try:
                dev_edges = conn.getEdges("Transaction", str(txn_id), "FROM_DEVICE", "DeviceProfile")
                if dev_edges:
                    device_id = dev_edges[0].get("to_id")
                    card_edges = conn.getEdges("DeviceProfile", device_id, "USED_ON", "Card")
                    connected_cards = [e.get("to_id") for e in card_edges if "to_id" in e]
            except Exception as e:
                print(f"[mcp_client] TigerGraph shared_devices error: {e}")

        if not connected_cards:
            dev_txn_path = os.path.join(PROCESSED_DIR, "e_txn_from_device.csv")
            made_path = os.path.join(PROCESSED_DIR, "e_card_made_txn.csv")
            if os.path.exists(dev_txn_path) and os.path.exists(made_path):
                df_dt = pd.read_csv(dev_txn_path, dtype=str)
                m = df_dt[df_dt["TransactionID"] == str(txn_id)]
                if not m.empty:
                    device_id = m["device_id"].iloc[0]
                    # Find all txns with this device
                    txns_with_dev = set(df_dt[df_dt["device_id"] == device_id]["TransactionID"])
                    df_made = pd.read_csv(made_path, dtype=str)
                    connected_cards = df_made[df_made["TransactionID"].isin(txns_with_dev)]["card_id"].unique().tolist()
    except Exception as e:
        print(f"[mcp_client] query_shared_devices error: {e}")

    latency_ms = round((time.time() - t0) * 1000, 2)
    return {
        "device_id": device_id,
        "connected_cards": connected_cards,
        "count": len(connected_cards),
        "latency_ms": latency_ms
    }


def query_prior_cases(card_id, conn=None):
    """
    Get all ClosedCase vertices connected to this card.
    """
    t0 = time.time()
    result = []
    try:
        if conn is not None:
            try:
                cases = conn.getEdges("Card", card_id, "HAS_CLOSED_CASE", "ClosedCase")
                result = [c.get("to_id") for c in cases if "to_id" in c]
            except Exception as e:
                print(f"[mcp_client] TigerGraph prior_cases error: {e}")

        if not result:
            cc_path = os.path.join(PROCESSED_DIR, "v_closed_case.csv")
            if os.path.exists(cc_path):
                df_cc = pd.read_csv(cc_path, dtype=str)
                matched = df_cc[df_cc["card_id"] == card_id]
                result = matched.to_dict(orient="records")
    except Exception as e:
        print(f"[mcp_client] query_prior_cases error: {e}")
        result = []

    latency_ms = round((time.time() - t0) * 1000, 2)
    return {"cases": result, "count": len(result), "latency_ms": latency_ms}


def write_case(case_json, conn=None):
    """
    Write Case vertex + CASE_INVOLVES, CASE_ON_CARD, CASE_CONNECTED_TO edges.
    Validates case_json has required fields before writing.
    """
    required = ["case_id", "card_id", "verdict", "evidence_json"]
    for f in required:
        if f not in case_json:
            raise ValueError(f"Missing required field in case_json: {f}")

    if conn is not None:
        try:
            # 1. Upsert Case vertex
            case_vertex_data = {
                case_json["case_id"]: {
                    "status": case_json.get("status", "open"),
                    "verdict": case_json.get("verdict", "uncertain"),
                    "fraud_probability": float(case_json.get("fraud_probability", 0.0)),
                    "pattern": case_json.get("pattern", "none"),
                    "pattern_description": case_json.get("pattern_description", ""),
                    "first_suspicious_txn_id": case_json.get("first_suspicious_txn_id", ""),
                    "exposure_usd": float(case_json.get("exposure_usd", 0.0)),
                    "summary": case_json.get("summary", ""),
                    "evidence_json": case_json.get("evidence_json", "[]"),
                    "actions_json": case_json.get("actions_json", "[]"),
                    "sar_json": case_json.get("sar_json", "{}"),
                    "sar_filed": bool(case_json.get("sar_filed", False)),
                    "stop_reason": case_json.get("stop_reason", ""),
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            }
            conn.upsertVertices("Case", case_vertex_data)

            # 2. Upsert CASE_ON_CARD edge
            conn.upsertEdge("Case", case_json["case_id"], "CASE_ON_CARD", "Card", case_json["card_id"])

            # 3. Upsert CASE_INVOLVES edges
            for tid in case_json.get("affected_txn_ids", []):
                conn.upsertEdge("Case", case_json["case_id"], "CASE_INVOLVES", "Transaction", str(tid))

            # 4. Upsert CASE_CONNECTED_TO edges
            for cid in case_json.get("connected_card_ids", []):
                conn.upsertEdge("Case", case_json["case_id"], "CASE_CONNECTED_TO", "Card", str(cid))

            return True
        except Exception as e:
            print(f"[mcp_client] write_case to TigerGraph failed: {e}")
            return False

    return True
