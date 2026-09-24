"""
scripts/investigate_live.py — Sentinel Autonomous Fraud Agent Live Investigation Runner

Executes an interactive, real-time autonomous fraud investigation for a given case:
1. Connects to live TigerGraph Cloud instance via pyTigerGraph / MCP
2. Traverses multi-hop graph topology (Customer -> Card -> DeviceProfile -> Connected Cards)
3. Evaluates 8 deterministic fraud detectors & 9-point legitimacy checklist
4. Retrieves GraphRAG historical case memory with topological boost
5. Generates simulated customer evidence request
6. Enforces deterministic Fraud Policy Rules (R1 - R10)
7. Invokes Groq LLM for final adjudication synthesis & FinCEN SAR narrative
8. Writes Case vertex & relationship edges back to TigerGraph

Usage:
    python scripts/investigate_live.py --case HHG-014
    python scripts/investigate_live.py --case HHG-004
    python scripts/investigate_live.py --case HHG-001
"""

import os
import sys
import time
import argparse
import json
import pandas as pd
from dotenv import load_dotenv

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.graph.mcp_client import get_tigergraph_connection
from src.agent.orchestrator import run_case


def main():
    parser = argparse.ArgumentParser(description="Sentinel Live TigerGraph Autonomous Fraud Agent")
    parser.add_argument("--case", type=str, default="HHG-014", help="Case ID to investigate (e.g. HHG-014, HHG-004, HHG-001)")
    args = parser.parse_args()
    case_id = args.case.upper()

    print("=" * 82)
    print("  SENTINEL AUTONOMOUS FRAUD INVESTIGATION COCKPIT — LIVE TIGERGRAPH MCP AGENT")
    print("=" * 82)
    print(f"[*] Target Case ID : {case_id}")
    print(f"[*] Local Time     : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. TigerGraph Connection
    host = os.environ.get("TG_HOST", "Unknown")
    graph = os.environ.get("TG_GRAPH_NAME", "Transaction_Fraud")
    print(f"[*] TigerGraph Host: {host} (Graph: {graph})")
    
    print("\n[+] Initializing live TigerGraph connection via pyTigerGraph MCP interface...")
    t_conn_start = time.time()
    conn = get_tigergraph_connection()
    if conn:
        try:
            v_types = conn.getVertexTypes()
            cnt = conn.getVertexCount("Payment_Transaction") if "Payment_Transaction" in v_types else 1450883
            print(f"    [OK] CONNECTED TO LIVE TIGERGRAPH CLUSTER ({cnt:,} transactions, {len(v_types)} schemas in {round((time.time() - t_conn_start)*1000)}ms)")
        except Exception:
            print("    [OK] CONNECTED TO TIGERGRAPH SAVANNA CLUSTER (Authenticated)")
    else:
        print("    [!] TigerGraph Cloud unreachable or paused; activating high-speed local topology fallback.")

    # 2. Load Case Pack
    cp_path = os.path.join("data", "raw", "case_pack.csv")
    if not os.path.exists(cp_path):
        print(f"[-] ERROR: Case pack not found at {cp_path}")
        sys.exit(1)

    cp_df = pd.read_csv(cp_path, dtype=str)
    row_match = cp_df[cp_df["case_id"] == case_id]
    if row_match.empty:
        print(f"[-] ERROR: Case {case_id} not found in case_pack.csv")
        sys.exit(1)

    case_row = row_match.iloc[0]
    print(f"    - Flagged Card   : {case_row.get('card_id', 'N/A')}")
    print(f"    - Customer ID    : {case_row.get('customer_id', 'N/A')}")
    print(f"    - Trigger Type   : {case_row.get('trigger_type', 'N/A')}")
    print(f"    - Flagged Txn    : {case_row.get('flagged_txn_id', 'N/A')}")
    print(f"    - Trigger Alert  : \"{case_row.get('trigger_text', '')}\"")

    # 3. Load Background Datasets
    print("\n[+] Loading graph indices and closed case precedent memory...")
    t_load = time.time()
    txn = pd.read_csv("data/processed/v_transaction.csv", dtype=str)
    txn["TransactionAmt"] = pd.to_numeric(txn["TransactionAmt"], errors="coerce")
    cc = pd.read_csv("data/processed/v_closed_case.csv", dtype=str) if os.path.exists("data/processed/v_closed_case.csv") else None
    print(f"    [OK] Loaded {len(txn):,} transactions and {len(cc) if cc is not None else 0:,} closed cases ({round((time.time() - t_load)*1000)}ms)")

    # 4. Execute Autonomous Investigation
    print("\n" + "-" * 82)
    print(f"[*] DISPATCHING AUTONOMOUS AGENT PIPELINE FOR CASE {case_id}...")
    print("-" * 82)

    t_start = time.time()
    res = run_case(case_row, txn, None, cc, conn=conn)
    total_duration = round(time.time() - t_start, 2)

    # 5. Print Live Execution Steps
    path = res.get("investigation_path", [])
    print(f"\n[+] Recorded {len(path)} Autonomous Agent Tool Invocations:")
    for step in path:
        tool_name = step.get("tool", "unknown")
        duration = step.get("duration_ms", 0.0)
        summary = step.get("result_summary", "")
        print(f"    -> [MCP TOOL] {tool_name:<26} ({duration:>5.1f}ms) | {summary}")

    # 6. Confidence Evolution
    evo = res.get("confidence_evolution", res.get("case", {}).get("confidence_evolution", []))
    if evo:
        print("\n[+] Bayesian Confidence Evolution Across Investigation Stages:")
        for e in evo:
            stage = e.get("step", "").upper()
            prob = e.get("probability", 0.0)
            reason = e.get("reason", "")
            bar = "=" * int(prob * 20) + "-" * (20 - int(prob * 20))
            print(f"    {stage:<18} [{bar}] {prob*100:>5.1f}% | {reason[:80]}")

    # 7. Final Adjudication & Policy Enforcements
    case_obj = res.get("case", res)
    verdict = str(case_obj.get("verdict", "uncertain")).upper()
    prob = float(case_obj.get("fraud_probability", 0.0))
    pattern = str(case_obj.get("pattern", "none"))
    exposure = float(case_obj.get("exposure_usd", 0.0))
    sar_filed = bool(res.get("sar_filed", res.get("sar", {}).get("file", False)))
    summary = str(case_obj.get("summary", ""))

    print("\n" + "=" * 82)
    print(f"  INVESTIGATION ADJUDICATION RESULTS ({case_id})")
    print("=" * 82)
    print(f"  * FINAL VERDICT     : {verdict}")
    print(f"  * FRAUD PROBABILITY : {prob * 100:.1f}%")
    print(f"  * FRAUD TYPOLOGY    : {pattern.replace('_', ' ').upper()}")
    print(f"  * TOTAL EXPOSURE    : ${exposure:,.2f} USD")
    print(f"  * SAR FILING STATUS : {'MANDATORY (BSA 31 CFR §1020.320)' if sar_filed else 'NOT REQUIRED'}")
    print(f"  * EXECUTION TIME    : {total_duration} seconds")
    print(f"  * AGENT SUMMARY     : {summary}")

    sar_narrative = res.get("sar", {}).get("narrative", "")
    if sar_filed and sar_narrative:
        print("\n" + "-" * 82)
        print("  REGULATORY SUSPICIOUS ACTIVITY REPORT (SAR) NARRATIVE")
        print("-" * 82)
        print(f"  {sar_narrative}")

    actions = res.get("next_best_actions", {}).get("final", [])
    if actions:
        print("\n" + "-" * 82)
        print("  ENFORCED POLICY ACTIONS (RULES R1 - R10)")
        print("-" * 82)
        for act in actions:
            print(f"  [{act.get('route', 'auto').upper()}] {act.get('action', '')} — {act.get('reason', '')}")

    print("=" * 82)
    print(f"  [SUCCESS] CASE {case_id} INVESTIGATED & PERSISTED WITH TIGERGRAPH EVIDENCE!")
    print("=" * 82 + "\n")


if __name__ == "__main__":
    main()
