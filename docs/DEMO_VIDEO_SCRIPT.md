# SENTINEL — 3 to 5 Minute Demo Video Script & Screenplay

**Project**: SENTINEL — Autonomous Fraud Investigation Cockpit  
**Target Duration**: 3:30 to 4:30 minutes  
**Screen Setup**: 
- Browser window with [`ui/sentinel_dashboard.html`](file:///c:/Users/SES/OneDrive/Documents/GOA_T/Task-4%20TigerGraph/ui/sentinel_dashboard.html)
- Terminal window with FastAPI backend running and ready to run `python scripts/validate_answers.py`

---

## 🎬 Screenplay & Talking Points

### [0:00 – 0:40] Introduction & Security Gateway
* **On Screen**: Browser open to `ui/sentinel_dashboard.html` displaying the **Sentinel Security Gateway** modal.
* **What to Do**:
  1. Show the glowing shield and Level-3 clearance badge.
  2. Type an incorrect passcode like `1234` and click **"Authorize & Enter Cockpit"** to show strict security rejection (`❌ Access Denied: Invalid Passcode`).
  3. Click **"One-Click Demo Access"** to enter the light-themed cockpit.
* **What to Say**:
  > *"Hello everyone! This is our submission for the TigerGraph Agentic Fraud Investigation Hackathon: **SENTINEL**—an autonomous, evidence-driven fraud investigation agent and cockpit.
  > In financial institutions, fraud teams face thousands of alerts daily. Distinguishing between genuine customer activity and organized fraud rings requires multi-hop graph traversal and strict policy adherence.
  > We've secured our cockpit with a dedicated security gateway enforcing Level-3 analyst credentials, cryptographic audit trails, and live graph enclave connectivity. Let's enter the cockpit."*

---

### [0:40 – 1:50] Fraud Investigation Deep Dive (Case `HHG-014` or `HHG-017`)
* **On Screen**: Select **HHG-014** from the sidebar. Click **[ ⛶ Fullscreen ]** to expand presentation mode.
* **What to Do**:
  1. Highlight the **Top Metrics**: Fraud Probability (`92%`), Flagged Exposure, Evidence Items (`8`), and SAR Filed (`YES`).
  2. Point to the **Donut Chart Gauge** in Fraud Analysis and the affected card chips.
  3. Walk through the **TigerGraph Traversal Path** SVG diagram:
     - Focal Card (`C13487-K1`) $\to$ Device Profile (`D005668`) $\to$ 51 Connected Cards in the syndicate.
  4. Point out the **Evidence Chain** horizontal stepper (numbered 1 through 4 with timestamps).
  5. Show the **Suspicious Activity Report (SAR)** panel and click **"Copy Narrative"**.
* **What to Say**:
  > *"Here is case **HHG-014**, triggered on card C13487-K1.
  > Notice the four real-time metric cards at the top. The agent scored a **92% fraud probability**.
  > Looking at the **TigerGraph Traversal Path**, our agent performed a multi-hop traversal from the focal card to its device profile D005668, uncovering that this device was shared across **51 distinct card accounts**. In relational SQL, finding this ring requires recursive, multi-table joins; in TigerGraph, it executes in sub-seconds.
  > Because the exposure and ring size exceed regulatory thresholds, the agent automatically compiled a complete **FinCEN Form 111 Suspicious Activity Report (SAR)** with full narrative, subject identifiers, and mandated Level 2 manager review."*

---

### [1:50 – 2:45] Dynamic Next-Best Action Progression
* **On Screen**: Scroll to the **Actions & Evidence Grid** (Initial Actions, Final Actions, What Changed).
* **What to Do**:
  1. Hover over the **Initial Actions** (`VERIFY_WITH_CUSTOMER` [AUTO], `MONITOR_CONNECTED_CARDS` [AUTO]).
  2. Point to the blue callout banner: **"What changed"**.
  3. Show the **Final Actions** (`BLOCK_CARD` [L1], `FILE_REPORT` [L2]).
* **What to Say**:
  > *"A core requirement of this hackathon is recommending the **Next-Best Action** when signals are uncertain.
  > Look at how our agent evolves its decisions:
  > **Before additional evidence was gathered**, under Rule R1 and R7, the agent recommended Initial Actions: verifying with the customer and placing connected cards under monitoring, while strictly preventing premature card blocking.
  > The agent then simulated an out-of-band customer verification request. Upon customer confirmation that the charge was unauthorized, the agent progressed the case to **Final Actions**: escalating to block the card under Route L1 and filing a regulatory report under Route L2.
  > The **What Changed** audit banner explains the exact evidentiary shift behind the policy change."*

---

### [2:45 – 3:35] Handling Legitimate & Disputed Charges (Case `HHG-008` / `HHG-009`)
* **On Screen**: Click **HHG-008** or **HHG-009** from the sidebar filter (click `Clear` filter tab).
* **What to Do**:
  1. Show that the verdict is **CLEARED / BASELINE** in green (`0% - 15%` fraud probability).
  2. Highlight that the transaction exposure ($77.07 or $30.02) is preserved.
  3. Show that SAR is marked **NOT REQUIRED** and actions state `CLOSE_NO_FRAUD` [AUTO].
* **What to Say**:
  > *"Now let's examine how SENTINEL prevents costly false positives.
  > On case **HHG-008**, an alert was triggered on an out-of-region transaction. Naive thresholding might block the card.
  > But SENTINEL ran our **Recurring Merchant and Historical Baseline Scans**, finding that this merchant matched the customer's legitimate 30-day billing cadence across prior cycles.
  > Following Bank Policy Rule R7, the agent cleared the case as legitimate, recommended `CLOSE_NO_FRAUD`, avoided filing an unnecessary SAR, and preserved cardholder trust."*

---

### [3:35 – 4:15] Benchmark Verification & Architecture Summary
* **On Screen**: Switch to the terminal and execute:
  ```powershell
  python scripts/validate_answers.py
  ```
* **What to Do**:
  1. Watch the validation test pass **20/20 with 0 errors**.
  2. Briefly show the `cases/generated/` folder.
* **What to Say**:
  > *"Every decision made by SENTINEL is rigorously validated.
  > Here in the terminal, we run our official validation script against all 20 ground-truth exam benchmark cases from `HHG-001` to `HHG-020`.
  > As you can see: **20 out of 20 cases PASS**, with 100% adherence to JSON schemas, policy rules R1 through R10, approval routes, and graph persistence.
  > Total execution across all 20 cases took just **154 seconds**—an average of 7.7 seconds per case."*

---

### [4:15 – 4:40] Conclusion & Wrap-Up
* **On Screen**: Switch back to the dashboard, click **[ 🔒 Lock ]** to return to the security gateway.
* **What to Say**:
  > *"By uniting TigerGraph's high-speed graph traversals, GraphRAG dense memory, deterministic policy guardrails, and LLaMA 3.3 reasoning, SENTINEL empowers financial institutions to stop fraud in seconds rather than days.
  > All source code, data pipelines, and answer files are open-source on GitHub. Thank you to the TigerGraph team for hosting this challenge!"*
