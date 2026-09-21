# TigerGraph MCP Setup & Tool Integration Guide

This document outlines the architecture, configuration, and execution patterns for the **TigerGraph Model Context Protocol (MCP)** integration used by the autonomous fraud investigation agent.

---

## 1. Overview

The agent interacts with TigerGraph through an MCP-compatible client interface implemented in [`src/graph/mcp_client.py`](file:///c:/Users/SES/OneDrive/Documents/GOA_T/Task-4%20TigerGraph/src/graph/mcp_client.py). The client provides deterministic graph query tools and persistence capabilities with automatic local indexed fallback:

1. **`query_card_history(card_id, limit=100)`**: Fetches recent card transactions ordered by timestamp with amounts, product codes, billing regions, and device IDs.
2. **`query_customer_cards(customer_id)`**: Traverses `Customer` $\to$ `OWNS` $\to$ `Card` edges to find all payment instruments belonging to a cardholder.
3. **`query_shared_devices(txn_id)`**: Identifies the device profile used for a transaction and traverses `DeviceProfile` $\to$ `USED_ON` $\to$ `Card` to detect shared device compromise rings.
4. **`query_prior_cases(card_id)`**: Retrieves historical `ClosedCase` vertices connected to the card to inform investigation context.
5. **`write_case(case_json)`**: Persists newly closed or escalated investigations into the graph as `Case` vertices with `CASE_ON_CARD`, `CASE_INVOLVES`, and `CASE_CONNECTED_TO` edges.

---

## 2. Environment Configuration

To connect directly to TigerGraph Savanna or an on-premise TigerGraph instance, set the following environment variables:

| Variable | Description | Example |
|---|---|---|
| `TG_HOST` | TigerGraph instance URL | `https://your-domain.i.tgcloud.io` |
| `TG_GRAPH` | Graph name | `FraudGraph` |
| `TG_USERNAME` | TigerGraph user | `tigergraph` |
| `TG_PASSWORD` | TigerGraph password | `your_password` |
| `TG_SECRET` | RESTPP API Secret | `your_secret_hash` |
| `TG_TOKEN` | RESTPP Auth Token (optional) | `your_auth_token` |

If `TG_HOST` is not set or the TigerGraph endpoint is unreachable, the client automatically falls back to indexed queries against `data/processed/`, ensuring zero downtime during development or offline runs.

---

## 3. Tool Execution & Audit Trail

Every MCP tool call is measured, audited, and logged within the investigation context:
- **`latency_ms`**: Wall-clock execution time recorded per call.
- **`result_summary`**: Concise output description (e.g. `Found 299 connected cards`).
- **`status`**: Execution status (`success` / `error`).

Tool executions are captured in the `investigation_path` array in each generated case file:
```json
{
  "step": 2,
  "tool": "query_shared_devices",
  "input": { "txn_id": "3450629" },
  "result_summary": "Found 299 connected cards",
  "latency_ms": 415.68,
  "status": "success"
}
```

---

## 4. Case Memory Persistence

When an investigation closes, `write_case()` writes the record to TigerGraph:
- **Vertex**: `Case` (`case_id`, `status`, `verdict`, `fraud_probability`, `pattern`, `exposure_usd`, `evidence_json`, `actions_json`, `sar_json`, etc.)
- **Edges**:
  - `Case` $\to$ `CASE_ON_CARD` $\to$ `Card`
  - `Case` $\to$ `CASE_INVOLVES` $\to$ `Transaction` (all `affected_txn_ids`)
  - `Case` $\to$ `CASE_CONNECTED_TO` $\to$ `Card` (all `connected_card_ids`)

This ensures subsequent investigations can immediately discover and cite newly closed cases via graph traversals and GraphRAG memory.
