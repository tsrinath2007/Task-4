# SENTINEL — Official Hackathon Social Media Post & Announcement
## Team GOA-T | TigerGraph Agentic Fraud Investigation Hackathon

This document provides ready-to-publish social media announcements for **X (Twitter)** and **LinkedIn**, fully formatted and tagged with `@TigerGraphDB` as required by the hackathon submission guidelines.

---

## 📱 Option 1: LinkedIn Post (Recommended for Primary Submission)

**Copy and paste the following text into LinkedIn:**

```text
🚀 Excited to announce our submission for the TigerGraph Agentic Fraud Investigation Hackathon: SENTINEL — an autonomous, graph-native fraud investigation cockpit powered by @TigerGraphDB, GraphRAG, and LLaMA 3.3!

In banking, fraud analysts face thousands of alerts daily. Distinguishing between genuine customer activity and organized fraud rings requires traversing complex multi-hop networks under strict regulatory and policy deadlines.

Our team, GOA-T, built SENTINEL to bridge the gap between fast graph traversal and defensible autonomous action:

🔹 Graph Traversal at Scale: Running on 590,000+ IEEE-CIS/Vesta transactions and 5,565 historical closed cases, SENTINEL uses TigerGraph GSQL to trace cardholder histories, shared digital device profiles, and multi-card syndicates in sub-second latency.
🔹 Hybrid GraphRAG Memory: Dense 384-d semantic embeddings combined with topological graph adjacency (+0.15 boost). Uniquely, we indexed 900 cleared cases as negative evidence to actively protect legitimate cardholders from false-positive blocks.
🔹 Deterministic Policy Engine (R1–R10): We separated deterministic policy enforcement from probabilistic LLM synthesis. Action selection (AUTO, L1 Lead, L2 Manager) and FinCEN SAR filings are 100% hard-coded in Python to prevent LLM hallucinations.
🔹 Dynamic Next-Best Action: The agent formulates pre-evidence actions, simulates out-of-band verification, and updates post-evidence recommendations with full audit explanations.
🔹 Evaluated on 20 Ground-Truth Benchmark Cases: 20/20 cases PASSED with 0 schema or policy errors, achieving 12 Fraud, 7 Legitimate, and 1 Escalated verdict with an average latency of 7.7 seconds per case.

👥 Team GOA-T:
• Thota Sai Eswar Srinath (Team Leader)
• Nikhil Kadiri
• Bondugula Pranav Teja

🔗 Live Interactive Dashboard: https://task-4-nvan.onrender.com/
💻 GitHub Repository: https://github.com/tsrinath2007/Task-4
📖 Technical Blog: https://github.com/tsrinath2007/Task-4/blob/main/docs/TECHNICAL_BLOG.md

Huge thanks to @TigerGraphDB and Devanshu for hosting an incredible agentic challenge!

#TigerGraph #GraphRAG #AI #FraudDetection #AgenticAI #MachineLearning #FinTech #OpenSource
```

---

## 🐦 Option 2: X (Twitter) Thread

**Tweet 1 (Main Announcement):**
```text
Excited to unveil SENTINEL for the @TigerGraphDB Agentic Fraud Investigation Hackathon! 🛡️⚡

An autonomous, policy-governed fraud investigation cockpit powered by TigerGraph, GraphRAG, & LLaMA 3.3 across 590K+ IEEE-CIS transactions.

Validation: 20/20 PASSED! 🧵👇
```

**Tweet 2 (Graph & Architecture):**
```text
2/ Finding multi-card fraud rings in relational SQL requires slow recursive joins. 

With @TigerGraphDB GSQL, SENTINEL traverses:
Transaction ➔ DeviceProfile ➔ Connected Cards ➔ Prior Closed Cases in sub-seconds across 590,000+ records! 🕸️⚡
```

**Tweet 3 (GraphRAG & Policy Engine):**
```text
3/ Innovation highlights:
🧠 GraphRAG: 384-d dense embeddings + topological graph adjacency boost (+0.15)
🛡️ Policy Engine: Pure deterministic Python rules (R1–R10) with AUTO / L1 / L2 approval routing
📝 FinCEN SAR: Automatic regulatory filing for multi-card syndicates
```

**Tweet 4 (Next Best Action & Results):**
```text
4/ Evaluated on all 20 exam benchmark cases (HHG-001 to HHG-020):
✅ 20/20 Validation PASS
⚖️ Calibrated: 12 Fraud, 7 Legitimate, 1 Uncertain
⏱️ 7.7s avg latency per case
🔒 Pre-evidence ➔ Post-evidence action progression with full audit trails
```

**Tweet 5 (Links & Team GOA-T):**
```text
5/ Built with pride by Team GOA-T:
• Thota Sai Eswar Srinath (Lead)
• Nikhil Kadiri
• Bondugula Pranav Teja

🌐 Live Cockpit: https://task-4-nvan.onrender.com/
📂 Code & Docs: https://github.com/tsrinath2007/Task-4

Thank you @TigerGraphDB! #GraphDatabase #AI #AgenticAI
```

---

## 📸 Recommended Media to Attach:
1. **Screenshot of SENTINEL Analyst Cockpit**: Showing Case `HHG-014` with the live SVG TigerGraph traversal diagram, donut chart, and SAR report.
2. **Screenshot of Validation Output**: Showing `python scripts/validate_answers.py` displaying `20/20 PASSED, 0/20 FAILED`.
3. **Team GOA-T Modal Screenshot**: Showing the Team GOA-T roster modal.
