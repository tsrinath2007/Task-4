"""
src/agent/states.py — Investigation Lifecycle States

Defines the states through which the autonomous fraud investigation agent progresses.
"""

from enum import Enum


class InvestigationState(str, Enum):
    TRIGGER = "TRIGGER"
    INVESTIGATE = "INVESTIGATE"
    GATHER_EVIDENCE = "GATHER_EVIDENCE"
    ASSESS_UNCERTAINTY = "ASSESS_UNCERTAINTY"
    GATHER_MORE_EVIDENCE = "GATHER_MORE_EVIDENCE"
    REASSESS = "REASSESS"
    RECOMMEND_ACTION = "RECOMMEND_ACTION"
    EXPLAIN = "EXPLAIN"
    UPDATE_CASE_MEMORY = "UPDATE_CASE_MEMORY"
