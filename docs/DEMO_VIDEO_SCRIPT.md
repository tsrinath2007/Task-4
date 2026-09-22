# SENTINEL — Official 3-Member Demo Video Screenplay & Script
## TigerGraph Agentic Fraud Investigation Hackathon
🏆 **Team:** **GOA-T** 🐐  
⏱️ **Target Duration:** **4:30 – 4:45 minutes** *(Strictly within the hackathon's 3–5 min requirement)*  
👥 **Cast & Speaking Roles:**
1. 👑 **Speaker 1: Thota Sai Eswar Srinath** *(Team Leader & System Architecture)*
2. ⚡ **Speaker 2: Nikhil Kadiri** *(Graph Traversal & TigerGraph Engineering)*
3. 🧠 **Speaker 3: Bondugula Pranav Teja** *(Policy Engine, GraphRAG & Benchmark)*

---

## 🎬 Setup & Screen Checklist Before Recording
1. **Browser Tab 1:** Open [https://task-4-nvan.onrender.com/](https://task-4-nvan.onrender.com/) (or local `index.html`). Have it showing the **Security Gateway** / login modal.
2. **Terminal Window:** Prepared in the project directory, ready to type/run:
   ```powershell
   python scripts/validate_answers.py
   ```
3. **Microphone Check:** Ensure all 3 members have clear audio levels.
4. **Smooth Transitions:** Notice the handoff lines between Srinath $\to$ Nikhil $\to$ Pranav $\to$ Srinath.

---

## 🕒 Minute-by-Minute Screenplay & Spoken Dialogue

---

### ⏱️ [0:00 – 1:15] SEGMENT 1: Introduction & Architecture
**Speaker:** 👑 **Thota Sai Eswar Srinath (Team Leader)**  
**Screen Setup:** Browser on `index.html` showing the Sentinel Security Gateway.

* **On-Screen Actions:**
  1. Click the glowing shield or **Team GOA-T** banner to open the Team Modal showing **Thota Sai Eswar Srinath (Lead)**, **Nikhil Kadiri**, and **Bondugula Pranav Teja**.
  2. Click **"Enter Sentinel Cockpit"** to authenticate and load the main dashboard.
  3. Briefly point out the **Global Risk Monitor** on the left sidebar and the **20 benchmark cases**.

* **Dialogue (Word-for-Word):**
  > *"Hello everyone! We are **Team GOA-T**—I’m **Thota Sai Eswar Srinath**, the Team Leader, and with me are my teammates **Nikhil Kadiri** and **Bondugula Pranav Teja**.
  >
  > Today, we are proud to present **SENTINEL**: an autonomous, graph-native fraud investigation cockpit built for the TigerGraph Agentic Fraud Investigation Hackathon.
  >
  > In tier-1 financial institutions, fraud teams are overwhelmed by hundreds of thousands of transaction alerts every single day. A high risk score from a machine learning model is only an alert—it is never a definitive verdict. Distinguishing between genuine customer activity and coordinated fraud syndicates requires multi-hop network traversal, strict policy adherence, and defensible regulatory reporting.
  >
  > We built SENTINEL to bridge this gap. Evaluated across **590,000+ IEEE-CIS transactions** and **5,565 historical closed cases**, our agent operates on an 8-stage state machine that unifies TigerGraph's GSQL graph traversal, hybrid GraphRAG memory, and a deterministic policy engine.
  >
  > Now, I’ll hand it over to **Nikhil** to walk you through our graph architecture and how TigerGraph uncovers multi-card fraud rings."*

---

### ⏱️ [1:15 – 2:30] SEGMENT 2: TigerGraph GSQL & Multi-Hop Fraud Syndicates
**Speaker:** ⚡ **Nikhil Kadiri (Graph Traversal & Systems Lead)**  
**Screen Setup:** Click and select **HHG-014** from the sidebar.

* **On-Screen Actions:**
  1. Click **HHG-014** on the left case list.
  2. Point your cursor to the top metric cards: **Fraud Probability (92%)**, **Exposure ($3,450)**, **SAR Filed (YES)**.
  3. Scroll down and hover over the **Inline SVG TigerGraph Traversal Path** diagram in the center of the screen.
  4. Point to the **Focal Card (`C13487-K1`)** $\to$ **Device Profile (`D005668`)** $\to$ **51 Connected Cards**.
  5. Click on one of the connected cards or the device to show the interactive **Node Inspector**.

* **Dialogue (Word-for-Word):**
  > *"Thanks, Srinath! I’m **Nikhil Kadiri**, and I led our TigerGraph schema design and GSQL graph traversals.
  >
  > Take a look at benchmark case **HHG-014**, triggered on card account C13487-K1. The agent scored a **92% fraud probability**.
  >
  > In a traditional relational SQL database, detecting an organized fraud ring requires slow, recursive self-joins across millions of rows where the connection depth is unknown. In TigerGraph, we execute a 3-hop traversal in sub-second latency:
  >
  > Following the graph path: our focal card connects via a `MADE` edge to the transaction, which links via `FROM_DEVICE` to device profile `D005668`. From there, TigerGraph traverses the `USED_ON` reverse edge to discover that this single hardware profile was shared across **51 distinct card accounts**.
  >
  > Furthermore, our GSQL query traverses the `HAS_CLOSED_CASE` edge into historical memory, identifying that this device is a known syndicate hub tied to prior confirmed fraud cases. By clicking any node, our **Node Inspector** displays its degree centrality and graph risk evaluation instantly.
  >
  > Next, my teammate **Pranav** will show how our policy engine turns this graph evidence into dynamic next-best actions and regulatory SAR filings."*

---

### ⏱️ [2:30 – 3:45] SEGMENT 3: Dynamic Next-Best Action, GraphRAG & Benchmark Proof
**Speaker:** 🧠 **Bondugula Pranav Teja (Policy Engine & GraphRAG Lead)**  
**Screen Setup:** Scroll to the **Actions & Evidence Grid** for HHG-014, then switch to **HHG-008**, and finally open the Terminal.

* **On-Screen Actions:**
  1. In **HHG-014**, point to the **Actions Grid**: Show **Initial Actions** (`VERIFY_WITH_CUSTOMER`), then point to the blue **"What Changed"** callout box, and show **Final Actions** (`BLOCK_CARD` [L2], `FILE_REPORT` [L2]).
  2. Point to the **FinCEN Form 111 SAR Panel** on the right side and click **"Copy Narrative"**.
  3. Click **HHG-008** from the sidebar (or click the `Clear` filter tab) to show a **Legitimate Case** (Fraud Prob: 8%, `CLOSE_NO_FRAUD`).
  4. Switch to the **Terminal Window** and run:
     ```powershell
     python scripts/validate_answers.py
     ```
  5. Watch the test pass **20/20 with 0 errors**.

* **Dialogue (Word-for-Word):**
  > *"Thanks, Nikhil! I’m **Bondugula Pranav Teja**, and I focused on the deterministic policy engine, GraphRAG memory, and next-best actions.
  >
  > A core requirement of this challenge is recommending the **Next-Best Action** when signals are uncertain. Look at how SENTINEL evolves its decisions:
  >
  > Under Bank Policy Rules R1 and R6, **before additional evidence was received**, the agent recommended initial actions: verifying with the customer and monitoring connected cards, while strictly forbidding premature account blocking.
  >
  > Once out-of-band customer verification confirmed that the charge was unauthorized, the policy engine updated the decision to **Final Actions**: escalating to block the card and filing a federal report under strict **Level 2 manager approval**. The **What Changed** audit banner explicitly explains this evidentiary shift.
  >
  > Notice also our **FinCEN Form 111 SAR panel**—it automatically compiles regulatory narratives with subject IDs, dates, and amounts.
  >
  > Equally important is preventing false positives: on case **HHG-008**, an alert fired on an out-of-region subscription. Naive systems block the card. But our **GraphRAG memory** retrieved historical cleared cases, recognizing a legitimate 30-day billing cadence. Under Rule R7, SENTINEL cleared the case with `CLOSE_NO_FRAUD`, preserving customer trust!
  >
  > Finally, let's verify our system integrity: here in the terminal, we execute `validate_answers.py` across all 20 benchmark exam cases. As you can see: **20 out of 20 cases PASS with zero errors!**
  >
  > Back to Srinath for our conclusion."*

---

### ⏱️ [3:45 – 4:30] SEGMENT 4: Conclusion & Wrap-Up
**Speaker:** 👑 **Thota Sai Eswar Srinath (Team Leader)**  
**Screen Setup:** Switch back to the Browser, show the **AI Copilot drawer** (ask a question or click a suggestion chip), and click **Lock Cockpit**.

* **On-Screen Actions:**
  1. Click the floating **AI Copilot** button in the bottom-right corner.
  2. Click the quick suggestion chip: *"Why was this case flagged as fraud?"* and show the instant grounded response.
  3. Click **[ 🔒 Lock ]** in the top navigation bar to lock the session back to the Security Gateway.

* **Dialogue (Word-for-Word):**
  > *"Thanks, Pranav!
  >
  > Analysts can also collaborate in real-time with our grounded **SENTINEL AI Copilot**, which answers questions about graph traversal paths, evidence chains, and policy rules directly from our TigerGraph knowledge graph.
  >
  > In conclusion, by combining:
  > 1. **TigerGraph's high-speed graph traversals**,
  > 2. **GraphRAG hybrid memory with cleared-case negative evidence**,
  > 3. **A 100% deterministic Python policy engine**, and
  > 4. **Groq LLaMA 3.3 explanation synthesis**,
  >
  > SENTINEL delivers a scalable, explainable, and policy-compliant fraud investigation solution.
  >
  > Our live cockpit is running on Render, and our complete source code, GSQL schemas, and technical blog are open-source on GitHub.
  >
  > On behalf of **Team GOA-T**—Thota Sai Eswar Srinath, Nikhil Kadiri, and Bondugula Pranav Teja—thank you to the TigerGraph team for hosting this incredible hackathon!"*

---

## 🎯 Quick Rehearsal Summary Table

| Time Range | Speaker | Main Topic | Key Visual on Screen |
| :--- | :--- | :--- | :--- |
| **0:00 – 1:15** | **Srinath** *(Team Leader)* | Intro, Team GOA-T, Problem, Cockpit Entry | Security Gateway $\to$ Team Modal $\to$ Dashboard |
| **1:15 – 2:30** | **Nikhil** *(Graph Lead)* | TigerGraph GSQL, 3-Hop Traversal, Fraud Ring | Case HHG-014, SVG Graph Traversal Diagram |
| **2:30 – 3:45** | **Pranav** *(Policy Lead)* | Next-Best Action, GraphRAG, 20/20 Validation | Actions Grid (`what_changed`), HHG-008, Terminal Test |
| **3:45 – 4:30** | **Srinath** *(Team Leader)* | AI Copilot, Architecture Wrap-Up, Sign-off | Copilot Chat Drawer $\to$ Lock Cockpit |

**Total Duration:** **~4 minutes 30 seconds** (Exact sweet spot for the 3–5 min requirement!)
