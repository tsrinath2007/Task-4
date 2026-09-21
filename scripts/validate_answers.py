"""
scripts/validate_answers.py — Answer File Validator

Validates all 20 benchmark case answer files in cases/generated/
against the authoritative README Answer Format and Fraud Policy rules.
"""

import os
import sys
import json
import glob

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REQUIRED_TOP_KEYS = [
    "case_id", "case", "evidence_requests", "next_best_actions",
    "sar", "stop_reason", "tool_calls", "tokens", "latency_s"
]

REQUIRED_CASE_KEYS = [
    "status", "verdict", "fraud_probability", "pattern", "pattern_description",
    "affected_txn_ids", "first_suspicious_txn_id", "connected_card_ids",
    "connected_device_profiles", "exposure_usd", "evidence",
    "similar_prior_cases", "summary", "written_to_graph", "graph_case_id"
]

REQUIRED_SAR_KEYS = [
    "file", "reason", "narrative", "subjects", "total_amount_usd", "activity_dates"
]

REQUIRED_ACTIONS_KEYS = [
    "initial", "final", "what_changed"
]

VALID_VERDICTS = {"fraud", "legitimate", "uncertain"}
VALID_STATUSES = {"open", "closed_fraud", "closed_legitimate", "escalated"}
VALID_PATTERNS = {
    "card_testing", "card_not_present_fraud", "card_not_present_new_device",
    "out_of_region_use", "account_takeover", "undocumented", "none"
}


def validate_case_file(filepath):
    errors = []
    warnings = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [f"JSON Parse Error: {e}"], []

    # 1. Top-level keys
    for k in REQUIRED_TOP_KEYS:
        if k not in data:
            errors.append(f"Missing top-level key '{k}'")

    case = data.get("case", {})
    sar = data.get("sar", {})
    nba = data.get("next_best_actions", {})

    # 2. Case keys
    for k in REQUIRED_CASE_KEYS:
        if k not in case:
            errors.append(f"Missing case key '{k}'")

    # 3. SAR keys
    for k in REQUIRED_SAR_KEYS:
        if k not in sar:
            errors.append(f"Missing sar key '{k}'")

    # 4. Actions keys
    for k in REQUIRED_ACTIONS_KEYS:
        if k not in nba:
            errors.append(f"Missing next_best_actions key '{k}'")

    # 5. Value checks
    verdict = case.get("verdict")
    if verdict not in VALID_VERDICTS:
        errors.append(f"Invalid verdict '{verdict}' (must be one of {VALID_VERDICTS})")

    status = case.get("status")
    if status not in VALID_STATUSES:
        errors.append(f"Invalid status '{status}' (must be one of {VALID_STATUSES})")

    pattern = case.get("pattern")
    if pattern not in VALID_PATTERNS:
        errors.append(f"Invalid pattern '{pattern}' (must be one of {VALID_PATTERNS})")

    prob = case.get("fraud_probability", -1)
    if not (0.0 <= prob <= 1.0):
        errors.append(f"Invalid fraud_probability {prob} (must be in [0.0, 1.0])")

    if pattern == "undocumented" and not case.get("pattern_description"):
        errors.append("Pattern is 'undocumented' but pattern_description is empty")

    # 6. Policy consistency rules
    final_actions = nba.get("final", [])
    final_action_names = [a.get("action") for a in final_actions]
    initial_actions = nba.get("initial", [])
    initial_action_names = [a.get("action") for a in initial_actions]

    # Legitimate constraints
    if verdict == "legitimate":
        if case.get("affected_txn_ids"):
            errors.append("Verdict is legitimate but affected_txn_ids is not empty")
        if case.get("exposure_usd", 0.0) != 0.0:
            errors.append(f"Verdict is legitimate but exposure_usd is {case.get('exposure_usd')}")
        if sar.get("file") is not False:
            errors.append("Verdict is legitimate but sar.file is True")

    # SAR file agreement
    sar_file = sar.get("file", False)
    has_file_report = "FILE_REPORT" in final_action_names
    if sar_file != has_file_report:
        errors.append(f"sar.file ({sar_file}) does not agree with FILE_REPORT in final actions ({has_file_report})")

    # Routing rules
    for a in final_actions:
        act = a.get("action")
        route = a.get("route")
        if act == "FILE_REPORT" and route != "L2":
            errors.append(f"FILE_REPORT route is '{route}', must be L2")
        if act == "BLOCK_ALL_CARDS" and route != "L2":
            errors.append(f"BLOCK_ALL_CARDS route is '{route}', must be L2")
        if act == "BLOCK_CARD":
            exp = case.get("exposure_usd", 0.0)
            expected_route = "L2" if exp > 2500.0 else "L1"
            if route != expected_route:
                errors.append(f"BLOCK_CARD route is '{route}' for exposure ${exp:.2f}, expected '{expected_route}'")

    # Mutual exclusion: CLOSE_NO_FRAUD and BLOCK_CARD
    if "CLOSE_NO_FRAUD" in final_action_names and "BLOCK_CARD" in final_action_names:
        errors.append("CLOSE_NO_FRAUD and BLOCK_CARD both appear in final actions")

    # Initial action constraint: no BLOCK_CARD if evidence is pending
    if data.get("evidence_requests") and "BLOCK_CARD" in initial_action_names:
        errors.append("BLOCK_CARD appears in initial actions while evidence requests are pending")

    return errors, warnings


def main():
    print("=" * 70)
    print("HHGOA ANSWER VALIDATOR")
    print("=" * 70)

    gen_dir = os.path.join("cases", "generated")
    expected_cases = [f"HHG-{i:03d}" for i in range(1, 21)]

    total_passed = 0
    total_failed = 0
    all_errors = {}

    for cid in expected_cases:
        filepath = os.path.join(gen_dir, f"{cid}.json")
        if not os.path.exists(filepath):
            total_failed += 1
            all_errors[cid] = ["File does not exist"]
            print(f"  [FAIL] {cid}: FILE MISSING")
            continue

        errors, warnings = validate_case_file(filepath)
        if errors:
            total_failed += 1
            all_errors[cid] = errors
            print(f"  [FAIL] {cid}: FAILED ({len(errors)} errors)")
            for err in errors:
                print(f"      - {err}")
        else:
            total_passed += 1
            print(f"  [PASS] {cid}: PASS")

    print("\n" + "=" * 70)
    print(f"VALIDATION SUMMARY: {total_passed}/20 PASSED, {total_failed}/20 FAILED")
    print("=" * 70)

    if total_failed == 0:
        print("ALL 20 CASE FILES MEET SPECIFICATIONS!")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
