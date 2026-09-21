"""
scripts/run_benchmark.py — Autonomous Fraud Investigation Benchmark Runner

Executes the full 20-case benchmark from data/raw/case_pack.csv.
- Sorts cases chronologically by opened_at (HHG-014 runs before Dec cases)
- Overwrites cases/generated/*.json
- Adds time.sleep(2) between cases to respect API rate limits
- Catches per-case exceptions and continues execution
- Outputs benchmark_summary.json with comprehensive metrics
"""

import os
import sys
import json
import time
import glob
import traceback
import pandas as pd

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.agent.orchestrator import run_case


def main():
    print("=" * 70)
    print("HHGOA BENCHMARK RUNNER — 20-CASE EXAM")
    print("=" * 70)

    start_bench_time = time.time()
    out_dir = os.path.join("cases", "generated")
    os.makedirs(out_dir, exist_ok=True)

    # 1. Load data
    print("\n[1/3] Loading processed datasets into memory...")
    t0 = time.time()
    txn_path = os.path.join("data", "processed", "v_transaction.csv")
    idf_path = os.path.join("data", "raw", "identity.csv")
    cc_path = os.path.join("data", "processed", "v_closed_case.csv")
    cp_path = os.path.join("data", "raw", "case_pack.csv")

    txn = pd.read_csv(txn_path, dtype=str)
    txn["TransactionAmt"] = pd.to_numeric(txn["TransactionAmt"], errors="coerce")
    idf = pd.read_csv(idf_path, dtype=str) if os.path.exists(idf_path) else None
    cc = pd.read_csv(cc_path, dtype=str) if os.path.exists(cc_path) else None
    cp = pd.read_csv(cp_path, dtype=str)

    print(f"Loaded datasets in {time.time() - t0:.2f}s:")
    print(f"  - Transactions: {len(txn):,} rows")
    print(f"  - Identity: {len(idf):,} rows" if idf is not None else "  - Identity: None")
    print(f"  - Closed Cases: {len(cc):,} rows" if cc is not None else "  - Closed Cases: None")
    print(f"  - Benchmark Cases: {len(cp)} cases")

    # 2. Sort cases chronologically by opened_at
    print("\n[2/3] Sorting cases chronologically by opened_at...")
    cp["opened_at_dt"] = pd.to_datetime(cp["opened_at"])
    cp_sorted = cp.sort_values("opened_at_dt").reset_index(drop=True)

    print("Execution order:")
    for idx, row in cp_sorted.iterrows():
        print(f"  {idx+1:2d}. {row['case_id']} (opened: {row['opened_at']}, trigger: {row['trigger_type']})")

    # 3. Execute benchmark
    print("\n[3/3] Running autonomous investigations...")
    total_cases = len(cp_sorted)
    completed = 0
    failed = 0
    results_summary = []
    verdicts = {"fraud": 0, "legitimate": 0, "uncertain": 0}
    patterns = {}
    total_exposure = 0.0
    total_tool_calls = 0
    total_tokens = 0
    sar_count = 0

    for i, row in cp_sorted.iterrows():
        cid = row["case_id"]
        print(f"\nRunning {cid} ({i+1}/{total_cases})...")
        case_start = time.time()

        try:
            res = run_case(row, txn, idf, cc)
            case_dur = round(time.time() - case_start, 2)
            completed += 1

            v = res.get("verdict", res.get("case", {}).get("verdict", "unknown"))
            prob = res.get("fraud_probability", res.get("case", {}).get("fraud_probability", 0.0))
            pat = res.get("pattern", res.get("case", {}).get("pattern", "none"))
            sar = res.get("sar_filed", res.get("sar", {}).get("file", False))
            exp = res.get("exposure_usd", res.get("case", {}).get("exposure_usd", 0.0))
            tc = len(res.get("investigation_path", [])) or res.get("tool_calls", 0)
            tok = res.get("tokens", 0)

            verdicts[v] = verdicts.get(v, 0) + 1
            patterns[pat] = patterns.get(pat, 0) + 1
            if sar:
                sar_count += 1
            total_exposure += exp
            total_tool_calls += tc
            total_tokens += tok

            final_actions = [a["action"] for a in res.get("next_best_actions", {}).get("final", [])]
            print(f"  [OK] {cid} completed in {case_dur}s | verdict={v} (p={prob:.2f}) | pattern={pat} | SAR={sar}")
            print(f"    Actions: {final_actions}")

            results_summary.append({
                "case_id": cid,
                "opened_at": row["opened_at"],
                "trigger_type": row["trigger_type"],
                "card_id": row["card_id"],
                "verdict": v,
                "fraud_probability": prob,
                "pattern": pat,
                "exposure_usd": exp,
                "sar_filed": sar,
                "tool_calls": tc,
                "tokens": tok,
                "latency_s": case_dur,
                "status": "success"
            })

        except Exception as e:
            failed += 1
            case_dur = round(time.time() - case_start, 2)
            print(f"  [FAIL] {cid} FAILED after {case_dur}s: {e}")
            traceback.print_exc()
            results_summary.append({
                "case_id": cid,
                "opened_at": row["opened_at"],
                "status": "error",
                "error": str(e),
                "latency_s": case_dur
            })

        # Rate limiting delay between cases
        if i < total_cases - 1:
            time.sleep(2)

    total_bench_dur = round(time.time() - start_bench_time, 2)
    avg_latency = round(total_bench_dur / total_cases, 2) if total_cases > 0 else 0.0

    summary_payload = {
        "benchmark": "HHGOA Fraud Investigation Exam",
        "total_cases": total_cases,
        "completed_cases": completed,
        "failed_cases": failed,
        "total_runtime_s": total_bench_dur,
        "avg_latency_s": avg_latency,
        "verdict_counts": verdicts,
        "sar_filed_count": sar_count,
        "pattern_counts": patterns,
        "total_exposure_usd": round(total_exposure, 2),
        "total_tool_calls": total_tool_calls,
        "total_tokens": total_tokens,
        "cases": results_summary
    }

    # Write summary
    summary_path = os.path.join(out_dir, "benchmark_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fp:
        json.dump(summary_payload, fp, indent=2)

    root_summary_path = "benchmark_summary.json"
    with open(root_summary_path, "w", encoding="utf-8") as fp:
        json.dump(summary_payload, fp, indent=2)

    print("\n" + "=" * 70)
    print("BENCHMARK EXECUTION COMPLETE")
    print("=" * 70)
    print(f"Cases Completed: {completed}/{total_cases} (Failed: {failed})")
    print(f"Total Runtime: {total_bench_dur}s (Avg: {avg_latency}s/case)")
    print(f"Verdicts: Fraud={verdicts.get('fraud',0)}, Legitimate={verdicts.get('legitimate',0)}, Uncertain={verdicts.get('uncertain',0)}")
    print(f"SARs Filed: {sar_count}/{total_cases}")
    print(f"Total Exposure Identified: ${total_exposure:,.2f}")
    print(f"Summary written to: {summary_path}")


if __name__ == "__main__":
    main()
