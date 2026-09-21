"""
src/memory/retriever.py — Unified GraphRAG Case Memory Retriever

Combines:
1. Semantic search over 5,565 closed cases (SentenceTransformers embeddings)
2. Graph adjacency traversals (device, region, customer linkages)

Applies a +0.15 priority boost to graph-connected cases and surfaces both
confirmed fraud and cleared cases as legitimate baselines.
"""

from src.memory.case_memory import semantic_search
from src.memory.graph_memory import (
    get_cases_by_device,
    get_cases_by_region,
    get_cases_by_customer
)


def retrieve(device_id=None, addr1=None, customer_id=None, evidence_summary="", top_k=5, conn=None):
    """
    Executes GraphRAG retrieval merging semantic similarity and graph adjacency.
    Returns top_k deduplicated, ranked closed cases.
    """
    # 1. Semantic retrieval
    semantic_results = semantic_search(evidence_summary, top_k=top_k * 2) if evidence_summary else []

    # 2. Graph adjacency retrieval
    graph_results = []
    if device_id:
        graph_results.extend(get_cases_by_device(device_id, conn))
    if addr1:
        graph_results.extend(get_cases_by_region(addr1, conn))
    if customer_id:
        graph_results.extend(get_cases_by_customer(customer_id, conn))

    # 3. Merge and deduplicate
    combined = {}

    # Add semantic results
    for r in semantic_results:
        cid = r["case_id"]
        combined[cid] = {
            "case_id": cid,
            "outcome": r["outcome"],
            "pattern": r["pattern"],
            "analyst_notes": r["analyst_notes"],
            "similarity": float(r["similarity"]),
            "retrieval_reason": "semantic",
            "entity_ids": list(r["entity_ids"])
        }

    # Add or boost with graph results
    for r in graph_results:
        cid = r["case_id"]
        reason = r.get("retrieval_reason", "graph_match")
        entities = r.get("entity_ids", [])
        
        if cid in combined:
            # Boost existing semantic match with graph connection
            combined[cid]["similarity"] = round(combined[cid]["similarity"] + 0.15, 4)
            combined[cid]["retrieval_reason"] = f"{reason} + semantic"
            combined[cid]["entity_ids"] = list(set(combined[cid]["entity_ids"] + entities))
        else:
            # Graph-only match receives baseline + boost
            combined[cid] = {
                "case_id": cid,
                "outcome": r["outcome"],
                "pattern": r["pattern"],
                "analyst_notes": r["analyst_notes"],
                "similarity": 0.65,  # baseline graph relevance
                "retrieval_reason": reason,
                "entity_ids": entities
            }

    # Rank by similarity descending
    ranked = sorted(combined.values(), key=lambda x: x["similarity"], reverse=True)

    # Ensure cleared cases are present if any were retrieved and query reflects legitimate/cleared context
    q_lower = (evidence_summary or "").lower()
    is_legit_query = any(k in q_lower for k in ["recurring", "subscription", "cleared", "monthly", "legitimate", "travel"])

    if is_legit_query:
        cleared_cases = [c for c in ranked if c["outcome"] == "cleared"]
        fraud_cases = [c for c in ranked if c["outcome"] != "cleared"]
        
        # Interleave to guarantee cleared representation
        interleaved = []
        c_i, f_i = 0, 0
        while len(interleaved) < top_k and (c_i < len(cleared_cases) or f_i < len(fraud_cases)):
            if c_i < len(cleared_cases):
                interleaved.append(cleared_cases[c_i])
                c_i += 1
            if len(interleaved) < top_k and f_i < len(fraud_cases):
                interleaved.append(fraud_cases[f_i])
                f_i += 1
        return interleaved[:top_k]

    return ranked[:top_k]
