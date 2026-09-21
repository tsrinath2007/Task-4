# TigerGraph Schema Data Dictionary

**Graph Name**: `FraudInvestigationGraph`  
**Version**: 1.0  
**Target Platform**: TigerGraph Savanna / TigerGraph 3.x / 4.x  

---

## 1. Overview & Architectural Design

The `FraudInvestigationGraph` schema is designed to support real-time graph traversals, deterministic fraud detectors, GraphRAG retrieval, and agentic case synthesis. 

### Key Architectural Requirements Met:
1. **TigerGraph-Compatible Types**: All attributes use standard TigerGraph data types (`STRING`, `INT`, `DOUBLE`, `DATETIME`, `BOOL`).
2. **Stable STRING Primary Keys**: All primary IDs (`customer_id`, `card_id`, `TransactionID`, `device_id`, `case_id`, `addr1`, `email_domain`) are strings, preventing any precision loss or float-formatting anomalies.
3. **Runtime Writable Case Vertex**: A dedicated `Case` vertex allows the AI agent to write new investigation cases and link them to involved transactions and cards without mutating historical `ClosedCase` vertices.
4. **Bidirectional Traversals**: All directed edges define an explicit `WITH REVERSE_EDGE`, enabling $O(1)$ traversals in both directions across graph hops.

---

## 2. Vertex Data Dictionary

### 2.1 `Customer`
Represents an individual bank customer.
| Attribute | Type | Primary Key | Description |
|---|---|---|---|
| `customer_id` | STRING | Yes | Synthesized customer identifier (e.g. `C08623`, `C12382`). |

### 2.2 `Card`
Represents a payment card owned by a customer.
| Attribute | Type | Primary Key | Description |
|---|---|---|---|
| `card_id` | STRING | Yes | Derived card identifier (e.g. `C08623-K2`). Rule: NaN `card2` $\to$ K1, ascending numeric $\to$ K2, K3... |
| `customer_id` | STRING | No | Foreign key reference to owning customer. |

### 2.3 `Transaction`
Represents a financial transaction event.
| Attribute | Type | Primary Key | Description |
|---|---|---|---|
| `TransactionID` | STRING | Yes | Unique transaction identifier (e.g. `3530164`). |
| `card_id` | STRING | No | Card identifier that made the transaction. |
| `customer_id` | STRING | No | Customer identifier owning the card. |
| `ts` | DATETIME | No | Real timestamp (`YYYY-MM-DD HH:MM:SS`), July–Dec 2016. |
| `TransactionAmt` | DOUBLE | No | Transaction amount in USD. |
| `ProductCD` | STRING | No | Product code (`W` = in-person, `C`, `H`, `R`, `S` = online). |
| `addr1` | STRING | No | Billing region code (e.g. `444.0`). |
| `P_emaildomain` | STRING | No | Purchaser email domain (e.g. `gmail.com`). |
| `R_emaildomain` | STRING | No | Recipient email domain (e.g. `anonymous.info`). |
| `risk_score` | DOUBLE | No | Model-generated risk score (0.0–1.0). Input feature, not verdict. |
| `channel` | STRING | No | `online` or `in_person`. |
| `M1`–`M9` | STRING | No | Match flags (e.g. `T`, `F`, match status). |
| `id_15` | STRING | No | Device status from identity record (`New`, `Found`, or empty). |
| `id_23` | STRING | No | Proxy status from identity record (`IP_PROXY:ANONYMOUS`, etc.). |
| `device_id` | STRING | No | Foreign key reference to `DeviceProfile`. |
| `gap_min` | DOUBLE | No | Elapsed minutes since previous transaction on this card. |
| `prev_txn_id` | STRING | No | TransactionID of prior transaction on this card. |

### 2.4 `DeviceProfile`
Represents an environment fingerprint captured for online transactions.
| Attribute | Type | Primary Key | Description |
|---|---|---|---|
| `device_id` | STRING | Yes | Stable deterministic identifier (`D000001`–`D009706`). |
| `device_info` | STRING | No | Device model string (e.g. `SM-G935F Build/NRD90M`). |
| `device_os` | STRING | No | Operating system string (e.g. `Android 7.0`). |
| `device_browser` | STRING | No | Browser string (e.g. `chrome 62.0 for android`). |
| `device_screen` | STRING | No | Screen resolution string (e.g. `1920x1080`). |
| `device_type` | STRING | No | `mobile` or `desktop`. |

### 2.5 `BillingRegion`
Represents an anonymized geographical billing territory.
| Attribute | Type | Primary Key | Description |
|---|---|---|---|
| `addr1` | STRING | Yes | Billing region code string (e.g. `264.0`, `444.0`). |

### 2.6 `EmailDomain`
Represents an email domain entity.
| Attribute | Type | Primary Key | Description |
|---|---|---|---|
| `email_domain` | STRING | Yes | Domain string (e.g. `gmail.com`, `yahoo.com`). |

### 2.7 `ClosedCase`
Represents completed historical investigations (July–October 2016).
| Attribute | Type | Primary Key | Description |
|---|---|---|---|
| `case_id` | STRING | Yes | Unique closed case identifier (`CC-0001` to `CC-5565`). |
| `customer_id` | STRING | No | Target customer ID. |
| `card_id` | STRING | No | Target card ID. |
| `opened_at` | DATETIME | No | Case open timestamp. |
| `closed_at` | DATETIME | No | Case close timestamp. |
| `outcome` | STRING | No | `confirmed_fraud` (4,665 cases) or `cleared` (900 cases). |
| `pattern` | STRING | No | Fraud typology (`card_testing`, `out_of_region_use`, etc., or `none`). |
| `first_fraud_txn_id` | STRING | No | Starting fraudulent transaction (empty for cleared cases). |
| `txn_ids` | STRING | No | Pipe-separated list of all involved transactions. |
| `n_txns` | INT | No | Number of transactions involved. |
| `exposure_usd` | DOUBLE | No | Total financial exposure in USD. |
| `connected_card_ids` | STRING | No | Other compromised cards in the same incident. |
| `actions_taken` | STRING | No | Pipe-separated list of bank actions taken. |
| `report_filed` | STRING | No | Whether SAR was filed (`Yes` / `No`). |
| `analyst_notes` | STRING | No | Text narrative and rationale written by analyst. |

### 2.8 `Case`
Represents new investigations generated by the agent at runtime.
| Attribute | Type | Primary Key | Description |
|---|---|---|---|
| `case_id` | STRING | Yes | Benchmark case ID (e.g. `HHG-001` to `HHG-020`) or generated ID. |
| `status` | STRING | No | `open`, `closed_fraud`, `closed_legitimate`, `escalated`. |
| `verdict` | STRING | No | `fraud`, `legitimate`, `uncertain`. |
| `fraud_probability` | DOUBLE | No | Calibrated probability (0.0–1.0). |
| `pattern` | STRING | No | Identified pattern or `undocumented` / `none`. |
| `pattern_description` | STRING | No | Description for undocumented patterns. |
| `first_suspicious_txn_id` | STRING | No | Transaction where suspicious activity began. |
| `exposure_usd` | DOUBLE | No | Financial exposure in USD. |
| `summary` | STRING | No | Investigation summary. |
| `evidence_json` | STRING | No | Serialized evidence list stored as JSON string. |
| `actions_json` | STRING | No | Serialized next best actions stored as JSON string. |
| `sar_json` | STRING | No | Serialized SAR filing stored as JSON string. |
| `sar_filed` | BOOL | No | True if regulatory report filed. |
| `stop_reason` | STRING | No | Stopping rule rationale. |
| `created_at` | DATETIME | No | Runtime creation timestamp. |

---

## 3. Edge Data Dictionary

| Edge Name | Source Vertex | Target Vertex | Reverse Edge | Attributes | Description |
|---|---|---|---|---|---|
| `OWNS` | `Customer` | `Card` | `OWNED_BY` | None | Maps customer to cards they own. |
| `MADE` | `Card` | `Transaction` | `MADE_BY` | None | Maps card to transactions it performed. |
| `NEXT` | `Transaction` | `Transaction` | `PREV` | `gap_min DOUBLE` | Chronological transaction sequence on a card. |
| `INVOLVES` | `ClosedCase` | `Transaction` | `INVOLVED_IN_CLOSED_CASE` | None | Links historical case to involved transactions. |
| `ON_CARD` | `ClosedCase` | `Card` | `HAS_CLOSED_CASE` | None | Links historical case to primary card investigated. |
| `CONNECTED_TO`| `ClosedCase` | `Card` | `CONNECTED_CLOSED_CASE` | None | Links historical case to secondary cards in ring. |
| `CASE_INVOLVES`| `Case` | `Transaction` | `INVOLVED_IN_CASE` | None | Runtime link from agent case to transactions. |
| `CASE_ON_CARD` | `Case` | `Card` | `HAS_CASE` | None | Runtime link from agent case to primary card. |
| `CASE_CONNECTED_TO`| `Case` | `Card` | `CONNECTED_CASE` | None | Runtime link from agent case to connected cards. |
| `FROM_DEVICE` | `Transaction` | `DeviceProfile` | `DEVICE_FOR_TXN` | None | Links online transaction to device fingerprint. |
| `BILLED_IN` | `Transaction` | `BillingRegion` | `REGION_FOR_TXN` | None | Links transaction to billing region (`addr1`). |
| `PURCHASER_EMAIL`| `Transaction` | `EmailDomain` | `EMAIL_FOR_TXN` | None | Links transaction to purchaser email domain. |
| `LINKED_DEVICE`| `Card` | `DeviceProfile` | `USED_ON` | None | Direct 1-hop link between card and device profiles. |

---

## 4. Key Graph Traversal Pathways

1. **Customer $\to$ Cards $\to$ Transactions**:
   `Customer -(OWNS)-> Card -(MADE)-> Transaction`
   *Use case*: Reconstructing customer-wide spending, checking if multiple cards owned by the same customer are compromised (Policy R10).

2. **Shared Device Ring Traversal**:
   `Card -(LINKED_DEVICE)-> DeviceProfile -(USED_ON)-> Card -(HAS_CLOSED_CASE)-> ClosedCase`
   *Use case*: Multi-card fraud ring detection (Policy R6, HHG-014).

3. **Regional Baseline & Travel Traversal**:
   `Card -(MADE)-> Transaction -(BILLED_IN)-> BillingRegion`
   *Use case*: Determining historical home regions vs. new region for out-of-region detection (Policy R2, R3).

4. **Card Sequence Traversal**:
   `Transaction -(NEXT)-> Transaction`
   *Use case*: Card testing velocity scans and burst detection (Policy R5).
