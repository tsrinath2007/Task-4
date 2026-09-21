# SENTINEL: Autonomous Fraud Investigation Agent with TigerGraph & GraphRAG

[![TigerGraph](https://img.shields.io/badge/TigerGraph-Savanna%20%7C%203.x%20%7C%204.x-FF6A00?logo=tigergraph&logoColor=white)](https://www.tigergraph.com/)
[![GraphRAG](https://img.shields.io/badge/Memory-GraphRAG%20384d-3B82F6)](https://github.com/microsoft/graphrag)
[![Groq LLaMA 3.3](https://img.shields.io/badge/LLM-Groq%20LLaMA%203.3%2070B-F55036)](https://groq.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An autonomous, evidence-driven, policy-governed fraud investigation cockpit powered by **TigerGraph**, **GraphRAG**, 8 deterministic detectors, a deterministic policy engine (R1–R10), and Groq LLaMA 3.3 70B synthesis.

Tested on **590,742 IEEE-CIS / Vesta transactions**, **5,565 closed historical cases**, and validated across **20 end-to-end benchmark exam cases (`HHG-001` to `HHG-020`)** with zero human intervention.

---

## 🏛️ System Architecture

```
                       +-----------------------------------+
                       |           ALERT TRIGGER           |
                       | (Risk Score / Dispute / Escalation)
                       +-----------------+-----------------+
                                         |
                                         v
                       +-----------------------------------+
                       |      TIGERGRAPH MCP TRAVERSAL     |
                       | - Card History   - Shared Devices |
                       | - Customer Cards - Prior Cases    |
                       +-----------------+-----------------+
                                         |
                                         v
   +-------------------------------------+-------------------------------------+
   |                                                                           |
   v                                                                           v
+-----------------------------+                             +-----------------------------+
|    DETERMINISTIC DETECTORS  |                             |       GRAPHRAG MEMORY       |
| - Card Testing Scan         |                             | - 384-d Dense Embeddings    |
| - Shared Device Ring Scan   |                             | - 5,565 Closed Cases        |
| - New Device & CNP Burst    |                             | - Graph Adjacency (+0.15)   |
| - Out-of-Region & ATO       |                             | - Top-5 Semantic Retrieval  |
| - Recurring Merchant Scan   |                             +--------------+--------------+
| - Legitimacy Checklist (9)  |                                            |
+--------------+--------------+                                            |
               |                                                           |
               +-----------------------------+-----------------------------+
                                             |
                                             v
                       +-----------------------------------+
                       |    DETERMINISTIC POLICY ENGINE    |
                       | - Rules R1 to R10 Coded Logic     |
                       | - Pre-Evidence Action Gating      |
                       | - Strict Routing (AUTO, L1, L2)   |
                       | - FinCEN SAR Filing Mandate       |
                       +-----------------+-----------------+
                                             |
                                             v
                       +-----------------------------------+
                       |     GROQ LLaMA 3.3 70B ADAPTER    |
                       | - Adjudication Synthesis          |
                       | - Action Policy Justification     |
                       | - FinCEN Form 111 SAR Narrative   |
                       +-----------------+-----------------+
                                             |
                                             v
                       +-----------------------------------+
                       |      TIGERGRAPH RUNTIME WRITE     |
                       | Writes Case vertex & links to txns|
                       +-----------------------------------+
```

---

## 📊 Benchmark Exam Results (20/20 Cases)

The agent was evaluated on 20 ground-truth exam cases (`HHG-001` through `HHG-020`):

| Metric | Result | Description |
| :--- | :--- | :--- |
| **Total Cases** | `20 / 20` | All cases executed and validated without human intervention |
| **Validation Score** | `20 / 20 PASS` | 0 schema, policy, or consistency errors (`scripts/validate_answers.py`) |
| **Verdict Calibration** | `12 Fraud, 7 Legitimate, 1 Uncertain` | Balanced decision boundary with zero bias |
| **SAR Regulatory Filings** | `12 Filed (100% Route L2)` | Strict FinCEN adherence (all multi-card rings or >$1,000 exposure) |
| **Total Exposure Handled** | `$4,679.81` | Quantified across all compromised accounts |
| **Total Runtime** | `154.36 s` | **7.72s average per case** end-to-end (traversal, detectors, memory, LLM) |

Full generated answer files are in [`cases/generated/HHG-001.json`](cases/generated/) through [`cases/generated/HHG-020.json`](cases/generated/).

---

## 🖥️ Local Analyst Cockpit

A fast local web application with **zero npm dependencies, zero React, and no build step**:

- **Inline SVG TigerGraph Traversal Diagram**: Live visualization of Focal Card $\to$ Device Profile $\to$ Connected Cards (Fraud/Clear) $\to$ Prior Cases.
- **Expanded FinCEN SAR Panel**: Full narrative, subjects, date ranges, and Route L2 approval badges.
- **Evidence Chain & Policy Progression**: Pre-evidence vs. post-evidence action evolution with `AUTO`, `L1`, and `L2` route chips.
- **Agent Audit Trace**: Tool execution latencies, token consumption, and Stopping Rule §6 metrics.

### Quick Start

1. **Install requirements**:
   ```bash
   pip install fastapi uvicorn pandas sentence-transformers groq python-dotenv
   ```

2. **Start the Sentinel Backend**:
   ```bash
   uvicorn sentinel_backend:app --port 8000 --reload
   ```

3. **Open the Cockpit**:
   Double click [`ui/sentinel_dashboard.html`](ui/sentinel_dashboard.html) or run:
   ```powershell
   Start-Process "ui/sentinel_dashboard.html"
   ```

---

## 📁 Repository Structure

```
.
├── cases/
│   └── generated/             # 20 validated JSON answer files & benchmark summary
├── data/
│   ├── raw/
│   │   ├── case_pack.csv      # 20 exam alert triggers
│   │   └── closed_cases_history.csv
│   └── processed/             # Graph schema vertices & edges (v_*.csv, e_*.csv)
├── docs/
│   └── TECHNICAL_BLOG.md      # Comprehensive 15-section technical blog post
├── scripts/
│   ├── run_benchmark.py       # Full benchmark runner across all 20 cases
│   ├── validate_answers.py    # Official answer schema & policy validator
│   ├── verify_tigergraph.py   # TigerGraph connection and schema verification
│   └── embed_cases.py         # GraphRAG 384-d embedding generator
├── src/
│   ├── agent/                 # Orchestrator, context, schemas, LLM adapter
│   ├── detectors/             # 8 deterministic fraud detectors & legitimacy checklist
│   ├── graph/                 # TigerGraph MCP client & GSQL query wrappers
│   ├── memory/                # GraphRAG hybrid vector & adjacency retriever
│   └── policy/                # Deterministic rules engine (R1 to R10)
├── tigergraph/
│   ├── schema/                # schema.gsql & schema documentation
│   ├── queries/               # Real-time GSQL graph queries
│   └── load/                  # TigerGraph CSV loading jobs
├── sentinel_backend.py        # FastAPI server for the analyst cockpit
└── ui/
    └── sentinel_dashboard.html # Self-contained analyst dashboard UI
```

---

## 📖 In-Depth Technical Blog

For complete details on the GSQL schema, graph traversal algorithms, deterministic policy rules (R1–R10), GraphRAG embedding methodology, and stopping criteria, read the [Technical Blog](docs/TECHNICAL_BLOG.md).
