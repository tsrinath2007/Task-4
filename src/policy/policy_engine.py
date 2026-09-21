"""
src/policy/policy_engine.py — Deterministic Fraud Policy Engine

Pure deterministic Python. No LLM. Same input always produces identical output.
Implements authoritative rules R1 to R10 and strict approval routing from README.

Approval Routes:
auto: ALLOW_TRANSACTION, MONITOR_CARD, MONITOR_CONNECTED_CARDS,
      WARN_CUSTOMER, VERIFY_WITH_CUSTOMER, STEP_UP_AUTH,
      GENERATE_REPORT, CREATE_CASE, ESCALATE_TO_ANALYST, CLOSE_NO_FRAUD
L1:   DECLINE_TRANSACTION
      BLOCK_CARD when case_exposure <= 2500
L2:   BLOCK_CARD when case_exposure > 2500
      BLOCK_ALL_CARDS (always)
      FILE_REPORT (always)
"""

VALID_ACTIONS = {
    "ALLOW_TRANSACTION": "auto",
    "DECLINE_TRANSACTION": "L1",
    "MONITOR_CARD": "auto",
    "MONITOR_CONNECTED_CARDS": "auto",
    "WARN_CUSTOMER": "auto",
    "VERIFY_WITH_CUSTOMER": "auto",
    "STEP_UP_AUTH": "auto",
    "BLOCK_CARD": "dynamic",  # L1 if <= 2500, L2 if > 2500
    "BLOCK_ALL_CARDS": "L2",
    "GENERATE_REPORT": "auto",
    "CREATE_CASE": "auto",
    "FILE_REPORT": "L2",
    "ESCALATE_TO_ANALYST": "auto",
    "CLOSE_NO_FRAUD": "auto"
}

ACTION_PRIORITY = {
    "ALLOW_TRANSACTION": 1,
    "DECLINE_TRANSACTION": 2,
    "STEP_UP_AUTH": 3,
    "VERIFY_WITH_CUSTOMER": 4,
    "WARN_CUSTOMER": 5,
    "BLOCK_CARD": 6,
    "BLOCK_ALL_CARDS": 7,
    "MONITOR_CARD": 8,
    "MONITOR_CONNECTED_CARDS": 9,
    "CREATE_CASE": 10,
    "FILE_REPORT": 11,
    "ESCALATE_TO_ANALYST": 12,
    "CLOSE_NO_FRAUD": 13,
    "GENERATE_REPORT": 14
}


def _get_block_card_route(exposure):
    return "L2" if float(exposure) > 2500.0 else "L1"


def _build_action(action_name, exposure=0.0):
    if action_name == "BLOCK_CARD":
        route = _get_block_card_route(exposure)
    else:
        route = VALID_ACTIONS.get(action_name, "auto")
    return {"action": action_name, "route": route}


def _enforce_hard_constraints(decision, recurring_charge=False):
    """
    Validates hard constraints and raises AssertionError if any rule is violated.
    """
    actions = decision["actions"]
    action_names = [a["action"] for a in actions]

    for a in actions:
        # Constraint 1: FILE_REPORT route must ALWAYS be L2
        if a["action"] == "FILE_REPORT":
            assert a["route"] == "L2", f"Hard constraint violation: FILE_REPORT route is {a['route']}, must be L2"

        # Constraint 2: BLOCK_ALL_CARDS route must ALWAYS be L2
        if a["action"] == "BLOCK_ALL_CARDS":
            assert a["route"] == "L2", f"Hard constraint violation: BLOCK_ALL_CARDS route is {a['route']}, must be L2"

    # Constraint 3: CLOSE_NO_FRAUD and BLOCK_CARD cannot both appear in same decision
    assert not ("CLOSE_NO_FRAUD" in action_names and "BLOCK_CARD" in action_names), \
        "Hard constraint violation: CLOSE_NO_FRAUD and BLOCK_CARD cannot both appear in same decision"

    # Constraint 4: R7 recurring_charge decisions must never include BLOCK_CARD
    if recurring_charge:
        assert "BLOCK_CARD" not in action_names, \
            "Hard constraint violation: R7 recurring_charge decisions must never include BLOCK_CARD"

    # Constraint 5: SAR (sar_required=True) must always be accompanied by FILE_REPORT action
    if decision["sar_required"]:
        assert "FILE_REPORT" in action_names, \
            "Hard constraint violation: sar_required=True but FILE_REPORT not in actions"

    # Constraint 6: FILE_REPORT must always set sar_required=True
    if "FILE_REPORT" in action_names:
        assert decision["sar_required"] is True, \
            "Hard constraint violation: FILE_REPORT in actions but sar_required is False"


def _order_and_dedupe_actions(actions_list):
    seen = set()
    deduped = []
    for a in actions_list:
        if a["action"] not in seen:
            seen.add(a["action"])
            deduped.append(a)
    deduped.sort(key=lambda x: ACTION_PRIORITY.get(x["action"], 99))
    return deduped


def decide_initial(
    verdict,
    fraud_probability,
    case_exposure,
    ring_exposure,
    connected_cards,
    pattern,
    trigger_type,
    recurring_charge=False,
    detector_results=None,
    confirmed_fraud_card_count=0
):
    """
    Determines initial actions before any evidence requests come back.
    """
    prob = float(fraud_probability)
    exposure = float(case_exposure)
    r_exposure = float(ring_exposure)
    conn_cards = list(connected_cards or [])
    
    actions = []
    rules_applied = []
    sar_required = False
    sar_reason = ""
    sar_exposure_basis = ""
    evidence_request_required = False
    evidence_request_type = ""
    stop_investigation = False

    # Check detector results if passed
    if detector_results:
        if any(d.get("detector") == "recurring_merchant_scan" and d.get("triggered") for d in detector_results):
            recurring_charge = True

    # Rule R7: Recurring subscription dispute
    if recurring_charge or (trigger_type == "customer_report" and recurring_charge):
        actions.append(_build_action("CREATE_CASE"))
        actions.append(_build_action("VERIFY_WITH_CUSTOMER"))
        actions.append(_build_action("WARN_CUSTOMER"))
        evidence_request_required = True
        evidence_request_type = "customer_validation"
        rules_applied.append("R7")
        stop_investigation = False

    # Rule R6: Shared origin / device ring (>= 3 connected cards)
    elif len(conn_cards) >= 3:
        actions.append(_build_action("CREATE_CASE"))
        actions.append(_build_action("FILE_REPORT"))
        actions.append(_build_action("MONITOR_CONNECTED_CARDS"))
        sar_required = True
        sar_reason = f"R6: Shared device profile used on {len(conn_cards)} cards across accounts"
        sar_exposure_basis = "ring_exposure"
        rules_applied.append("R6")
        if exposure > 500 or prob > 0.40:
            evidence_request_required = True
            evidence_request_type = "customer_validation"

    # Rule R9: Undocumented pattern
    elif pattern == "undocumented":
        actions.append(_build_action("CREATE_CASE"))
        actions.append(_build_action("FILE_REPORT"))
        actions.append(_build_action("ESCALATE_TO_ANALYST"))
        sar_required = True
        sar_reason = "R9: Undocumented coordinated fraud pattern"
        sar_exposure_basis = "case_exposure"
        rules_applied.append("R9")

    # Rule R5: Card testing pattern
    elif pattern == "card_testing":
        actions.append(_build_action("DECLINE_TRANSACTION"))
        actions.append(_build_action("STEP_UP_AUTH"))
        if exposure > 100.0:
            actions.append(_build_action("BLOCK_CARD", exposure))
        rules_applied.append("R5")
        evidence_request_required = True
        evidence_request_type = "step_up_auth"

    # Rule R1: Single signal / moderate probability (0.40 - 0.75)
    elif 0.40 <= prob <= 0.75:
        actions.append(_build_action("VERIFY_WITH_CUSTOMER"))
        if exposure > 500.0:
            actions.append(_build_action("ESCALATE_TO_ANALYST"))
        evidence_request_required = True
        evidence_request_type = "customer_validation"
        rules_applied.append("R1")

    # Rule R8: Uncertain and exposed (> 500)
    elif verdict == "uncertain" and exposure > 500.0:
        actions.append(_build_action("ESCALATE_TO_ANALYST"))
        evidence_request_required = True
        evidence_request_type = "customer_validation"
        rules_applied.append("R8")

    # Clear legitimate activity (low probability)
    elif verdict == "legitimate" or prob <= 0.15:
        actions.append(_build_action("CLOSE_NO_FRAUD"))
        actions.append(_build_action("ALLOW_TRANSACTION"))
        stop_investigation = True

    # High probability fraud (> 0.75) without customer contact yet
    elif prob > 0.75:
        actions.append(_build_action("DECLINE_TRANSACTION"))
        actions.append(_build_action("CREATE_CASE"))
        actions.append(_build_action("VERIFY_WITH_CUSTOMER"))
        if exposure > 1000.0:
            actions.append(_build_action("FILE_REPORT"))
            sar_required = True
            sar_reason = f"High confidence fraud (prob={prob:.2f}) with exposure ${exposure:.2f} > $1,000"
            sar_exposure_basis = "case_exposure"
        evidence_request_required = True
        evidence_request_type = "customer_validation"

    # Default fallback
    else:
        actions.append(_build_action("MONITOR_CARD"))
        actions.append(_build_action("VERIFY_WITH_CUSTOMER"))
        evidence_request_required = True
        evidence_request_type = "customer_validation"

    # Rule R10: Block all cards only if >= 2 confirmed fraud cards on same customer
    if confirmed_fraud_card_count >= 2:
        actions.append(_build_action("BLOCK_ALL_CARDS"))
        rules_applied.append("R10")

    # Enforce R2 policy rule: customer denial is required BEFORE blocking
    if evidence_request_required:
        if prob > 0.75 or evidence_request_type == "customer_validation":
            if not any(a["action"] == "VERIFY_WITH_CUSTOMER" for a in actions):
                actions.append(_build_action("VERIFY_WITH_CUSTOMER"))
        # BLOCK_CARD must NOT be in initial actions when evidence is pending
        actions = [a for a in actions if a["action"] != "BLOCK_CARD"]

    decision = {
        "actions": _order_and_dedupe_actions(actions),
        "sar_required": sar_required,
        "sar_reason": sar_reason,
        "sar_exposure_basis": sar_exposure_basis,
        "evidence_request_required": evidence_request_required,
        "evidence_request_type": evidence_request_type,
        "stop_investigation": stop_investigation,
        "rules_applied": rules_applied
    }

    _enforce_hard_constraints(decision, recurring_charge=recurring_charge)
    return decision


def decide_after_evidence(
    verdict,
    fraud_probability,
    case_exposure,
    ring_exposure,
    connected_cards,
    pattern,
    trigger_type,
    recurring_charge=False,
    customer_response="no_reply_24h",
    detector_results=None,
    confirmed_fraud_card_count=0
):
    """
    Determines final actions after customer or auth response is received.
    """
    prob = float(fraud_probability)
    exposure = float(case_exposure)
    r_exposure = float(ring_exposure)
    conn_cards = list(connected_cards or [])
    resp = str(customer_response).lower().strip()

    actions = []
    rules_applied = []
    sar_required = False
    sar_reason = ""
    sar_exposure_basis = ""
    stop_investigation = True

    # Rule R3: Customer confirmed transaction
    if resp == "confirmed":
        actions.append(_build_action("CLOSE_NO_FRAUD"))
        actions.append(_build_action("ALLOW_TRANSACTION"))
        rules_applied.append("R3")
        stop_investigation = True

    # Rule R2: Customer denied transaction
    elif resp == "denied":
        # R7 exception: if recurring charge disputed, do not block without analyst
        if recurring_charge:
            actions.append(_build_action("CREATE_CASE"))
            actions.append(_build_action("WARN_CUSTOMER"))
            actions.append(_build_action("ESCALATE_TO_ANALYST"))
            rules_applied.append("R7")
        else:
            actions.append(_build_action("BLOCK_CARD", exposure))
            actions.append(_build_action("CREATE_CASE"))
            rules_applied.append("R2")

            # Check SAR thresholds under R2
            if exposure > 1000.0:
                actions.append(_build_action("FILE_REPORT"))
                sar_required = True
                sar_reason = f"R2: Customer denied unauthorized activity; exposure ${exposure:.2f} > $1,000"
                sar_exposure_basis = "case_exposure"
            elif (r_exposure > 1000.0 or exposure > 1000.0) and len(conn_cards) >= 2:
                actions.append(_build_action("FILE_REPORT"))
                sar_required = True
                sar_reason = f"R2: Customer denied transaction connected to multi-card compromise ring"
                sar_exposure_basis = "ring_exposure"

            # If connected cards exist, place them under monitoring
            if len(conn_cards) > 0:
                actions.append(_build_action("MONITOR_CONNECTED_CARDS"))

    # Rule R4: No reply within 24 hours
    elif resp in ["no_reply_24h", "no_response"]:
        actions.append(_build_action("MONITOR_CARD"))
        actions.append(_build_action("DECLINE_TRANSACTION"))
        if exposure > 500.0:
            actions.append(_build_action("ESCALATE_TO_ANALYST"))
        rules_applied.append("R4")

    else:
        # Fallback for other response types
        actions.append(_build_action("MONITOR_CARD"))
        if exposure > 500.0:
            actions.append(_build_action("ESCALATE_TO_ANALYST"))

    # Additional contextual overrides
    # Rule R6: Multi-card ring (>= 3 cards) maintains FILE_REPORT and MONITOR_CONNECTED_CARDS
    if len(conn_cards) >= 3 and "CLOSE_NO_FRAUD" not in [a["action"] for a in actions]:
        actions.append(_build_action("CREATE_CASE"))
        actions.append(_build_action("FILE_REPORT"))
        actions.append(_build_action("MONITOR_CONNECTED_CARDS"))
        sar_required = True
        sar_reason = f"R6: Confirmed ring across {len(conn_cards)} cards"
        sar_exposure_basis = "ring_exposure"
        if "R6" not in rules_applied:
            rules_applied.append("R6")

    # Rule R9: Undocumented pattern
    if pattern == "undocumented" and "CLOSE_NO_FRAUD" not in [a["action"] for a in actions]:
        actions.append(_build_action("CREATE_CASE"))
        actions.append(_build_action("FILE_REPORT"))
        actions.append(_build_action("ESCALATE_TO_ANALYST"))
        sar_required = True
        sar_reason = "R9: Undocumented fraud pattern"
        sar_exposure_basis = "case_exposure"
        if "R9" not in rules_applied:
            rules_applied.append("R9")

    # Rule R10: Block all cards
    if confirmed_fraud_card_count >= 2 and "CLOSE_NO_FRAUD" not in [a["action"] for a in actions]:
        actions.append(_build_action("BLOCK_ALL_CARDS"))
        if "R10" not in rules_applied:
            rules_applied.append("R10")

    decision = {
        "actions": _order_and_dedupe_actions(actions),
        "sar_required": sar_required,
        "sar_reason": sar_reason,
        "sar_exposure_basis": sar_exposure_basis,
        "evidence_request_required": False,
        "evidence_request_type": "",
        "stop_investigation": stop_investigation,
        "rules_applied": rules_applied
    }

    _enforce_hard_constraints(decision, recurring_charge=(recurring_charge and resp != "denied"))
    return decision
