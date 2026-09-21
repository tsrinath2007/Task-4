"""
src/agent/context.py — Investigation Execution Context

Maintains mutable state, intermediate evidence, tool execution history, and metrics
across all stages of a single case investigation.
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.agent.states import InvestigationState


@dataclass
class InvestigationContext:
    # Case metadata
    case_id: str
    opened_at: str
    trigger_type: str
    trigger_text: str
    flagged_txn_id: str
    card_id: str
    customer_id: str
    risk_score: Optional[float] = None

    # Lifecycle state
    state: InvestigationState = InvestigationState.TRIGGER
    current_step: int = 1

    # Analysis data
    detector_results: List[Dict[str, Any]] = field(default_factory=list)
    legitimacy_results: Dict[str, Any] = field(default_factory=dict)
    graph_context: Dict[str, Any] = field(default_factory=dict)
    retrieved_cases: List[Dict[str, Any]] = field(default_factory=list)

    # Uncertainty & dynamic evidence
    uncertainty_score: float = 0.0
    uncertainty_reasons: List[str] = field(default_factory=list)
    evidence_requests: List[Dict[str, Any]] = field(default_factory=list)

    # Adjudication results
    verdict: str = "uncertain"
    fraud_probability: float = 0.5
    pattern: str = "none"
    pattern_description: str = ""
    affected_txn_ids: List[str] = field(default_factory=list)
    first_suspicious_txn_id: str = ""
    connected_card_ids: List[str] = field(default_factory=list)
    connected_device_profiles: List[str] = field(default_factory=list)
    exposure_usd: float = 0.0
    ring_exposure: float = 0.0

    # Policy recommendations
    initial_actions: List[Dict[str, str]] = field(default_factory=list)
    final_actions: List[Dict[str, str]] = field(default_factory=list)
    what_changed: str = "nothing"
    rules_applied: List[str] = field(default_factory=list)

    # Regulatory filing
    sar_required: bool = False
    sar_reason: str = ""
    sar: Dict[str, Any] = field(default_factory=dict)

    # Explanations & Evidence
    summary: str = ""
    evidence_list: List[Dict[str, Any]] = field(default_factory=list)
    similar_prior_cases: List[str] = field(default_factory=list)
    stop_reason: str = ""

    # Graph persistence
    written_to_graph: bool = False
    graph_case_id: str = ""

    # Operational metrics & audit trail
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0
    start_time: float = field(default_factory=time.time)
    total_latency_s: float = 0.0

    def log_tool_call(self, tool_name: str, input_args: Dict[str, Any], result_summary: str, latency_ms: float):
        """Records a tool execution in the investigation path."""
        self.tool_calls.append({
            "step": self.current_step,
            "tool": tool_name,
            "input": input_args,
            "result_summary": result_summary,
            "latency_ms": round(latency_ms, 2),
            "status": "success"
        })
