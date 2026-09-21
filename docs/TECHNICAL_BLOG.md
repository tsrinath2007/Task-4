# Autonomous Fraud Investigation at Scale: Graph-Native Multi-Agent Orchestration with TigerGraph & GraphRAG

*Building an evidence-driven, policy-constrained autonomous fraud investigator on 590,000+ IEEE-CIS/Vesta transactions and 5,565 closed cases.*

---

## 1. Problem — Why Fraud Investigation is Hard at Scale

Financial institutions face hundreds of thousands of transaction alerts daily. Modern real-time fraud models score transactions probabilistically, but a high risk score is merely an alert—never a verdict. Above a 0.70 score threshold, the majority of flagged transactions turn out to be legitimate cardholder activity (e.g., travel, subscriptions, or authorized high-value purchases). Conversely, sophisticated card testing rings and credential-stuffing syndicates deliberately operate below threshold limits to avoid real-time detection.

Manual fraud investigation is slow, cognitively exhausting, and inconsistent. Human analysts must manually cross-reference:
- Cardholder historical baselines (spending percentiles, typical merchant categories, home billing locations).
- Multi-hop entity linkages (shared devices, common IP subnets, compromised merchants).
- Regulatory mandates (FinCEN Suspicious Activity Report [SAR] filing standards).
- Bank governance policies (approval routing, customer validation before card cancellation).

Scaling this process requires more than simple LLM prompting. LLMs hallucinate rules, struggle with multi-hop graph topology, and cannot be trusted to unilaterally execute irreversible policy actions like blocking cards or filing federal regulatory reports.

---

## 2. Dataset — IEEE-CIS / Vesta Edition

The benchmark dataset comprises real-world transaction patterns from the **IEEE-CIS Fraud Detection** dataset published by Vesta Corporation:
- **590,742 transactions**: Preserving all original 393 Vesta features (masked C, D, M, V numeric flags, amounts, timestamps, and product codes) augmented with derived customer identifiers (`customer_id`), real calendar timestamps (`ts`), and transaction channels (`in_person` vs `online`).
- **144,432 identity records**: Device models, OS versions, browser families, screen resolutions, and proxy ratings for online card authorizations.
- **5,565 historical closed cases**: The sole repository of ground truth from July to October 2016, containing 4,665 confirmed fraud cases and 900 cleared cases (false alarms, disputed recurring subscriptions, and legitimate travel).
- **20 exam benchmark cases (`HHG-001` to `HHG-020`)**: Diverse November and December alerts spanning risk score triggers, customer disputes, and analyst escalation requests.

---

## 3. Architecture — End-to-End System Pipeline

The Sentinel autonomous architecture separates deterministic evidence gathering and strict policy governance from probabilistic LLM synthesis:

```text
       +-------------------------------------------------------------+
       |                        ALERT TRIGGER                        |
       |  (Risk Score Alert / Customer Dispute / Analyst Escalation)  |
       +------------------------------+------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |                  TIGERGRAPH MCP TRAVERSAL                   |
       |   - Card History           - Customer Card Portfolio        |
       |   - Shared Device Rings    - Prior Closed Cases             |
       +------------------------------+------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |                EVIDENCE GATHERING LAYER                     |
       |   - 8 Deterministic Detectors                               |
       |   - Card-Specific Legitimacy Checklist                      |
       |   - GraphRAG Hybrid Memory (Semantic + Adjacency Boost)     |
       +------------------------------+------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |                 DETERMINISTIC POLICY ENGINE                 |
       |   - Authoritative Rules R1 to R10                           |
       |   - Route Enforcement: auto | L1 (Lead) | L2 (Manager)     |
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
       |   - TigerGraph Case Vertex Upsert                           |
       |   - Standardized Answer JSON (cases/generated/<id>.json)    |
       +-------------------------------------------------------------+
```

---

## 4. Why TigerGraph — Traversals Impossible in SQL

In relational SQL databases, tracking fraud rings requires recursive, deeply nested joins across tables with hundreds of millions of rows. Relational schemas break down when querying entity networks where the depth of connection is unknown in advance.

### The Shared Device Ring Traversal:
In TigerGraph, uncovering a multi-card fraud syndicate requires traversing:
$$\text{Transaction} \xrightarrow{\text{FROM\_DEVICE}} \text{DeviceProfile} \xrightarrow{\text{USED\_ON}} \text{Card} \xrightarrow{\text{HAS\_CLOSED\_CASE}} \text{ClosedCase}$$

In GSQL, this 3-hop traversal executes in sub-second latency across 590,000+ transactions:
```gsql
SELECT c 
FROM Transaction:t -(FROM_DEVICE)-> DeviceProfile:d -(USED_ON)-> Card:c -(HAS_CLOSED_CASE)-> ClosedCase:cc
WHERE t.id == target_txn_id;
```
In benchmark case `HHG-014` and `HHG-017`, this single graph lookup discovered device profile `D007287` connecting **299 distinct card accounts** across disparate cardholder names. Relational SQL queries doing self-joins across millions of rows to find this ring either timed out or required complex batch pre-aggregations.

---

## 5. Graph Schema — Key Vertices & Edges

The graph schema is optimized for real-time investigation traversals and case memory persistence:

### Primary Vertices:
- `Customer`: Primary cardholder entity (`customer_id`).
- `Card`: Individual payment instrument (`card_id`, e.g., `C04570-K1`).
- `Transaction`: Authorization record (`TransactionID`, `TransactionAmt`, `ProductCD`, `ts`, `channel`, `risk_score`).
- `DeviceProfile`: Composite digital fingerprint (`device_id`, `DeviceInfo`, `id_30` OS, `id_31` browser, `id_33` screen).
- `BillingRegion`: Anonymized geographical billing code (`addr1`).
- `EmailDomain`: Domain of purchaser email (`P_emaildomain`).
- `ClosedCase`: Historical case record (`case_id`, `outcome`, `pattern`, `exposure_usd`, `analyst_notes`).
- `Case`: Newly generated investigation vertex storing status, verdict, probability, actions, and serialized evidence JSON.

### Key Edges:
- `Customer` $\xrightarrow{\text{OWNS}}$ `Card`
- `Card` $\xrightarrow{\text{MADE}}$ `Transaction`
- `Transaction` $\xrightarrow{\text{FROM\_DEVICE}}$ `DeviceProfile`
- `Transaction` $\xrightarrow{\text{BILLED\_IN}}$ `BillingRegion`
- `Transaction` $\xrightarrow{\text{PURCHASER\_EMAIL}}$ `EmailDomain`
- `Transaction` $\xrightarrow{\text{NEXT}}$ `Transaction` (ordered by `ts` per card)
- `ClosedCase` $\xrightarrow{\text{ON\_CARD}}$ `Card`, `ClosedCase` $\xrightarrow{\text{INVOLVES}}$ `Transaction`
- `Case` $\xrightarrow{\text{CASE\_ON\_CARD}}$ `Card`, `Case` $\xrightarrow{\text{CASE\_INVOLVES}}$ `Transaction`, `Case` $\xrightarrow{\text{CASE\_CONNECTED\_TO}}$ `Card`

---

## 6. Eight Deterministic Detectors

Rather than relying on LLM intuition, 8 specialized Python detectors execute card-specific heuristics:

1. **`recurring_merchant_scan`**: Evaluates periodic intervals (28–34 days) for identical amounts on high-velocity cards to distinguish legitimate monthly subscriptions from recurring disputes.
2. **`card_testing_scan`**: Detects rapid sequences of micro-authorizations ($< \$10$) within 4 hours followed by larger purchases, or rapid clusters of test authorizations within 2 hours.
3. **`shared_device_scan`**: Evaluates whether the transaction device profile is linked to $\ge 2$ other cards or prior fraud cases.
4. **`new_device_scan`**: Checks if the device is tagged `New` for this cardholder or appears for the first time in account history.
5. **`out_of_region_scan`**: Flags card-present transactions in billing regions outside the cardholder's historical baseline, differentiating multi-day travel from single isolated clones.
6. **`cnp_burst_scan`**: Detects bursts of card-not-present authorizations exceeding baseline velocity by $3\times$ within 48 hours.
7. **`account_takeover_scan`**: Flags conflicting digital identity signatures (abrupt OS/browser changes combined with match-flag discrepancies).
8. **`shared_region_scan`**: Flags clusters of unrelated cards originating from identical billing regions tied to prior fraud episodes.

---

## 7. GraphRAG — How Semantic + Graph Adjacency Work Together

Standard RAG searches text embeddings in isolation, missing structural network relationships. GraphRAG in Sentinel combines both:
1. **Semantic Search**: Case summaries and analyst notes are embedded into 384-dimensional dense vectors using `sentence-transformers/all-MiniLM-L6-v2` and searched via cosine similarity.
2. **Graph Adjacency**: Simultaneously, the graph is queried for cases sharing the exact `device_id`, `addr1` region, or `customer_id`.
3. **Relevance Fusion**: Graph-adjacent cases receive a **+0.15 priority boost**. If a case matches both semantically and shares graph topology, it is prioritized at the top of retrieved context.

---

## 8. Case Memory — Cleared Cases as Legitimacy Evidence

A critical flaw in standard fraud systems is that memory only stores fraud. If an investigator only retrieves prior fraud, every alert looks suspicious.

In Sentinel:
- All 900 historical **cleared cases** (`outcome='cleared'`, `pattern='none'`) are embedded and indexed.
- When an alert resembles normal activity (e.g., recurring subscriptions, expected business travel), the retriever interleaves cleared cases into the top-$k$ results.
- In `HHG-003`, historical cleared cases `CC-4922` and `CC-4718` proved that recurring disputes on this merchant category were routinely cleared as legitimate cardholder billing confusion, preventing a false-positive card block.

---

## 9. Agent State Machine & Stopping Rule §6

The agent advances through 8 discrete states:
1. `TRIGGER` $\to$ 2. `INVESTIGATE` $\to$ 3. `GATHER_EVIDENCE` $\to$ 4. `ASSESS_UNCERTAINTY` $\to$ 5. `GATHER_MORE_EVIDENCE` $\to$ 6. `REASSESS` $\to$ 7. `RECOMMEND_ACTION` $\to$ 8. `UPDATE_CASE_MEMORY`.

### Stopping Rule (§6):
To prevent endless loops and reduce API overhead, the agent terminates investigation when:
- Fraud probability reaches $\ge 0.85$ or $\le 0.15$ supported by $\ge 2$ independent pieces of evidence.
- A simulated customer or auth verification response settles the dispute.
- Further graph traversals are mathematically guaranteed not to alter the policy action.

---

## 10. Policy Engine — R1–R10 and Hard Constraints

The policy engine is written in **100% deterministic Python**. The LLM is never permitted to select actions or choose approval routes.

### Authoritative Rules:
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

### Hard Constraints:
- `FILE_REPORT` is strictly route `L2`.
- `BLOCK_ALL_CARDS` is strictly route `L2`.
- `BLOCK_CARD` is route `L1` ($\le \$2,500$) or `L2` ($> \$2,500$).
- `CLOSE_NO_FRAUD` and `BLOCK_CARD` can never coexist in the same decision.

---

## 11. Additional Evidence Loop — Dynamic Evolution

Policy recommendations are dynamic:
1. **Initial Recommendation**: Formulated before customer contact. For instance, in `HHG-017`, initial actions were `VERIFY_WITH_CUSTOMER`, `MONITOR_CONNECTED_CARDS`, `CREATE_CASE`, and `FILE_REPORT`.
2. **Simulation**: The agent simulates customer validation based on detector findings. If an unfamiliar shared device was used, customer denial is assumed.
3. **Reassessment**: Upon receiving denial, `decide_after_evidence()` updates the actions to `BLOCK_CARD` (L1), preserving `MONITOR_CONNECTED_CARDS` and `FILE_REPORT`.
4. **Audit Trail**: The `what_changed` field explicitly explains how incoming evidence altered the bank's response.

---

## 12. Benchmark Results — 20/20 Exam Cases

The agent was evaluated across all 20 benchmark cases in `case_pack.csv`:

- **Execution Runtime**: 154.36 seconds total (average **7.72s per case**).
- **Validation Pass Rate**: **20/20 (100%)** zero schema or policy violations.
- **Verdict Distribution**:
  - **Fraud**: 12 cases (60%)
  - **Legitimate**: 7 cases (35%)
  - **Uncertain**: 1 case (`HHG-002`, 5%)
- **Regulatory Filings**: 12 SARs filed (100% accompanied by `FILE_REPORT` route `L2` and backed by multi-card ring evidence).
- **Total Fraud Exposure Identified**: **$4,679.81**.

---

## 13. What Worked Well

1. **Deterministic-LLM Separation**: Keeping policy execution in pure Python prevented LLM action hallucinations and guaranteed 100% compliance with approval hierarchies.
2. **Fast Local Fallback**: Combining pyTigerGraph with pre-indexed local CSV traversals enabled lightning-fast local testing without network throttling.
3. **Graph-Boosted Semantic Memory**: Adding +0.15 similarity to cases sharing physical device or region nodes completely eliminated irrelevant semantic false matches.

---

## 14. What Was Harder Than Expected

1. **Card ID Derivation**: Ensuring deterministic `customer_id` + `card2` ordering required sorting `NaN` values first (`K1`) before ascending floats (`K2`, `K3`). Any deviation caused silent key mismatches.
2. **Recurring Velocity Gaps**: High-spend cards had multiple authorizations per day, causing naive `.diff()` timestamp calculations to measure 24-hour gaps instead of 30-day billing intervals. Grouping by monthly representative transactions resolved this.
3. **Windows Console Encodings**: Default Windows `cp1252` encoding threw exceptions on Unicode checkmarks (`✓`), necessitating explicit UTF-8 stream reconfiguration.

---

## 15. Future Improvements

1. **Graph Neural Networks (GNNs)**: Train an inductive Graph Convolutional Network (GCN) directly on TigerGraph subgraphs to score node embeddings before LLM ingestion.
2. **Real-Time Stream Ingestion**: Connect TigerGraph Kafka Loader to ingest authorization streams live rather than in batch intervals.
3. **Interactive Human-in-the-Loop Review**: Allow Level 1 and Level 2 fraud managers to approve or reject recommendations directly through the Streamlit cockpit.

---

## LinkedIn Post

Building autonomous AI agents for fraud investigation is impossible with raw LLM prompts alone—real-world compliance demands deterministic policy guardrails and multi-hop graph topology. We built SENTINEL on @TigerGraphDB, combining deterministic detectors, GraphRAG case memory, and Groq LLaMA 3.3 to autonomously investigate 590,000+ IEEE-CIS transactions with 100% policy compliance across all 20 benchmark cases. Graph traversals turned multi-card compromise rings into instant sub-second evidence! #TigerGraph #GraphRAG #AI #FraudDetection #AgenticAI
