# Autonomous Fraud Investigation at Scale: Graph-Native Multi-Agent Orchestration with TigerGraph & GraphRAG

**TigerGraph Agentic Fraud Investigation Hackathon 2026**  
**Team Name:** GOA-T  
**Team Members:**
- **Thota Sai Eswar Srinath** (Team Leader & Agentic Architecture)
- **Nikhil Kadiri** (Graph Systems & TigerGraph Traversal Engineering)
- **Bondugula Pranav Teja** (Policy Engine & GraphRAG Implementation)

**Live Cockpit:** [https://task-4-nvan.onrender.com/](https://task-4-nvan.onrender.com/)  
**GitHub Repository:** [https://github.com/tsrinath2007/Task-4](https://github.com/tsrinath2007/Task-4)  
**20-Case Benchmark Report:** [docs/BENCHMARK_REPORT.md](BENCHMARK_REPORT.md)  
**Demo Video Script:** [docs/DEMO_VIDEO_SCRIPT.md](DEMO_VIDEO_SCRIPT.md)  
**Social Media Post:** [docs/SOCIAL_POST.md](SOCIAL_POST.md)  

---

## Executive Summary

Financial institutions face hundreds of thousands of transaction alerts daily. Modern machine-learning fraud engines score transactions probabilistically, but a high risk score is merely an alert—never an actionable verdict. Above a 0.70 score threshold, the majority of flagged transactions turn out to be legitimate cardholder activity (e.g., recurring subscriptions, out-of-region travel, or authorized family purchases). Conversely, sophisticated card testing rings and credential-stuffing syndicates deliberately operate below threshold limits to avoid triggering single-event alerts.

Manual fraud investigation is slow, cognitively exhausting, and inconsistent. Human analysts must manually cross-reference cardholder spending baselines, multi-hop entity linkages, regulatory mandates (FinCEN Suspicious Activity Reports under 31 CFR §1020.320), and strict bank governance rules.

To solve this, **Team GOA-T** created **SENTINEL**: an evidence-driven, policy-constrained autonomous fraud investigation agent and interactive analyst cockpit. Tested on **590,742 IEEE-CIS / Vesta transactions**, **5,565 closed historical cases**, and evaluated across **20 benchmark exam cases (`HHG-001` to `HHG-020`)**, SENTINEL achieves **100% policy compliance** (20/20 PASS) with **$5,174.77 total fraud exposure secured**, automated FinCEN Form 111 XML generation, and live sub-second TigerGraph Model Context Protocol (MCP) tool execution.

---

## 1. What We Built

SENTINEL is an end-to-end, graph-native autonomous fraud investigation system comprising:

1. **Live TigerGraph Savanna Cloud & MCP Client**: Real-time multi-hop traversal of cardholder accounts, shared devices, and prior fraud rings across **1,450,883 transactions, 137,211 cards, and 128,110 device profiles** on live TigerGraph Savanna Cloud (`Transaction_Fraud` graph).
2. **Hybrid GraphRAG Memory**: 384-dimensional dense semantic embeddings (`sentence-transformers/all-MiniLM-L6-v2`) fused with topological graph adjacency boosts (+0.15 score). Uniquely, SENTINEL indexes 900 historical cleared cases to act as negative evidence and prevent false positives.
3. **8 Deterministic Fraud Detectors & Legitimacy Checklist**: Zero-hallucination heuristic rules detecting card testing, shared device syndicates, out-of-region travel, recurring merchant subscriptions, and account takeovers.
4. **Deterministic Policy Engine (R1–R10)**: Pure deterministic Python enforcing bank policy rules R1 through R10, approval routes (`auto`, `L1` Lead, `L2` Manager), and FinCEN SAR filing requirements. The LLM is never permitted to select actions or assign approval routes.
5. **Dynamic Next-Best Action Engine**: Evaluates pre-evidence actions, determines when further evidence is needed, executes customer validation or step-up authentication, and updates post-evidence recommendations with full audit reasoning (`what_changed`) across 100% of cases.
6. **LLM Synthesis & Explanation**: Powered by Groq LLaMA 3.3 70B for executive case summaries, regulatory FinCEN Form 111 SAR narratives, and action justifications. Includes deterministic fallback if the API is offline.
7. **Interactive Analyst Web Cockpit**: High-performance dashboard with zero build dependencies, featuring live SVG multi-hop graph visualizers, interactive evidence steppers, watchlist managers, FinCEN Form 111 XML batch export, CSV compliance audit logs, and an AI copilot.
8. **Live MCP Investigation Modal**: Allows analysts or judges to select any case and execute an end-to-end autonomous investigation live against the TigerGraph Savanna cluster in ~1.2s, with live RESTPP tool calls and automatic case vertex write-back.

---

## 2. System Architecture

SENTINEL strictly decouples deterministic graph traversals and policy enforcement from probabilistic LLM synthesis:

```text
       +-------------------------------------------------------------+
       |                        ALERT TRIGGER                        |
       |  (Risk Score Alert / Customer Dispute / Analyst Escalation)  |
       +------------------------------+------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |             TIGERGRAPH CLOUD MCP TOOL SUITE                 |
       |   - query_customer_cards     - query_card_history           |
       |   - query_shared_devices     - query_prior_cases            |
       |   - write_case (Runtime Case Vertex & Relationship Upsert)  |
       +------------------------------+------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |                EVIDENCE GATHERING LAYER                     |
       |   - 8 Deterministic Detectors                               |
       |   - Card-Specific Legitimacy Checklist (9 Baseline Tests)   |
       |   - GraphRAG Hybrid Memory (Semantic + Adjacency Boost)     |
       +------------------------------+------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |                 DETERMINISTIC POLICY ENGINE                 |
       |   - Authoritative Rules R1 to R10                           |
       |   - Route Enforcement: auto | L1 (Lead) | L2 (Manager)      |
       |   - Initial Action Determination (Pre-Evidence)             |
       +------------------------------+------------------------------+
                                      |
                    [Evidence Request Required?]
                                   /       \
                              YES /         \ NO
                                 v           v
         +----------------------------+       |
         | EVIDENCE SIMULATION LOOP   |       |
         | - Customer Validation      |       |
         | - Step-up Authentication   |       |
         +--------------+-------------+       |
                        |                     |
                        v                     |
         +----------------------------+       |
         | REASSESSMENT & FINAL RULES |       |
         | - decide_after_evidence()  |<------+
         +--------------+-------------+
                        |
                        v
       +-------------------------------------------------------------+
       |                 GROQ LLaMA 3.3 70B ADAPTER                  |
       |   - Structured Adjudication & Evidence Formatting           |
       |   - Action Explanation citing Policy Rules                  |
       |   - Regulatory FinCEN SAR Narrative Generation              |
       +------------------------------+------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |                     PERSISTENCE & EXPORT                    |
       |   - TigerGraph Savanna Case Vertex & Edge Upsert            |
       |   - Standardized Answer JSON (cases/generated/<id>.json)    |
       |   - FinCEN Form 111 XML Batch Export & Audit CSV            |
       +-------------------------------------------------------------+
```

---

## 3. How TigerGraph is Used

### Why Relational Databases Fail for Fraud Rings
In relational SQL databases, detecting a multi-card fraud syndicate requires recursive self-joins across transactions, cards, and device tables containing hundreds of millions of rows:

```sql
-- Relational 4-JOIN Query (Fails under sub-second SLAs on 590K+ records)
SELECT c2.card_id, count(*) 
FROM transactions t1
JOIN cards c1 ON t1.card_id = c1.card_id
JOIN device_profiles d ON t1.device_id = d.device_id
JOIN transactions t2 ON t2.device_id = d.device_id
JOIN cards c2 ON t2.card_id = c2.card_id
WHERE c1.card_id != c2.card_id AND t1.transaction_id = '3478561'
GROUP BY c2.card_id;
```

Joining 3 high-volume tables across millions of records requires scanning massive secondary indexes and materializing large temporary tables. Under high transaction volume, running multi-hop relational joins triggers table locks, query timeouts (>5s), or forces financial institutions to rely on stale overnight batch jobs.

### Multi-Hop Graph Traversal in TigerGraph
In TigerGraph, uncovering a multi-card fraud syndicate requires traversing:
$$\text{Transaction} \xrightarrow{\text{FROM\_DEVICE}} \text{DeviceProfile} \xrightarrow{\text{USED\_ON}} \text{Card} \xrightarrow{\text{HAS\_CLOSED\_CASE}} \text{ClosedCase}$$

In GSQL, this 3-hop traversal executes in sub-second latency across 590,000+ transactions:
```gsql
CREATE OR REPLACE QUERY find_shared_device_ring(STRING txnId) FOR GRAPH Transaction_Fraud {
  StartTxn = {Transaction.*};
  TargetTxn = SELECT t FROM StartTxn:t WHERE t.TransactionID == txnId;
  
  // Hop 1: Find DeviceProfile
  Dev = SELECT d FROM TargetTxn:t -(FROM_DEVICE:e)-> DeviceProfile:d;
  
  // Hop 2: Find all cards used on this device
  ConnectedCards = SELECT c FROM Dev:d -(USED_ON:e)-> Card:c;
  
  // Hop 3: Find prior fraud history
  PriorFraud = SELECT cc FROM ConnectedCards:c -(HAS_CLOSED_CASE:e)-> ClosedCase:cc 
               WHERE cc.outcome == "fraud";
  
  PRINT ConnectedCards.size() AS syndicate_size, ConnectedCards, PriorFraud;
}
```

In benchmark cases `HHG-014` and `HHG-017`, this single graph lookup discovered device profiles connecting **299 distinct card accounts** across disparate cardholder names.

### Graph Schema Architecture
Our live TigerGraph Savanna schema defines:
- **Vertices**: `Customer`, `Card`, `Transaction`, `DeviceProfile`, `BillingRegion`, `EmailDomain`, `ClosedCase`, and runtime `Case`.
- **Edges**: 
  - `Customer` $\xrightarrow{\text{OWNS}}$ `Card`
  - `Card` $\xrightarrow{\text{MADE}}$ `Transaction`
  - `Transaction` $\xrightarrow{\text{FROM\_DEVICE}}$ `DeviceProfile`
  - `Transaction` $\xrightarrow{\text{BILLED\_IN}}$ `BillingRegion`
  - `Transaction` $\xrightarrow{\text{PURCHASER\_EMAIL}}$ `EmailDomain`
  - `Transaction` $\xrightarrow{\text{NEXT}}$ `Transaction` (temporal sequence with gap)
  - `ClosedCase` $\xrightarrow{\text{ON\_CARD}}$ `Card`, `ClosedCase` $\xrightarrow{\text{INVOLVES}}$ `Transaction`
  - `Case` $\xrightarrow{\text{CASE\_ON\_CARD}}$ `Card`, `Case` $\xrightarrow{\text{CASE\_INVOLVES}}$ `Transaction`, `Case` $\xrightarrow{\text{CASE\_CONNECTED\_TO}}$ `Card`

### TigerGraph Model Context Protocol (MCP) Tools
SENTINEL equips the autonomous agent with 5 specialized TigerGraph MCP tools (`src/graph/mcp_client.py`):
- `query_customer_cards(customer_id)`: Fetches the customer's entire active card portfolio.
- `query_card_history(card_id, limit)`: Retrieves the temporal transaction stream on the subject card.
- `query_shared_devices(txn_id)`: Executes 4-hop graph expansion to detect shared hardware devices.
- `query_prior_cases(card_id)`: Retrieves past investigations on the focal card.
- `write_case(case_data)`: Persists newly closed investigations back into the live TigerGraph cluster as `Case` vertices with incident edges.

---

## 4. Agentic Capabilities Implemented

### A. Deterministic Fraud Detectors & Heuristics
Rather than delegating pattern recognition to LLMs, 8 specialized Python detectors execute card-specific heuristics:
1. **`recurring_merchant_scan`**: Evaluates periodic intervals (28–34 days) for identical amounts on high-velocity cards to distinguish legitimate monthly subscriptions from recurring disputes.
2. **`card_testing_scan`**: Detects rapid sequences of micro-authorizations ($< \$10$) within 4 hours followed by larger purchases, or rapid clusters of test authorizations within 2 hours.
3. **`shared_device_scan`**: Evaluates whether the transaction device profile is linked to $\ge 2$ other cards or prior fraud cases.
4. **`new_device_scan`**: Checks if the device is tagged `New` for this cardholder or appears for the first time in account history.
5. **`out_of_region_scan`**: Flags card-present transactions in billing regions outside the cardholder's historical baseline, differentiating multi-day travel from single isolated clones.
6. **`cnp_burst_scan`**: Detects bursts of card-not-present authorizations exceeding baseline velocity by $3\times$ within 48 hours.
7. **`account_takeover_scan`**: Flags conflicting digital identity signatures (abrupt OS/browser changes combined with match-flag discrepancies).
8. **`shared_region_scan`**: Flags clusters of unrelated cards originating from identical billing regions tied to prior fraud episodes.

### B. GraphRAG: Hybrid Vector Memory + Topological Adjacency
Standard RAG searches text embeddings in isolation, missing structural network relationships. GraphRAG in SENTINEL combines both:
1. **Dense Semantic Search**: Case summaries and analyst notes from 5,565 historical cases are embedded into 384-dimensional dense vectors using `sentence-transformers/all-MiniLM-L6-v2` and searched via cosine similarity.
2. **Graph Adjacency**: Simultaneously, the graph is queried for cases sharing the exact `device_id`, `addr1` region, or `customer_id`.
3. **Relevance Fusion**: Graph-adjacent cases receive a **+0.15 priority boost**. If a case matches both semantically and shares graph topology, it is prioritized at the top of retrieved context.
4. **Cleared Cases as Negative Evidence**: All 900 historical cleared cases (`outcome='cleared'`) are indexed. In `HHG-003`, historical cleared cases `CC-4922` and `CC-4718` proved that recurring disputes on this merchant category were routinely cleared as legitimate cardholder billing confusion, preventing a false-positive card block.

### C. Deterministic Policy Engine (R1–R10)
Action selection is 100% deterministic Python. The LLM is never permitted to select actions or choose approval routes:
- **R1**: Weak single signals ($p < 0.70$) require `VERIFY_WITH_CUSTOMER` or `STEP_UP_AUTH` before blocking.
- **R2**: Customer denial triggers `BLOCK_CARD` and `CREATE_CASE`. If exposure $> \$1,000$ or connected to a ring, add `FILE_REPORT` (L2).
- **R3**: Customer confirmation triggers `CLOSE_NO_FRAUD` and `ALLOW_TRANSACTION`.
- **R4**: No reply in 24 hours triggers `MONITOR_CARD` and `DECLINE_TRANSACTION`.
- **R5**: Card testing triggers `DECLINE_TRANSACTION` and `STEP_UP_AUTH`.
- **R6**: Shared origin ($\ge 3$ cards) triggers `CREATE_CASE`, `FILE_REPORT` (L2), and `MONITOR_CONNECTED_CARDS`.
- **R7**: Disputed recurring charges trigger `CREATE_CASE`, `VERIFY_WITH_CUSTOMER`, and `WARN_CUSTOMER`. **Blocking is prohibited.**
- **R8**: Uncertain cases with exposure $> \$500$ escalate to human analysts (`ESCALATE_TO_ANALYST`).
- **R9**: Undocumented patterns trigger `CREATE_CASE`, `FILE_REPORT` (L2), and `ESCALATE_TO_ANALYST`.
- **R10**: `BLOCK_ALL_CARDS` is prohibited unless $\ge 2$ cards have confirmed fraud.

### D. Dynamic Next-Best Action Progression
Policy recommendations are dynamic across 100% of investigations:
1. **Initial Recommendation**: Formulated before customer contact (e.g., `VERIFY_WITH_CUSTOMER`, `MONITOR_CONNECTED_CARDS`, `CREATE_CASE`, `FILE_REPORT`).
2. **Simulation**: The agent simulates customer validation based on detector findings. If an unfamiliar shared device was used, customer denial is received.
3. **Reassessment**: Upon receiving denial, `decide_after_evidence()` updates the actions to `BLOCK_CARD` (L1), preserving `MONITOR_CONNECTED_CARDS` and `FILE_REPORT`.
4. **Audit Trail**: The `what_changed` field explicitly explains how incoming evidence altered the bank's response.

### E. Agent State Machine & Stopping Rule §6
The agent advances through 8 discrete states:
1. `TRIGGER` $\to$ 2. `INVESTIGATE` $\to$ 3. `GATHER_EVIDENCE` $\to$ 4. `ASSESS_UNCERTAINTY` $\to$ 5. `GATHER_MORE_EVIDENCE` $\to$ 6. `REASSESS` $\to$ 7. `RECOMMEND_ACTION` $\to$ 8. `UPDATE_CASE_MEMORY`.

**Stopping Rule (§6)**: The agent terminates investigation when:
- Fraud probability reaches $\ge 0.85$ or $\le 0.15$ supported by $\ge 2$ independent pieces of evidence.
- A simulated customer or auth verification response settles the dispute.
- Further graph traversals are mathematically guaranteed not to alter the policy action.

---

## 5. Benchmark Exam Results (20/20 Ground-Truth Cases)

Every team is evaluated on the 20 ground-truth benchmark exam cases (`HHG-001` through `HHG-020`). Running `python scripts/validate_answers.py` yields **100% compliance**:

| Case ID | Trigger Type | Verdict | Fraud Prob | Primary Pattern | Exposure ($) | SAR Filed | Initial Actions | Final Actions | Validation |
| :--- | :--- | :--- | :---: | :--- | :---: | :---: | :--- | :--- | :---: |
| **HHG-001** | `risk_score` (0.61) | Legitimate | 0.07 | `none` (Recurring) | $77.07 | NO | `VERIFY_WITH_CUSTOMER`, `WARN_CUSTOMER` | `ALLOW_TRANSACTION` [AUTO], `CLOSE_NO_FRAUD` [AUTO] | **PASS** |
| **HHG-002** | `risk_score` (0.79) | Fraud | 0.95 | `card_not_present_fraud` | $292.36 | NO | `DECLINE_TRANSACTION`, `VERIFY_WITH_CUSTOMER` | `BLOCK_CARD` [L1], `CREATE_CASE` [AUTO] | **PASS** |
| **HHG-003** | `customer_report` | Legitimate | 0.07 | `none` (Recurring) | $49.00 | NO | `VERIFY_WITH_CUSTOMER`, `WARN_CUSTOMER` | `ALLOW_TRANSACTION` [AUTO], `CLOSE_NO_FRAUD` [AUTO] | **PASS** |
| **HHG-004** | `customer_report` | Fraud | 0.90 | `card_testing` | $55.89 | **YES (L2)** | `VERIFY_WITH_CUSTOMER`, `MONITOR_CONNECTED_CARDS` | `BLOCK_CARD` [L1], `MONITOR_CONNECTED_CARDS` [AUTO] | **PASS** |
| **HHG-005** | `risk_score` (0.54) | Fraud | 0.94 | `card_not_present_new_device` | $100.07 | **YES (L2)** | `VERIFY_WITH_CUSTOMER`, `MONITOR_CONNECTED_CARDS` | `BLOCK_CARD` [L1], `MONITOR_CONNECTED_CARDS` [AUTO] | **PASS** |
| **HHG-006** | `customer_report` | Fraud | 0.93 | `card_testing` | $1,906.07 | **YES (L2)** | `VERIFY_WITH_CUSTOMER`, `MONITOR_CONNECTED_CARDS` | `BLOCK_CARD` [L1], `MONITOR_CONNECTED_CARDS` [AUTO] | **PASS** |
| **HHG-007** | `risk_score` (0.87) | Legitimate | 0.08 | `none` (Subscription) | $111.92 | NO | `VERIFY_WITH_CUSTOMER`, `WARN_CUSTOMER` | `ALLOW_TRANSACTION` [AUTO], `CLOSE_NO_FRAUD` [AUTO] | **PASS** |
| **HHG-008** | `customer_report` | Legitimate | 0.07 | `none` (Recurring) | $55.68 | NO | `VERIFY_WITH_CUSTOMER`, `WARN_CUSTOMER` | `ALLOW_TRANSACTION` [AUTO], `CLOSE_NO_FRAUD` [AUTO] | **PASS** |
| **HHG-009** | `customer_report` | Fraud | 0.95 | `card_not_present_new_device` | $30.02 | **YES (L2)** | `VERIFY_WITH_CUSTOMER`, `MONITOR_CONNECTED_CARDS` | `BLOCK_CARD` [L1], `MONITOR_CONNECTED_CARDS` [AUTO] | **PASS** |
| **HHG-010** | `risk_score` (0.90) | Fraud | 0.96 | `card_not_present_new_device` | $1,000.03 | **YES (L2)** | `VERIFY_WITH_CUSTOMER`, `MONITOR_CONNECTED_CARDS` | `BLOCK_CARD` [L1], `MONITOR_CONNECTED_CARDS` [AUTO] | **PASS** |
| **HHG-011** | `customer_report` | Legitimate | 0.08 | `none` (Recurring) | $131.30 | NO | `VERIFY_WITH_CUSTOMER`, `WARN_CUSTOMER` | `ALLOW_TRANSACTION` [AUTO], `CLOSE_NO_FRAUD` [AUTO] | **PASS** |
| **HHG-012** | `risk_score` (0.55) | Legitimate | 0.07 | `none` (Recurring) | $30.91 | NO | `VERIFY_WITH_CUSTOMER`, `WARN_CUSTOMER` | `ALLOW_TRANSACTION` [AUTO], `CLOSE_NO_FRAUD` [AUTO] | **PASS** |
| **HHG-013** | `risk_score` (0.76) | Fraud | 0.95 | `card_not_present_new_device` | $35.66 | **YES (L2)** | `VERIFY_WITH_CUSTOMER`, `MONITOR_CONNECTED_CARDS` | `BLOCK_CARD` [L1], `MONITOR_CONNECTED_CARDS` [AUTO] | **PASS** |
| **HHG-014** | `analyst_request` | Fraud | 0.95 | `card_not_present_new_device` | $74.96 | **YES (L2)** | `VERIFY_WITH_CUSTOMER`, `MONITOR_CONNECTED_CARDS` | `BLOCK_CARD` [L1], `MONITOR_CONNECTED_CARDS` [AUTO] | **PASS** |
| **HHG-015** | `risk_score` (0.77) | Fraud | 0.92 | `card_not_present_new_device` | $599.94 | **YES (L2)** | `VERIFY_WITH_CUSTOMER`, `MONITOR_CONNECTED_CARDS` | `BLOCK_CARD` [L1], `MONITOR_CONNECTED_CARDS` [AUTO] | **PASS** |
| **HHG-016** | `customer_report` | Fraud | 0.94 | `card_not_present_new_device` | $59.67 | **YES (L2)** | `VERIFY_WITH_CUSTOMER`, `MONITOR_CONNECTED_CARDS` | `BLOCK_CARD` [L1], `MONITOR_CONNECTED_CARDS` [AUTO] | **PASS** |
| **HHG-017** | `risk_score` (0.57) | Fraud | 0.93 | `card_testing` | $300.14 | **YES (L2)** | `VERIFY_WITH_CUSTOMER`, `MONITOR_CONNECTED_CARDS` | `BLOCK_CARD` [L1], `MONITOR_CONNECTED_CARDS` [AUTO] | **PASS** |
| **HHG-018** | `customer_report` | Legitimate | 0.07 | `none` (Recurring) | $39.08 | NO | `VERIFY_WITH_CUSTOMER`, `WARN_CUSTOMER` | `ALLOW_TRANSACTION` [AUTO], `CLOSE_NO_FRAUD` [AUTO] | **PASS** |
| **HHG-019** | `risk_score` (0.90) | Fraud | 0.91 | `card_not_present_new_device` | $99.92 | **YES (L2)** | `VERIFY_WITH_CUSTOMER`, `MONITOR_CONNECTED_CARDS` | `BLOCK_CARD` [L1], `MONITOR_CONNECTED_CARDS` [AUTO] | **PASS** |
| **HHG-020** | `risk_score` (0.52) | Fraud | 0.95 | `card_not_present_new_device` | $125.08 | **YES (L2)** | `VERIFY_WITH_CUSTOMER`, `MONITOR_CONNECTED_CARDS` | `BLOCK_CARD` [L1], `MONITOR_CONNECTED_CARDS` [AUTO] | **PASS** |

### Aggregate Benchmark Metrics
- **Validation Pass Rate**: **20 / 20 (100% PASS)**
- **Verdict Distribution**: 13 Fraud (65%), 7 Legitimate (35%)
- **Regulatory Filings**: 12 FinCEN Form 111 SARs filed (100% Route `L2` Supervisory Approval)
- **Total Fraud Exposure Managed**: **$5,174.77 USD**
- **Average Fraud Probability (Fraud Cases)**: **93.5%**
- **Average Fraud Probability (Legitimate Cases)**: **7.3%**
- **Dynamic Policy Progression**: In **20 out of 20 cases (100%)**, initial hypotheses and action sets were dynamically updated post-evidence.
- **Runtime Latency**: Live fast-path TigerGraph investigation completes in **~1.2 seconds**.

---

## 6. What We Learned

1. **Separation of Policy and Reasoning is Vital**: Early prototypes that allowed the LLM to choose actions frequently violated approval hierarchies (e.g., assigning `auto` approval to `FILE_REPORT` or blocking accounts on recurring subscriptions). Restricting action selection to deterministic Python while letting the LLM generate justifications produced 100% compliance.
2. **Negative Evidence is as Important as Positive Evidence**: Most fraud memory systems only store confirmed fraud cases. By indexing 900 cleared cases in GraphRAG, SENTINEL actively recognized legitimate customer patterns (e.g., gym memberships, recurring cloud hosting) and defended genuine transactions against false-positive card cancellations.
3. **Graph Adjacency Supercharges Embeddings**: Pure semantic embeddings often grouped completely unrelated transactions together based on surface keywords. Combining vector similarity with topological graph adjacency (+0.15 boost for shared device or customer nodes) pinpointed the exact historical precedent every time.
4. **Card ID Ordering Matters**: Reconstructing customer card portfolios from unmasked IEEE-CIS tables required sorting `NaN` cards first (`K1`) before sequential floats (`K2`, `K3`) to ensure deterministic key mapping across all 590,000 transactions.
5. **Asynchronous UI Orchestration**: In real-time investigation cockpits, asynchronous frontend streaming must be strictly sequenced. Replacing uncoordinated timers with sequential async pipelines eliminates race conditions and delivers crisp, reliable user feedback during live demonstrations.

---

## 7. What We Would Improve With More Time

1. **Inductive Graph Neural Networks (GNNs)**: Train a Graph Convolutional Network (GCN) or Relational Graph Convolutional Network (RGCN) directly inside TigerGraph to score structural risk embeddings before agent execution.
2. **Live Kafka Stream Ingestion**: Connect TigerGraph Kafka Loader to ingest authorization transactions in real-time, executing the agent state machine within sub-second streaming windows.
3. **Multi-Party Human-in-the-Loop Webhooks**: Integrate Slack and Microsoft Teams webhooks allowing Level 1 and Level 2 fraud managers to approve `BLOCK_CARD` and `FILE_REPORT` actions with a single click.
4. **Direct FinCEN BSA E-Filing Gateway**: Transmit the generated FinCEN Form 111 XML directly into the BSA E-Filing System sandbox for fully end-to-end automated regulatory submission.

---

## Hackathon Rubric Alignment

| Rubric Category | Weight | How SENTINEL Delivers | Verified Evidence |
| :--- | :---: | :--- | :--- |
| **Investigation Accuracy** | **25%** | 8 deterministic detectors + legitimacy checklist across 590K txns. Calibrated 13 Fraud, 7 Legitimate, 0 False Positives. | `src/detectors/`, `cases/generated/*.json` (20/20 PASS) |
| **Next Best Action** | **25%** | Pre-evidence vs post-evidence action gating with strict approval routes (`auto`, `L1`, `L2`). | `src/policy/policy_engine.py`, `what_changed` field in all 20 cases |
| **Case Summary & Explainability**| **10%** | Groq LLaMA 3.3 70B synthesis citing policy rules, full FinCEN Form 111 SAR narratives, tool latency audit logs. | `src/agent/llm_adapter.py`, SAR panel in web cockpit |
| **Agentic Design & Engineering** | **15%** | 8-stage state machine, Stopping Rule §6, TigerGraph MCP client, runtime graph write-back. | `src/agent/orchestrator.py`, `src/graph/mcp_client.py` |
| **Innovation** | **15%** | GraphRAG 384-d embeddings + graph adjacency boost (+0.15), cleared cases indexed as negative evidence. | `src/memory/retriever.py`, `scripts/embed_cases.py` |
| **Demo Quality & Completeness** | **10%** | Web cockpit with SVG graph visualizer, live TigerGraph MCP investigation modal, AI Copilot, video demo script, and social post templates. | [Live Cockpit](https://task-4-nvan.onrender.com/), `docs/DEMO_VIDEO_SCRIPT.md` |

---

*Team GOA-T — Thota Sai Eswar Srinath, Nikhil Kadiri, Bondugula Pranav Teja*
