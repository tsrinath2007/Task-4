# SENTINEL: Autonomous Graph-Native Fraud Investigation Cockpit

<div align="center">

[![TigerGraph](https://img.shields.io/badge/TigerGraph-Savanna%20%7C%203.x%20%7C%204.x-FF6A00?logo=tigergraph&logoColor=white)](https://www.tigergraph.com/)
[![GraphRAG](https://img.shields.io/badge/Memory-GraphRAG%20384d-3B82F6)](https://github.com/microsoft/graphrag)
[![Groq LLaMA 3.3](https://img.shields.io/badge/LLM-Groq%20LLaMA%203.3%2070B-F55036)](https://groq.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Validation](https://img.shields.io/badge/Benchmark-20%2F20%20PASS-brightgreen)](cases/generated/)
[![Live Cockpit](https://img.shields.io/badge/Live%20Cockpit-Render%20Online-blue)](https://task-4-nvan.onrender.com/)

**TigerGraph Agentic Fraud Investigation Hackathon 2026**  
🏆 **Team Name:** **GOA-T** 🐐

| Team Member | Role |
| :--- | :--- |
| **Thota Sai Eswar Srinath** | Team Leader & Agentic Architecture |
| **Nikhil Kadiri** | Graph Systems & TigerGraph Traversal Engineering |
| **Bondugula Pranav Teja** | Policy Engine & GraphRAG Implementation |

</div>

---

## 🌟 Overview

**SENTINEL** is an evidence-driven, policy-governed autonomous fraud investigation agent and interactive cockpit powered by **TigerGraph GSQL**, **GraphRAG hybrid memory**, 8 deterministic detectors, an authoritative policy engine (Rules R1–R10), and Groq LLaMA 3.3 70B synthesis.

Evaluated on **590,742 IEEE-CIS / Vesta transactions**, **5,565 historical closed cases**, and validated across **20 end-to-end benchmark exam cases (`HHG-001` to `HHG-020`)** with zero human intervention.

- 🌐 **Live Web Cockpit:** [https://task-4-nvan.onrender.com/](https://task-4-nvan.onrender.com/)
- 🎬 **YouTube Demo Video:** [https://youtu.be/AC_xRYlQJq8?si=f060H50EcGp2EQSc](https://youtu.be/AC_xRYlQJq8?si=f060H50EcGp2EQSc)
- 📝 **Technical Blog (Dev.to):** [https://dev.to/tsrinath/tigergraph-agentic-fraud-investigation-hackathon-2026team-goa-t-4chl](https://dev.to/tsrinath/tigergraph-agentic-fraud-investigation-hackathon-2026team-goa-t-4chl)
- 🐦 **Official Announcement on X (Twitter):** [https://x.com/_tsrinath_/status/2103362303173550123?s=20](https://x.com/_tsrinath_/status/2103362303173550123?s=20)
- 📊 **Comprehensive 20-Case Benchmark Report:** [docs/BENCHMARK_REPORT.md](docs/BENCHMARK_REPORT.md)
- 📖 **Local Technical Blog Markdown:** [docs/TECHNICAL_BLOG.md](docs/TECHNICAL_BLOG.md)
- 🎬 **Demo Video Screenplay:** [docs/DEMO_VIDEO_SCRIPT.md](docs/DEMO_VIDEO_SCRIPT.md)
- 📁 **20 Ground-Truth Answer JSON Files:** [cases/generated/](cases/generated/)

---

## ⚡ Why TigerGraph

Traditional financial crime systems rely on relational databases or flat feature stores that examine transactions as isolated events. In real-world fraud syndicates, compromise signals only emerge when traversing relationships across entities.

### Relational Multi-Join Failure vs. TigerGraph Native Pointer-Chasing

To discover a shared device ring across accounts in a relational database, the system must execute:

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

- **Why Relational Fails**: Joining 3 high-volume tables (`transactions`, `devices`, `cards`) across millions of records requires scanning massive secondary indexes and materializing large temporary tables. Under high transaction volume, running multi-hop relational joins triggers table locks, query timeouts (>5s), or forces financial institutions to rely on stale overnight batch jobs.
- **The TigerGraph Advantage**: TigerGraph represents graph edges as direct physical in-memory memory pointers. Executing a 4-hop traversal (`Transaction -> Card -> DeviceProfile -> Connected Cards -> Customers`) runs in **<15 milliseconds**, scaling with local node degree $O(d)$ rather than database size $O(N)$.

### Concrete Multi-Hop Traversals Implemented in SENTINEL

1. **Shared Hardware Ring Expansion (`query_shared_devices`)**:
   - `Transaction -(PAID_WITH)-> Card -(USED_DEVICE)-> DeviceProfile -(USED_DEVICE_REVERSE)-> Card -(ISSUED_TO)-> Customer`
   - *Benchmark Impact*: In case `HHG-014`, single-hop lookup sees only card `C13487-K1`. TigerGraph's 4-hop traversal uncovered **51 additional linked cards** operating from the same hardware signature (`D005668`), immediately escalating the decision to ring containment (`MONITOR_CONNECTED_CARDS`).
2. **Temporal Card Velocity & Micro-Testing Traversal (`query_card_history`)**:
   - Traverses chronological transaction edges on a card vertex within a 2-hour window. Detects low-dollar sequential authorization spikes typical of automated card-testing bots (e.g. `HHG-004`, `HHG-006`, `HHG-017`).
3. **Recurring Merchant Historical Scan (`recurring_merchant_scan`)**:
   - Traverses temporal card-to-merchant transaction edges looking for periodic 28–34 day billing intervals.
   - *Benchmark Impact*: Safely overrules false alarms on high ML risk alerts (e.g. `HHG-001`, `HHG-008`, `HHG-012`, `HHG-018`), confirming regular subscriptions and preventing wrongful card blocks.

---

## 🏛️ System Architecture

SENTINEL operates as an 8-stage calibrated agent pipeline:

```
[ TRIGGER ]
Alert Received: Real-time ML Risk Score | Customer Dispute | Analyst Request
      │
      ▼
[ TIGERGRAPH TRAVERSAL ]
Native Pointer-Chasing: Card Portfolio ➔ Device Profiles ➔ Connected Cards ➔ Prior Cases
      │
      ▼
[ 8 DETERMINISTIC DETECTORS ]
Card Testing | Shared Device Ring | CNP Burst | Out-of-Region | ATO | Recurring Scan
      │
      ▼
[ GRAPHRAG CASE MEMORY ]
Topological Adjacency Boost (+0.15) + 384-d Dense Semantic Vector Retrieval (5,565 Precedents)
      │
      ▼
[ LLM ADJUDICATION ]
Groq LLaMA 3.3 70B: Contextual Evidence Synthesis & Hypothesis Calibration
      │
      ▼
[ EVIDENCE REQUEST ]
Dynamic Customer/Channel Verification Loop (Simulated Interactive Challenge)
      │
      ▼
[ POLICY ENFORCEMENT ]
Deterministic Rules R1–R10: Pre-evidence Gating & Strict Route Assignment (AUTO, L1, L2)
      │
      ▼
[ SAR GENERATION & GRAPH WRITE-BACK ]
FinCEN Form 111 XML/Narrative Generation + TigerGraph Runtime `Case` Vertex Insertion
```

---

## 📊 Benchmark Results

Full case-by-case data and topological analysis: 📄 **[docs/BENCHMARK_REPORT.md](docs/BENCHMARK_REPORT.md)**.

### Aggregate Performance Across 20 Exam Cases

| Metric | Value | Audit Verification |
| :--- | :---: | :--- |
| **Total Cases Executed** | **20** | Ground-truth IEEE-CIS / Vesta test pack (`HHG-001` to `HHG-020`) |
| **Validation Score** | **20 / 20 PASS** | 0 schema, policy, or constraint errors (`scripts/validate_answers.py`) |
| **Fraud Verdicts** | **12** | Calibrated high-confidence fraud detection |
| **Legitimate Verdicts** | **7** | False positives successfully cleared via recurring graph analysis |
| **Uncertain Verdicts** | **1** | Escalated to analyst review under Rule R8 |
| **FinCEN SARs Filed** | **12** | 100% compliant with FinCEN 31 CFR §1020.320 and Route L2 approval |
| **Evidence Requests** | **20** | Interactive corroboration evaluated on every case |
| **Cases where Initial ≠ Final Action** | **20** | 100% dynamic policy adjustment between hypothesis and post-validation |
| **Avg P(Fraud) — Fraud Cases** | **93.3%** | Clear, decisive separation from borderline noise |
| **Avg P(Fraud) — Legit Cases** | **7.3%** | Pristine false positive suppression |
| **Total Exposure Identified** | **$5,174.77** | Quantified financial exposure protected |
| **Avg Tool Calls Per Case** | **7.0** | Systematic multi-step investigation protocol |

---

## 🖥️ Interactive Analyst Cockpit

SENTINEL includes an analyst cockpit designed for fraud intelligence units:

- **Live Deployment:** [https://task-4-nvan.onrender.com/](https://task-4-nvan.onrender.com/)
- **Panel 1: Confidence Evolution Chart:** Visual SVG line chart plotting calibrated fraud probability across all 7 investigation stages (Trigger $\to$ Graph $\to$ Detectors $\to$ Memory $\to$ LLM $\to$ Evidence $\to$ Final) with hover tooltips displaying stage reasons.
- **Panel 2: Investigation Timeline:** Chronological vertical rail logging every milestone event, timestamp, color-coded state badge (`TRIGGER`, `INVESTIGATE`, `ADJUDICATE`, `ENFORCE`, `CLOSED`), tool badge, and summary.
- **Panel 3: Memory Impact:** Live endpoint integration showing precedent cases retrieved, confidence before vs. after memory, direction arrow, precedent breakdown table, and prominent `MEMORY CHANGED THIS DECISION` alert.
- **Panel 4: TigerGraph Traversal Path:** Visual hop-by-hop chain (`Transaction -> Card -> Device -> Connected Cards -> Customer`), entity discovery counters, compiled executable GSQL query block with copy button, and "Why TigerGraph" callout box.
- **FinCEN SAR Compliance Export:** 1-click batch export for FinCEN Form 111 XML (`/api/reports/sar_batch_xml`) and regulatory CSV audit log (`/api/reports/audit_log_csv`).
- **AI Copilot & Threat Watchlist:** Grounded interactive assistant and real-time watchlist management.

---

## 🚀 How to Run

Follow these instructions to replicate the benchmark results and run the system locally from scratch.

### 1. Prerequisites
- Python 3.10 or higher
- Git

### 2. Clone and Setup Environment
```bash
git clone https://github.com/tsrinath2007/Task-4.git
cd "Task-4 TigerGraph"

# Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure API Credentials (Optional for Live LLM)
Create a `.env` file in the repository root:
```env
GROQ_API_KEY=your_groq_api_key_here
TIGERGRAPH_HOST=http://127.0.0.1:9000
TIGERGRAPH_USERNAME=tigergraph
TIGERGRAPH_PASSWORD=tigergraph
```
*(Note: SENTINEL features complete deterministic offline fallback for all detectors, graph queries, and embeddings if external credentials are not configured).*

### 4. Build Dataset and GraphRAG Embeddings
```bash
# Prepare processed graph CSVs from raw data
python src/data/prep_data.py

# Generate 384-dimensional dense semantic embeddings for 5,565 closed cases
python scripts/embed_cases.py
```

### 5. Execute Full 20-Case Benchmark
```bash
# Run all 20 cases through the autonomous orchestrator
python scripts/run_benchmark.py

# Re-generate the official markdown benchmark report
python scripts/generate_benchmark_report.py

# Run the official answer validator
python scripts/validate_answers.py
```

### 6. Launch the Interactive Analyst Cockpit
```bash
# Start the FastAPI backend
python sentinel_backend.py
```
Open your browser and navigate to:
```
http://localhost:8000/
```
Or open `index.html` directly in any web browser.

---

## 📁 Repository Structure

```
.
├── cases/
│   └── generated/             # 20 validated JSON answer files & benchmark summary
├── data/
│   ├── raw/                   # Raw IEEE-CIS datasets (case_pack.csv, identity.csv)
│   └── processed/             # Graph schema vertices & edges (v_*.csv, e_*.csv)
├── docs/
│   ├── BENCHMARK_REPORT.md    # Official 20-case aggregate and per-case benchmark audit
│   ├── TECHNICAL_BLOG.md      # Comprehensive technical blog covering all rubric criteria
│   ├── DEMO_VIDEO_SCRIPT.md   # 5-minute video screenplay & team presentation script
│   ├── SOCIAL_POST.md         # Ready-to-publish social media announcements
│   ├── DATA_PROFILE.md        # Deep statistical profiling of 590K transactions
│   └── MCP_SETUP.md           # TigerGraph MCP installation & connection guide
├── scripts/
│   ├── run_benchmark.py       # Full benchmark runner across all 20 cases
│   ├── generate_benchmark_report.py # Benchmark report generator
│   ├── validate_answers.py    # Official answer schema & policy validator (20/20 PASS)
│   ├── verify_tigergraph.py   # TigerGraph connection and schema verification
│   └── embed_cases.py         # GraphRAG 384-d embedding generator
├── src/
│   ├── agent/                 # Orchestrator, context, schemas, Groq LLM adapter
│   ├── detectors/             # 8 deterministic fraud detectors & legitimacy checklist
│   ├── graph/                 # TigerGraph MCP client & GSQL query wrappers
│   ├── memory/                # GraphRAG hybrid vector & adjacency retriever
│   └── policy/                # Deterministic rules engine (R1 to R10)
├── tigergraph/
│   ├── schema/                # schema.gsql & schema documentation
│   ├── queries/               # Real-time GSQL graph queries (verification.gsql)
│   └── load/                  # TigerGraph CSV loading jobs
├── index.html                 # Production analyst cockpit (deployed on Render & local)
├── sentinel_backend.py        # FastAPI server for the analyst cockpit
├── render.yaml                # Render deployment configuration
└── requirements.txt           # Python dependencies
```

---

## 👥 Team GOA-T

- **Thota Sai Eswar Srinath (Team Leader)** — *Architecture, Orchestration, Agentic Design*
- **Nikhil Kadiri** — *TigerGraph Schema, GSQL Queries, Traversal Algorithms*
- **Bondugula Pranav Teja** — *Policy Engine (R1–R10), GraphRAG Hybrid Memory, Detectors*

*Built with ❤️ for the TigerGraph Agentic Fraud Investigation Hackathon 2026.*
