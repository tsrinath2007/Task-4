"""
src/agent/schemas.py — Pydantic Schemas for Structured Agent Outputs

Defines strict models for LLM structured outputs and internal validations.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    claim: str = Field(description="A factual statement of evidence uncovered")
    source: Literal["graph", "document", "customer", "external"] = Field(
        description="Source category of the evidence"
    )
    ref: str = Field(description="Query name, document section, or request id")
    entity_ids: List[str] = Field(
        default_factory=list,
        description="List of IDs (transactions, cards, devices, cases) supporting the claim"
    )


class AdjudicatorOutput(BaseModel):
    verdict: Literal["fraud", "legitimate", "uncertain"] = Field(
        description="Overall investigation conclusion"
    )
    fraud_probability: float = Field(
        ge=0.0,
        le=1.0,
        description="Calibrated probability that flagged activity is fraud"
    )
    pattern: Literal[
        "card_testing",
        "card_not_present_fraud",
        "card_not_present_new_device",
        "out_of_region_use",
        "account_takeover",
        "undocumented",
        "none"
    ] = Field(description="Fraud pattern typology or none")
    pattern_description: str = Field(
        default="",
        description="Required if pattern is 'undocumented', otherwise empty string"
    )
    affected_txn_ids: List[str] = Field(
        default_factory=list,
        description="All transaction IDs in the fraud episode (empty if legitimate)"
    )
    first_suspicious_txn_id: str = Field(
        default="",
        description="Transaction ID where the suspicious activity commenced"
    )
    connected_card_ids: List[str] = Field(
        default_factory=list,
        description="Other card IDs linked via ring, device, or customer compromise"
    )
    connected_device_profiles: List[str] = Field(
        default_factory=list,
        description="Device profiles linking this case to other activity"
    )
    exposure_usd: float = Field(
        default=0.0,
        ge=0.0,
        description="Total exposure in USD of all affected transactions"
    )
    summary: str = Field(
        description="Two to six concise sentences summarizing the investigation findings"
    )
    evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="Structured factual evidence items"
    )


class ActionItem(BaseModel):
    action: str = Field(description="Policy action name")
    route: Literal["auto", "L1", "L2"] = Field(description="Required approval route")
    reason: str = Field(description="Justification citing policy rule")


class ActionExplainerOutput(BaseModel):
    initial: List[ActionItem] = Field(description="Initial actions before evidence returned")
    final: List[ActionItem] = Field(description="Final actions after evidence returned")
    what_changed: str = Field(description="One or two sentences explaining the change or 'nothing'")


class SarOutput(BaseModel):
    file: bool = Field(description="Whether a Suspicious Activity Report should be filed")
    reason: str = Field(description="Regulatory justification citing policy rule")
    narrative: str = Field(
        default="",
        description="Complete FinCEN narrative covering who, what, when, where, how, why (empty if file=false)"
    )
    subjects: List[str] = Field(
        default_factory=list,
        description="Customer, card, and device IDs named in narrative"
    )
    total_amount_usd: float = Field(
        default=0.0,
        description="Total amount of suspicious activity"
    )
    activity_dates: List[str] = Field(
        default_factory=list,
        description="[start_date, end_date] in YYYY-MM-DD format"
    )


class CaseMemoryOutput(BaseModel):
    analyst_notes: str = Field(description="Free-text investigation notes for future retrieval")
    summary: str = Field(description="Concise case summary")
