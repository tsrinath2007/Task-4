"""
src/memory/case_memory.py — Semantic Case Retrieval

Loads pre-computed embeddings and performs cosine similarity search over all 5,565 closed cases.
Preserves and surfaces both confirmed fraud and cleared cases.
"""

import os
import json
import pandas as pd
import numpy as np
from src.memory.embeddings import embed_query

PROCESSED_DIR = os.path.join("data", "processed")
EMBEDDINGS_PATH = os.path.join(PROCESSED_DIR, "case_embeddings.npy")
IDS_PATH = os.path.join(PROCESSED_DIR, "case_ids.json")
CASES_PATH = os.path.join(PROCESSED_DIR, "v_closed_case.csv")

_EMBEDDINGS = None
_CASE_IDS = None
_CASES_DF = None


def _load_cache():
    global _EMBEDDINGS, _CASE_IDS, _CASES_DF
    if _EMBEDDINGS is None:
        if not os.path.exists(EMBEDDINGS_PATH) or not os.path.exists(IDS_PATH):
            raise FileNotFoundError("Embeddings index missing. Run scripts/build_embeddings.py first.")
        _EMBEDDINGS = np.load(EMBEDDINGS_PATH)
        with open(IDS_PATH, "r", encoding="utf-8") as f:
            _CASE_IDS = json.load(f)
        _CASES_DF = pd.read_csv(CASES_PATH).set_index("case_id")


def semantic_search(query_text, top_k=5):
    """
    Performs cosine similarity search against all 5,565 closed cases.
    Ensures cleared cases are not starved when the query indicates legitimate / recurring activity.
    """
    _load_cache()
    if not query_text or str(query_text).strip() == "":
        return []

    q_vec = embed_query(query_text)
    # Cosine similarities (vectors are L2-normalized)
    sims = np.dot(_EMBEDDINGS, q_vec)

    top_indices = np.argsort(sims)[::-1]

    results = []
    seen = set()

    # Detect if query has legitimacy signals (recurring, subscription, cleared, travel)
    q_lower = query_text.lower()
    is_legit_query = any(k in q_lower for k in ["recurring", "subscription", "cleared", "monthly", "legitimate", "travel"])

    # Collect top matches
    for idx in top_indices:
        case_id = _CASE_IDS[idx]
        if case_id in seen:
            continue
        sim = float(sims[idx])
        row = _CASES_DF.loc[case_id] if case_id in _CASES_DF.index else None
        
        outcome = row["outcome"] if row is not None and pd.notna(row.get("outcome")) else "unknown"
        pattern = row["pattern"] if row is not None and pd.notna(row.get("pattern")) else "none"
        notes = row["analyst_notes"] if row is not None and pd.notna(row.get("analyst_notes")) else ""

        results.append({
            "case_id": case_id,
            "outcome": outcome,
            "pattern": pattern,
            "analyst_notes": str(notes),
            "similarity": round(sim, 4),
            "retrieval_reason": "semantic",
            "entity_ids": [case_id]
        })
        seen.add(case_id)
        if len(results) >= top_k * 2:
            break

    # If it's a legitimacy query and top_k has no cleared cases, surface top cleared cases
    if is_legit_query:
        cleared_results = [r for r in results if r["outcome"] == "cleared"]
        if not cleared_results:
            # Look further in sorted indices for top cleared cases
            for idx in top_indices:
                case_id = _CASE_IDS[idx]
                if case_id in seen:
                    continue
                row = _CASES_DF.loc[case_id] if case_id in _CASES_DF.index else None
                if row is not None and row.get("outcome") == "cleared":
                    cleared_results.append({
                        "case_id": case_id,
                        "outcome": "cleared",
                        "pattern": row.get("pattern", "none"),
                        "analyst_notes": str(row.get("analyst_notes", "")),
                        "similarity": round(float(sims[idx]), 4),
                        "retrieval_reason": "semantic",
                        "entity_ids": [case_id]
                    })
                    if len(cleared_results) >= 2:
                        break
        # Interleave to ensure at least 1-2 cleared cases in top_k for legitimate queries
        final_list = []
        c_idx = 0
        f_idx = 0
        fraud_results = [r for r in results if r["outcome"] != "cleared"]
        while len(final_list) < top_k and (c_idx < len(cleared_results) or f_idx < len(fraud_results)):
            if c_idx < len(cleared_results):
                final_list.append(cleared_results[c_idx])
                c_idx += 1
            if len(final_list) < top_k and f_idx < len(fraud_results):
                final_list.append(fraud_results[f_idx])
                f_idx += 1
        return final_list[:top_k]

    return results[:top_k]
