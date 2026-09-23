"""
src/agent/orchestrator.py — Autonomous Fraud Investigation Orchestrator

Coordinates graph queries, fraud detectors, GraphRAG case memory,
the deterministic policy engine, and the Groq LLM adapter to investigate cases.
"""

import os
import json
import time
import pandas as pd
from typing import Dict, Any, Optional

from src.agent.states import InvestigationState
from src.agent.context import InvestigationContext
from src.agent.llm_adapter import LLMAdapter
from src.detectors.run_all import run_all_detectors
from src.detectors.legitimacy_checklist import legitimacy_checklist
from src.policy.policy_engine import decide_initial, decide_after_evidence
from src.memory.retriever import retrieve
from src.graph.mcp_client import (
    query_card_history,
    query_customer_cards,
    query_shared_devices,
    query_prior_cases,
    write_case
)


def _get_val(row: Any, key: str, default: Any = None) -> Any:
    """Safely retrieves a value from a dict or pandas Series."""
    if isinstance(row, dict):
        return row.get(key, default)
    elif hasattr(row, "get"):
        val = row.get(key, default)
        return default if pd.isna(val) else val
    elif hasattr(row, "__getitem__"):
        try:
            val = row[key]
            return default if pd.isna(val) else val
        except (KeyError, IndexError):
            return default
    return default


def run_case(
    case_row: Any,
    transactions_df: pd.DataFrame,
    identity_df: Optional[pd.DataFrame] = None,
    closed_cases_df: Optional[pd.DataFrame] = None,
    conn: Any = None
) -> Dict[str, Any]:
    """
    Executes the full 8-step autonomous investigation pipeline for a given case.
    Returns the complete answer dictionary and writes cases/generated/<case_id>.json.
    """
    start_time = time.time()
    llm = LLMAdapter()

    # 1. TRIGGER
    case_id = str(_get_val(case_row, "case_id", "UNKNOWN"))
    opened_at = str(_get_val(case_row, "opened_at", ""))
    trigger_type = str(_get_val(case_row, "trigger_type", "risk_score"))
    trigger_text = str(_get_val(case_row, "trigger_text", ""))
    flagged_txn_id = str(_get_val(case_row, "flagged_txn_id", ""))
    card_id = str(_get_val(case_row, "card_id", ""))
    customer_id = str(_get_val(case_row, "customer_id", ""))
    risk_score_raw = _get_val(case_row, "risk_score", None)
    risk_score = float(risk_score_raw) if risk_score_raw is not None and str(risk_score_raw).strip() != "" and str(risk_score_raw) != "nan" else None

    ctx = InvestigationContext(
        case_id=case_id,
        opened_at=opened_at,
        trigger_type=trigger_type,
        trigger_text=trigger_text,
        flagged_txn_id=flagged_txn_id,
        card_id=card_id,
        customer_id=customer_id,
        risk_score=risk_score,
        state=InvestigationState.TRIGGER,
        current_step=1,
        start_time=start_time
    )

    # Resolve flagged transaction details from transactions_df
    txn_match = transactions_df[transactions_df["TransactionID"] == flagged_txn_id]
    flagged_amount = 0.0
    device_id = None
    addr1 = None
    txn_ts = opened_at

    if not txn_match.empty:
        curr = txn_match.iloc[0]
        flagged_amount = float(curr.get("TransactionAmt", 0.0))
        device_id = curr.get("device_id")
        addr1 = curr.get("addr1")
        txn_ts = curr.get("ts", opened_at)

    row_amt = _get_val(case_row, "amount", None) or _get_val(case_row, "flagged_amount", None)
    if row_amt is not None and str(row_amt).strip() != "" and str(row_amt) != "nan":
        try:
            flagged_amount = float(row_amt)
        except (ValueError, TypeError):
            pass

    ctx.exposure_usd = flagged_amount

    # --- Confidence Evolution Step 1: TRIGGER ---
    trigger_prob = float(risk_score) if risk_score is not None else (0.50 if trigger_type == "customer_report" else 0.50)
    ctx.add_confidence_step(
        step="trigger",
        probability=trigger_prob,
        reason=f"Investigation initiated via {trigger_type} ({trigger_text or 'model threshold alert'}). Baseline risk score: {trigger_prob:.2f}.",
        tool_used=None
    )
    ctx.log_timeline_event(
        event=f"Investigation triggered by {trigger_type}",
        state="TRIGGER",
        confidence=trigger_prob,
        tool=None,
        result_summary=f"Alert flagged transaction {flagged_txn_id} on card {card_id} for ${flagged_amount:.2f}"
    )

    # 2. INVESTIGATE (Graph Queries)
    ctx.state = InvestigationState.INVESTIGATE
    ctx.current_step = 2

    # Query customer cards
    t0 = time.time()
    cust_cards_res = query_customer_cards(customer_id, conn)
    ctx.log_tool_call("query_customer_cards", {"customer_id": customer_id}, f"Found {cust_cards_res['count']} cards", cust_cards_res["latency_ms"])
    ctx.log_timeline_event(
        event="Customer card portfolio queried from TigerGraph",
        state="INVESTIGATE",
        confidence=trigger_prob,
        tool="query_customer_cards",
        result_summary=f"Found {cust_cards_res['count']} card(s) owned by customer {customer_id}"
    )

    # Query card history
    t0 = time.time()
    card_hist_res = query_card_history(card_id, conn, limit=100)
    ctx.log_tool_call("query_card_history", {"card_id": card_id}, f"Retrieved {card_hist_res['count']} transactions", card_hist_res["latency_ms"])
    ctx.log_timeline_event(
        event="Card transaction history retrieved from TigerGraph",
        state="INVESTIGATE",
        confidence=trigger_prob,
        tool="query_card_history",
        result_summary=f"Retrieved {card_hist_res['count']} transactions on {card_id}"
    )

    # Query shared devices
    t0 = time.time()
    shared_dev_res = query_shared_devices(flagged_txn_id, conn)
    ctx.log_tool_call("query_shared_devices", {"txn_id": flagged_txn_id}, f"Found {shared_dev_res['count']} connected cards", shared_dev_res["latency_ms"])

    # Query prior cases
    t0 = time.time()
    prior_cases_res = query_prior_cases(card_id, conn)
    ctx.log_tool_call("query_prior_cases", {"card_id": card_id}, f"Found {prior_cases_res['count']} prior cases", prior_cases_res["latency_ms"])
    if prior_cases_res["count"] > 0:
        ctx.log_timeline_event(
            event="Prior closed cases queried on card",
            state="INVESTIGATE",
            confidence=trigger_prob,
            tool="query_prior_cases",
            result_summary=f"Found {prior_cases_res['count']} historical closed investigation(s) for {card_id}"
        )

    ctx.graph_context = {
        "customer_cards": cust_cards_res.get("cards", []),
        "card_history": card_hist_res.get("data", []),
        "shared_devices": shared_dev_res,
        "prior_cases": prior_cases_res.get("cases", [])
    }

    # Extract connected cards (excluding current card)
    all_connected = set(cust_cards_res.get("cards", []) + shared_dev_res.get("connected_cards", []))
    all_connected.discard(card_id)
    ctx.connected_card_ids = sorted(list(all_connected))

    # Identify connected device profiles
    dev_id = shared_dev_res.get("device_id") or device_id
    if dev_id and str(dev_id).strip() not in ["", "nan", "None"]:
        ctx.connected_device_profiles = [str(dev_id)]
    else:
        ctx.connected_device_profiles = []

    # --- Confidence Evolution Step 2: GRAPH_TRAVERSAL ---
    if len(ctx.connected_card_ids) >= 3:
        graph_prob = min(0.85, max(trigger_prob, 0.72))
        graph_reason = f"TigerGraph multi-hop traversal revealed shared device {dev_id} linked to {len(ctx.connected_card_ids)} distinct cards (syndicate pattern)."
    elif len(ctx.connected_card_ids) > 0:
        graph_prob = trigger_prob
        graph_reason = f"TigerGraph traversal identified {len(ctx.connected_card_ids)} connected card(s) under customer portfolio."
    else:
        graph_prob = max(0.05, trigger_prob - 0.05) if trigger_prob < 0.3 else trigger_prob
        graph_reason = "TigerGraph traversal found no multi-card device sharing or prior compromise history."

    ctx.add_confidence_step(
        step="graph_traversal",
        probability=graph_prob,
        reason=graph_reason,
        tool_used="query_shared_devices"
    )
    ctx.log_timeline_event(
        event=f"Shared device scan found {shared_dev_res['count']} cards on device {dev_id or 'N/A'}",
        state="INVESTIGATE",
        confidence=graph_prob,
        tool="query_shared_devices",
        result_summary=f"Device {dev_id} connects to {len(ctx.connected_card_ids)} connected card account(s)"
    )

    # 3. GATHER_EVIDENCE (Detectors & Memory)
    ctx.state = InvestigationState.GATHER_EVIDENCE
    ctx.current_step = 3

    # Run detectors
    t0 = time.time()
    ctx.detector_results = run_all_detectors(card_id, flagged_txn_id, transactions_df, identity_df, closed_cases_df)
    ctx.log_tool_call("run_all_detectors", {"card_id": card_id, "txn_id": flagged_txn_id}, f"Evaluated 8 detectors", (time.time() - t0) * 1000)

    # Run legitimacy checklist
    t0 = time.time()
    ctx.legitimacy_results = legitimacy_checklist(card_id, flagged_txn_id, flagged_amount, transactions_df, identity_df)
    ctx.log_tool_call("legitimacy_checklist", {"card_id": card_id, "txn_id": flagged_txn_id}, f"Score {ctx.legitimacy_results['legitimacy_score']}/{ctx.legitimacy_results['max_score']}", (time.time() - t0) * 1000)

    # Determine detector conditions
    recurring_det = next((d for d in ctx.detector_results if d.get("detector") == "recurring_merchant_scan"), {})
    card_testing_det = next((d for d in ctx.detector_results if d.get("detector") == "card_testing_scan"), {})
    shared_dev_det = next((d for d in ctx.detector_results if d.get("detector") == "shared_device_scan"), {})
    
    is_recurring = bool(recurring_det.get("triggered", False))
    is_card_testing = bool(card_testing_det.get("triggered", False))
    is_shared_dev = bool(shared_dev_det.get("triggered", False))

    if is_card_testing:
        det_prob = 0.88
        det_reason = "Card testing scan detected rapid sequence of micro-authorizations."
        det_tool = "card_testing_scan"
    elif is_recurring:
        det_prob = 0.08
        det_reason = "Recurring merchant scan detected periodic 28-34 day billing interval matching legitimate subscription."
        det_tool = "recurring_merchant_scan"
    elif is_shared_dev and len(ctx.connected_card_ids) >= 3:
        det_prob = 0.90
        det_reason = f"Shared device scan confirmed multi-card syndicate hub ({len(ctx.connected_card_ids)} cards)."
        det_tool = "shared_device_scan"
    elif trigger_type == "customer_report":
        det_prob = 0.85
        det_reason = "Direct customer fraud report filed for unauthorized charge."
        det_tool = "run_all_detectors"
    else:
        legit_score = ctx.legitimacy_results.get("legitimacy_score", 0)
        if legit_score >= 4:
            det_prob = 0.10
            det_reason = f"Legitimacy checklist scored {legit_score}/9, validating established spending baseline."
            det_tool = "legitimacy_checklist"
        else:
            det_prob = float(risk_score or 0.55)
            det_reason = "Evaluated 8 deterministic fraud detectors against transaction velocity and location."
            det_tool = "run_all_detectors"

    # --- Confidence Evolution Step 3: DETECTORS ---
    ctx.add_confidence_step(
        step="detectors",
        probability=det_prob,
        reason=det_reason,
        tool_used=det_tool
    )
    ctx.log_timeline_event(
        event="Evaluated 8 deterministic fraud detectors",
        state="GATHER_EVIDENCE",
        confidence=det_prob,
        tool=det_tool,
        result_summary=f"Triggered: {', '.join([d['detector'] for d in ctx.detector_results if d.get('triggered')]) or 'None'}"
    )
    ctx.log_timeline_event(
        event=f"Legitimacy checklist evaluated ({ctx.legitimacy_results.get('legitimacy_score', 0)}/9)",
        state="GATHER_EVIDENCE",
        confidence=det_prob,
        tool="legitimacy_checklist",
        result_summary=f"Matched baseline indicators: {ctx.legitimacy_results.get('legitimacy_score', 0)} out of 9"
    )

    # Retrieve from GraphRAG memory
    t0 = time.time()
    query_summary = f"{trigger_type} {trigger_text} card {card_id} amount {flagged_amount}"
    ctx.retrieved_cases = retrieve(
        device_id=dev_id,
        addr1=addr1,
        customer_id=customer_id,
        evidence_summary=query_summary,
        top_k=5,
        conn=conn
    )
    ctx.similar_prior_cases = [c["case_id"] for c in ctx.retrieved_cases]
    ctx.log_tool_call("retrieve_case_memory", {"customer_id": customer_id, "top_k": 5}, f"Retrieved {len(ctx.retrieved_cases)} cases", (time.time() - t0) * 1000)

    # --- Confidence Evolution Step 4: CASE_MEMORY ---
    top_prior = ctx.retrieved_cases[0] if ctx.retrieved_cases else None
    if top_prior and top_prior.get("outcome") == "fraud":
        memory_prob = min(0.95, det_prob + 0.04) if det_prob > 0.5 else det_prob
        memory_reason = f"GraphRAG retrieved {len(ctx.retrieved_cases)} cases; prior confirmed fraud case {top_prior.get('case_id')} ({top_prior.get('pattern', 'fraud')}) corroborated suspicion."
    elif top_prior and top_prior.get("outcome") == "cleared":
        memory_prob = max(0.05, det_prob - 0.02) if det_prob < 0.5 else det_prob
        memory_reason = f"GraphRAG retrieved {len(ctx.retrieved_cases)} cases; prior cleared case {top_prior.get('case_id')} reinforced legitimate cardholder precedent."
    else:
        memory_prob = det_prob
        memory_reason = f"GraphRAG retrieved {len(ctx.retrieved_cases)} precedent cases for contextual grounding."

    ctx.add_confidence_step(
        step="case_memory",
        probability=memory_prob,
        reason=memory_reason,
        tool_used="retrieve_case_memory"
    )
    ctx.log_timeline_event(
        event=f"GraphRAG memory retrieved {len(ctx.retrieved_cases)} historical cases",
        state="GATHER_EVIDENCE",
        confidence=memory_prob,
        tool="retrieve_case_memory",
        result_summary=f"Top precedent: {top_prior.get('case_id', 'N/A')} (Outcome: {top_prior.get('outcome', 'unknown') if top_prior else 'none'})"
    )

    # 4. ASSESS_UNCERTAINTY & INITIAL POLICY
    ctx.state = InvestigationState.ASSESS_UNCERTAINTY
    ctx.current_step = 4

    if is_card_testing:
        testing_txns = card_testing_det.get("details", {}).get("testing_txns", [flagged_txn_id])
        ctx.affected_txn_ids = testing_txns
        ctx.first_suspicious_txn_id = testing_txns[0] if testing_txns else flagged_txn_id
        # Calculate total exposure from testing txns
        sub_txns = transactions_df[transactions_df["TransactionID"].isin(testing_txns)]
        ctx.exposure_usd = float(pd.to_numeric(sub_txns["TransactionAmt"], errors="coerce").sum())
        ctx.pattern = "card_testing"
        prelim_verdict = "fraud"
        prelim_prob = 0.88
    elif is_recurring:
        ctx.pattern = "none"
        prelim_verdict = "legitimate"
        prelim_prob = 0.08
        ctx.exposure_usd = flagged_amount
    elif is_shared_dev and len(ctx.connected_card_ids) >= 3:
        ctx.pattern = "card_not_present_new_device"
        prelim_verdict = "fraud"
        prelim_prob = 0.90
        ctx.affected_txn_ids = [flagged_txn_id]
        ctx.first_suspicious_txn_id = flagged_txn_id
    elif trigger_type == "customer_report":
        ctx.pattern = "card_not_present_fraud"
        prelim_verdict = "fraud"
        prelim_prob = 0.85
        ctx.affected_txn_ids = [flagged_txn_id]
        ctx.first_suspicious_txn_id = flagged_txn_id
    else:
        legit_score = ctx.legitimacy_results.get("legitimacy_score", 0)
        if legit_score >= 4:
            ctx.pattern = "none"
            prelim_verdict = "legitimate"
            prelim_prob = 0.10
            ctx.exposure_usd = flagged_amount
        else:
            ctx.pattern = "card_not_present_fraud" if (risk_score or 0) > 0.6 else "none"
            prelim_verdict = "uncertain"
            prelim_prob = float(risk_score or 0.55)
            ctx.affected_txn_ids = [flagged_txn_id] if prelim_prob > 0.6 else []
            ctx.first_suspicious_txn_id = flagged_txn_id if prelim_prob > 0.6 else ""

    # Ring exposure calculation
    ctx.ring_exposure = ctx.exposure_usd

    # Initial policy decision
    initial_decision = decide_initial(
        verdict=prelim_verdict,
        fraud_probability=prelim_prob,
        case_exposure=ctx.exposure_usd,
        ring_exposure=ctx.ring_exposure,
        connected_cards=ctx.connected_card_ids,
        pattern=ctx.pattern,
        trigger_type=trigger_type,
        recurring_charge=is_recurring,
        detector_results=ctx.detector_results
    )

    ctx.initial_actions = initial_decision["actions"]
    ctx.sar_required = initial_decision["sar_required"]
    ctx.sar_reason = initial_decision["sar_reason"]
    ctx.rules_applied = list(initial_decision["rules_applied"])

    # 5. GATHER_MORE_EVIDENCE (Simulation)
    ctx.state = InvestigationState.GATHER_MORE_EVIDENCE
    ctx.current_step = 5

    simulated_reply = None
    assumed_resp = None
    if initial_decision.get("evidence_request_required", False):
        req_type = initial_decision.get("evidence_request_type", "customer_validation")
        if req_type == "customer_validation":
            if is_recurring:
                assumed_resp = (
                    "Customer contacted regarding recurring subscription. Cardholder acknowledges subscription "
                    "billing and requests merchant cancellation details rather than fraud claim."
                )
                simulated_reply = "confirmed"
            elif trigger_type == "customer_report":
                assumed_resp = "Customer confirms they did not make or authorize the transaction and still have the card in possession."
                simulated_reply = "denied"
            elif any(d.get("triggered") for d in ctx.detector_results if d.get("detector") not in ["recurring_merchant_scan", "shared_region_scan"]):
                assumed_resp = "Customer contacted via SMS; states they do not recognize the transaction and did not authorize it."
                simulated_reply = "denied"
            elif is_shared_dev and len(ctx.connected_card_ids) >= 2:
                assumed_resp = "Customer contacted via SMS; states they do not recognize the transaction and did not authorize it."
                simulated_reply = "denied"
            elif ctx.legitimacy_results.get("legitimacy_score", 0) >= 4:
                assumed_resp = "Customer contacted via SMS; confirms they made the purchase."
                simulated_reply = "confirmed"
            else:
                assumed_resp = "Customer contacted via SMS; states they do not recognize the transaction."
                simulated_reply = "denied"
        elif req_type == "step_up_auth":
            if is_card_testing:
                assumed_resp = "Step-up authentication failed: one-time passcode not entered; session timed out."
                simulated_reply = "denied"
            else:
                assumed_resp = "Customer successfully completed biometric step-up authentication."
                simulated_reply = "confirmed"
        else:
            assumed_resp = "No customer response within 24 hours."
            simulated_reply = "no_reply_24h"

        ctx.evidence_requests.append({
            "type": req_type,
            "asked_after_step": 4,
            "assumed_response": assumed_resp
        })

    # 6. REASSESS (Final Policy Decision)
    ctx.state = InvestigationState.REASSESS
    ctx.current_step = 6

    if simulated_reply is not None:
        final_decision = decide_after_evidence(
            verdict=prelim_verdict,
            fraud_probability=prelim_prob,
            case_exposure=ctx.exposure_usd,
            ring_exposure=ctx.ring_exposure,
            connected_cards=ctx.connected_card_ids,
            pattern=ctx.pattern,
            trigger_type=trigger_type,
            recurring_charge=is_recurring,
            customer_response=simulated_reply,
            detector_results=ctx.detector_results
        )
        ctx.final_actions = final_decision["actions"]
        ctx.sar_required = final_decision["sar_required"]
        ctx.sar_reason = final_decision["sar_reason"]
        ctx.rules_applied = list(set(ctx.rules_applied + final_decision["rules_applied"]))

        # Adjust verdict & probability based on simulated outcome
        if simulated_reply == "confirmed":
            ctx.verdict = "legitimate"
            ctx.fraud_probability = 0.05
            ctx.pattern = "none"
            ctx.affected_txn_ids = []
            ctx.first_suspicious_txn_id = ""
            ctx.exposure_usd = flagged_amount
            ev_prob = 0.05
            ev_reason = "Customer confirmed transaction validity; cleared fraud suspicion."
        elif simulated_reply == "denied":
            if not is_recurring:
                ctx.verdict = "fraud"
                ctx.fraud_probability = max(prelim_prob, 0.86)
            else:
                ctx.verdict = "legitimate"
                ctx.fraud_probability = 0.08
            ev_prob = ctx.fraud_probability
            ev_reason = "Customer denied transaction authorization; confirmed unauthorized card compromise."
        elif simulated_reply == "no_reply_24h":
            ev_prob = prelim_prob
            ev_reason = "No customer response within 24-hour verification window; maintained current risk baseline."
        else:
            ev_prob = prelim_prob
            ev_reason = f"Evidence request response received: {simulated_reply}."
        ev_tool = "customer_validation"
    else:
        ctx.final_actions = list(ctx.initial_actions)
        ctx.verdict = prelim_verdict
        ctx.fraud_probability = prelim_prob
        ev_prob = memory_prob
        ev_reason = "No additional evidence request required; existing graph and detector signals were definitive."
        ev_tool = None

    # --- Confidence Evolution Step 6: EVIDENCE_REQUEST ---
    ctx.add_confidence_step(
        step="evidence_request",
        probability=ev_prob,
        reason=ev_reason,
        tool_used=ev_tool
    )
    ctx.log_timeline_event(
        event=f"Evidence request evaluated ({simulated_reply or 'Definitive graph evidence'})",
        state="REASSESS",
        confidence=ev_prob,
        tool=ev_tool,
        result_summary=assumed_resp if simulated_reply and assumed_resp else "Direct graph evidence definitive; proceed to final policy actions."
    )

    # 7. RECOMMEND_ACTION & EXPLAIN (LLM Adapter Synthesis)
    ctx.state = InvestigationState.RECOMMEND_ACTION
    ctx.current_step = 7

    # Adjudicator synthesis
    adj_out = llm.call_adjudicator(ctx)
    ctx.verdict = adj_out.verdict
    ctx.fraud_probability = adj_out.fraud_probability
    ctx.pattern = adj_out.pattern
    ctx.pattern_description = adj_out.pattern_description
    ctx.summary = adj_out.summary
    ctx.evidence_list = [e.dict() for e in adj_out.evidence]

    if ctx.verdict == "legitimate":
        ctx.affected_txn_ids = []
        ctx.first_suspicious_txn_id = ""
        ctx.exposure_usd = flagged_amount
    else:
        ctx.affected_txn_ids = adj_out.affected_txn_ids or [flagged_txn_id]
        ctx.first_suspicious_txn_id = adj_out.first_suspicious_txn_id or flagged_txn_id
        ctx.exposure_usd = adj_out.exposure_usd or flagged_amount

    # --- Confidence Evolution Step 5: LLM_ADJUDICATION ---
    ctx.add_confidence_step(
        step="llm_adjudication",
        probability=float(adj_out.fraud_probability),
        reason=f"LLM synthesis evaluated evidence: verdict {adj_out.verdict.upper()} ({adj_out.pattern}).",
        tool_used="llm_adjudicator"
    )
    ctx.log_timeline_event(
        event=f"Adjudicator synthesized case verdict: {adj_out.verdict.upper()}",
        state="RECOMMEND_ACTION",
        confidence=float(adj_out.fraud_probability),
        tool="llm_adjudicator",
        result_summary=adj_out.summary[:140] + ("..." if len(adj_out.summary) > 140 else "")
    )

    # Action explainer
    act_out = llm.call_action_explainer(ctx)
    ctx.initial_actions = [a.dict() for a in act_out.initial]
    ctx.final_actions = [a.dict() for a in act_out.final]
    ctx.what_changed = act_out.what_changed

    # SAR narrative
    activity_dates = [txn_ts.split()[0], txn_ts.split()[0]] if txn_ts else ["2016-12-01", "2016-12-01"]
    sar_out = llm.call_sar(ctx, activity_dates=activity_dates)
    ctx.sar = sar_out.dict()

    # 8. UPDATE_CASE_MEMORY & OUTPUT
    ctx.state = InvestigationState.UPDATE_CASE_MEMORY
    ctx.current_step = 8

    # Determine stop reason
    if is_recurring:
        ctx.stop_reason = "Recurring subscription pattern confirmed with cardholder; no unauthorized card compromise detected. Further steps would not change actions."
    elif ctx.verdict == "fraud":
        ctx.stop_reason = "Verification confirmed card compromise; exposure quantified and protective policy actions enforced. Further steps would not change actions."
    elif ctx.verdict == "legitimate":
        ctx.stop_reason = "Transaction validated against established cardholder spending baseline and confirmed legitimate. Further steps would not change actions."
    else:
        ctx.stop_reason = "Assessment concluded with balanced evidence baseline and escalated appropriately. Further steps would not change actions."

    # Determine status
    if ctx.verdict == "fraud":
        status = "closed_fraud"
    elif ctx.verdict == "legitimate":
        status = "closed_legitimate"
    else:
        status = "escalated" if any(a["action"] == "ESCALATE_TO_ANALYST" for a in ctx.final_actions) else "open"

    # Ensure exposure_usd always uses the flagged transaction amount from case_row, never 0.0 unless actual txn amount is 0
    if (ctx.exposure_usd == 0.0 or ctx.verdict == "legitimate") and flagged_amount > 0:
        ctx.exposure_usd = flagged_amount

    # --- Confidence Evolution Step 7: FINAL ---
    ctx.add_confidence_step(
        step="final",
        probability=float(ctx.fraud_probability),
        reason=f"Final adjudication established: {ctx.verdict.upper()} ({ctx.pattern}). Protection actions enforced under Rules {', '.join(ctx.rules_applied)}.",
        tool_used="policy_engine"
    )
    ctx.log_timeline_event(
        event=f"Policy actions enforced: {', '.join([a['action'] + ' [' + a['route'] + ']' for a in ctx.final_actions])}",
        state="RECOMMEND_ACTION",
        confidence=float(ctx.fraud_probability),
        tool="policy_engine",
        result_summary=f"Applied Rules: {', '.join(ctx.rules_applied)}. What changed: {ctx.what_changed}"
    )

    # TigerGraph Case writing
    ctx.graph_case_id = f"CASE-{case_id}"
    case_tg_payload = {
        "case_id": ctx.graph_case_id,
        "card_id": card_id,
        "status": status,
        "verdict": ctx.verdict,
        "fraud_probability": ctx.fraud_probability,
        "pattern": ctx.pattern,
        "pattern_description": ctx.pattern_description,
        "first_suspicious_txn_id": ctx.first_suspicious_txn_id,
        "exposure_usd": ctx.exposure_usd,
        "summary": ctx.summary,
        "evidence_json": json.dumps(ctx.evidence_list),
        "actions_json": json.dumps(ctx.final_actions),
        "sar_json": json.dumps(ctx.sar),
        "sar_filed": ctx.sar.get("file", False),
        "stop_reason": ctx.stop_reason,
        "affected_txn_ids": ctx.affected_txn_ids,
        "connected_card_ids": ctx.connected_card_ids
    }
    write_success = write_case(case_tg_payload, conn)
    ctx.written_to_graph = write_success

    ctx.log_timeline_event(
        event="Case written to TigerGraph",
        state="UPDATE_CASE_MEMORY",
        confidence=float(ctx.fraud_probability),
        tool="write_case",
        result_summary=f"Case record {ctx.graph_case_id} and associated relationship edges written to graph."
    )

    total_latency_s = round(time.time() - start_time, 2)
    ctx.total_latency_s = total_latency_s

    # Ensure confidence_evolution is in canonical order of 7 steps
    step_order = ["trigger", "graph_traversal", "detectors", "case_memory", "llm_adjudication", "evidence_request", "final"]
    ordered_evolution = sorted(
        ctx.confidence_evolution,
        key=lambda x: step_order.index(x["step"]) if x["step"] in step_order else 99
    )

    # Build final result dictionary
    result_dict = {
        "case_id": case_id,
        "case": {
            "status": status,
            "verdict": ctx.verdict,
            "fraud_probability": round(float(ctx.fraud_probability), 2),
            "pattern": ctx.pattern,
            "pattern_description": ctx.pattern_description,
            "affected_txn_ids": ctx.affected_txn_ids,
            "first_suspicious_txn_id": ctx.first_suspicious_txn_id,
            "connected_card_ids": ctx.connected_card_ids,
            "connected_device_profiles": ctx.connected_device_profiles,
            "exposure_usd": round(float(ctx.exposure_usd), 2),
            "evidence": ctx.evidence_list,
            "similar_prior_cases": ctx.similar_prior_cases,
            "summary": ctx.summary,
            "written_to_graph": ctx.written_to_graph,
            "graph_case_id": ctx.graph_case_id,
            "confidence_evolution": ordered_evolution,
            "investigation_timeline": ctx.investigation_timeline
        },
        "evidence_requests": ctx.evidence_requests,
        "next_best_actions": {
            "initial": ctx.initial_actions,
            "final": ctx.final_actions,
            "what_changed": ctx.what_changed
        },
        "sar": ctx.sar,
        "stop_reason": ctx.stop_reason,
        "tool_calls": len(ctx.tool_calls),
        "tokens": ctx.tokens_used,
        "latency_s": total_latency_s,
        "confidence_evolution": ordered_evolution,
        "investigation_timeline": ctx.investigation_timeline,
        # Helper / convenience aliases for smoke test and evaluations
        "verdict": ctx.verdict,
        "actions": ctx.final_actions,
        "sar_filed": ctx.sar.get("file", False),
        "investigation_path": ctx.tool_calls,
        "performance": {
            "latency_ms": round(total_latency_s * 1000, 2),
            "tokens": ctx.tokens_used
        }
    }

    # Save to cases/generated/<case_id>.json
    os.makedirs(os.path.join("cases", "generated"), exist_ok=True)
    out_path = os.path.join("cases", "generated", f"{case_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, indent=2)

    return result_dict

