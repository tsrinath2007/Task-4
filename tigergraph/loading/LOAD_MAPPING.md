# TigerGraph Load Mapping Specification

**Target Graph**: `FraudInvestigationGraph`  
**Data Directory**: `data/processed/`  
**Encoding**: UTF-8  
**Format**: CSV with header row  

---

## 1. Loading Rules & Pre-Conditions

1. **Topological Order**: Vertices must be loaded and committed **before** loading edges.
2. **Missing & Empty Values**: Empty strings `""` must be mapped safely. For `ClosedCase`, `first_fraud_txn_id` is empty for all 900 cleared cases; loaders must not reject these rows.
3. **No Duplicate IDs**: Primary keys are pre-deduplicated in `data/processed/`.
4. **String Preservation**: Numeric-looking identifiers (`TransactionID`, `addr1`, `device_id`) must be loaded as strings to prevent float-conversion artifacts.

---

## 2. Vertex Load Mappings

### 2.1 Customer Vertex
- **Source File**: `data/processed/v_customer.csv`
- **Target Vertex**: `Customer`
- **Mapping**:
  | Target Attribute | Source Column | Type | Notes |
  |---|---|---|---|
  | `PRIMARY_ID` | `customer_id` | STRING | Pre-deduplicated (13,553 rows) |

### 2.2 Card Vertex
- **Source File**: `data/processed/v_card.csv`
- **Target Vertex**: `Card`
- **Mapping**:
  | Target Attribute | Source Column | Type | Notes |
  |---|---|---|---|
  | `PRIMARY_ID` | `card_id` | STRING | e.g. `C08623-K2` |
  | `customer_id` | `customer_id` | STRING | Owning customer ID |

### 2.3 DeviceProfile Vertex
- **Source File**: `data/processed/v_device.csv`
- **Target Vertex**: `DeviceProfile`
- **Mapping**:
  | Target Attribute | Source Column | Type | Notes |
  |---|---|---|---|
  | `PRIMARY_ID` | `device_id` | STRING | e.g. `D000001` |
  | `device_info` | `device_info` | STRING | |
  | `device_os` | `device_os` | STRING | |
  | `device_browser`| `device_browser`| STRING | |
  | `device_screen` | `device_screen` | STRING | |
  | `device_type` | `device_type` | STRING | `mobile` or `desktop` |

### 2.4 BillingRegion Vertex
- **Source File**: `data/processed/v_billing_region.csv`
- **Target Vertex**: `BillingRegion`
- **Mapping**:
  | Target Attribute | Source Column | Type | Notes |
  |---|---|---|---|
  | `PRIMARY_ID` | `addr1` | STRING | 332 unique regions |

### 2.5 EmailDomain Vertex
- **Source File**: `data/processed/v_email_domain.csv`
- **Target Vertex**: `EmailDomain`
- **Mapping**:
  | Target Attribute | Source Column | Type | Notes |
  |---|---|---|---|
  | `PRIMARY_ID` | `email_domain` | STRING | 59 unique domains |

### 2.6 ClosedCase Vertex
- **Source File**: `data/processed/v_closed_case.csv`
- **Target Vertex**: `ClosedCase`
- **Mapping**:
  | Target Attribute | Source Column | Type | Notes |
  |---|---|---|---|
  | `PRIMARY_ID` | `case_id` | STRING | `CC-0001` to `CC-5565` |
  | `customer_id` | `customer_id` | STRING | |
  | `card_id` | `card_id` | STRING | |
  | `opened_at` | `opened_at` | DATETIME | |
  | `closed_at` | `closed_at` | DATETIME | |
  | `outcome` | `outcome` | STRING | `confirmed_fraud` or `cleared` |
  | `pattern` | `pattern` | STRING | Typology or `none` |
  | `first_fraud_txn_id` | `first_fraud_txn_id` | STRING | Nullable (empty on cleared) |
  | `txn_ids` | `txn_ids` | STRING | Pipe-separated |
  | `n_txns` | `n_txns` | INT | |
  | `exposure_usd` | `exposure_usd` | DOUBLE | |
  | `connected_card_ids` | `connected_card_ids` | STRING | Nullable |
  | `actions_taken` | `actions_taken` | STRING | Pipe-separated |
  | `report_filed` | `report_filed` | STRING | `Yes` or `No` |
  | `analyst_notes` | `analyst_notes` | STRING | Full text notes |

### 2.7 Transaction Vertex
- **Source File**: `data/processed/v_transaction.csv`
- **Target Vertex**: `Transaction`
- **Mapping**:
  | Target Attribute | Source Column | Type | Notes |
  |---|---|---|---|
  | `PRIMARY_ID` | `TransactionID` | STRING | 590,742 rows |
  | `card_id` | `card_id` | STRING | Derived card |
  | `customer_id` | `customer_id` | STRING | |
  | `ts` | `ts` | DATETIME | ISO format |
  | `TransactionAmt`| `TransactionAmt`| DOUBLE | |
  | `ProductCD` | `ProductCD` | STRING | |
  | `addr1` | `addr1` | STRING | Nullable |
  | `P_emaildomain`| `P_emaildomain` | STRING | Nullable |
  | `R_emaildomain`| `R_emaildomain` | STRING | Nullable |
  | `risk_score` | `risk_score` | DOUBLE | Nullable |
  | `channel` | `channel` | STRING | |
  | `M1`–`M9` | `M1`–`M9` | STRING | Nullable |
  | `id_15` | `id_15` | STRING | Nullable |
  | `id_23` | `id_23` | STRING | Nullable |
  | `device_id` | `device_id` | STRING | Nullable |
  | `gap_min` | `gap_min` | DOUBLE | Nullable |
  | `prev_txn_id` | `prev_txn_id` | STRING | Nullable |

---

## 3. Edge Load Mappings

### 3.1 Customer -OWNS-> Card
- **Source File**: `data/processed/e_customer_owns_card.csv`
- **Target Edge**: `OWNS`
- **Mapping**: `FROM (customer_id) TO (card_id)`

### 3.2 Card -MADE-> Transaction
- **Source File**: `data/processed/e_card_made_txn.csv`
- **Target Edge**: `MADE`
- **Mapping**: `FROM (card_id) TO (TransactionID)`

### 3.3 Transaction -NEXT-> Transaction
- **Source File**: `data/processed/e_txn_next.csv`
- **Target Edge**: `NEXT`
- **Mapping**: `FROM (from_txn_id) TO (to_txn_id), gap_min = gap_min`

### 3.4 ClosedCase -INVOLVES-> Transaction
- **Source File**: `data/processed/e_case_involves_txn.csv`
- **Target Edge**: `INVOLVES`
- **Mapping**: `FROM (case_id) TO (TransactionID)`

### 3.5 ClosedCase -ON_CARD-> Card
- **Source File**: `data/processed/v_closed_case.csv`
- **Target Edge**: `ON_CARD`
- **Mapping**: `FROM (case_id) TO (card_id)`

### 3.6 Transaction -FROM_DEVICE-> DeviceProfile
- **Source File**: `data/processed/e_txn_from_device.csv`
- **Target Edge**: `FROM_DEVICE`
- **Mapping**: `FROM (TransactionID) TO (device_id)`

### 3.7 Transaction -BILLED_IN-> BillingRegion
- **Source File**: `data/processed/e_txn_billed_in.csv`
- **Target Edge**: `BILLED_IN`
- **Mapping**: `FROM (TransactionID) TO (addr1)`

### 3.8 Transaction -PURCHASER_EMAIL-> EmailDomain
- **Source File**: `data/processed/e_txn_purchaser_email.csv`
- **Target Edge**: `PURCHASER_EMAIL`
- **Mapping**: `FROM (TransactionID) TO (email_domain)`

### 3.9 Card -LINKED_DEVICE-> DeviceProfile
- **Source**: Traversal inference or derived via `e_txn_from_device` joined with `card_id`.

---

## 4. GSQL Loading Job Example

```gsql
USE GRAPH FraudInvestigationGraph

CREATE LOADING JOB load_fraud_data FOR GRAPH FraudInvestigationGraph {
  DEFINE FILENAME f_cust = "$sys.data_root/v_customer.csv";
  DEFINE FILENAME f_card = "$sys.data_root/v_card.csv";
  DEFINE FILENAME f_dev  = "$sys.data_root/v_device.csv";
  DEFINE FILENAME f_reg  = "$sys.data_root/v_billing_region.csv";
  DEFINE FILENAME f_mail = "$sys.data_root/v_email_domain.csv";
  DEFINE FILENAME f_case = "$sys.data_root/v_closed_case.csv";
  DEFINE FILENAME f_txn  = "$sys.data_root/v_transaction.csv";

  DEFINE FILENAME f_e_owns = "$sys.data_root/e_customer_owns_card.csv";
  DEFINE FILENAME f_e_made = "$sys.data_root/e_card_made_txn.csv";
  DEFINE FILENAME f_e_next = "$sys.data_root/e_txn_next.csv";
  DEFINE FILENAME f_e_involves = "$sys.data_root/e_case_involves_txn.csv";
  DEFINE FILENAME f_e_dev  = "$sys.data_root/e_txn_from_device.csv";
  DEFINE FILENAME f_e_bill = "$sys.data_root/e_txn_billed_in.csv";
  DEFINE FILENAME f_e_mail = "$sys.data_root/e_txn_purchaser_email.csv";

  // Load Vertices
  LOAD f_cust TO VERTEX Customer VALUES ($0) USING HEADER="true", SEPARATOR=",";
  LOAD f_card TO VERTEX Card VALUES ($0, $1) USING HEADER="true", SEPARATOR=",";
  LOAD f_dev  TO VERTEX DeviceProfile VALUES ($0, $1, $2, $3, $4, $5) USING HEADER="true", SEPARATOR=",";
  LOAD f_reg  TO VERTEX BillingRegion VALUES ($0) USING HEADER="true", SEPARATOR=",";
  LOAD f_mail TO VERTEX EmailDomain VALUES ($0) USING HEADER="true", SEPARATOR=",";
  LOAD f_case TO VERTEX ClosedCase VALUES ($0, $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14) USING HEADER="true", SEPARATOR=",";
  LOAD f_txn  TO VERTEX Transaction VALUES ($0, $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24) USING HEADER="true", SEPARATOR=",";

  // Load Edges
  LOAD f_e_owns TO EDGE OWNS VALUES ($0, $1) USING HEADER="true", SEPARATOR=",";
  LOAD f_e_made TO EDGE MADE VALUES ($0, $1) USING HEADER="true", SEPARATOR=",";
  LOAD f_e_next TO EDGE NEXT VALUES ($0, $1, $2) USING HEADER="true", SEPARATOR=",";
  LOAD f_e_involves TO EDGE INVOLVES VALUES ($0, $1) USING HEADER="true", SEPARATOR=",";
  LOAD f_case TO EDGE ON_CARD VALUES ($0, $2) USING HEADER="true", SEPARATOR=",";
  LOAD f_e_dev  TO EDGE FROM_DEVICE VALUES ($0, $1) USING HEADER="true", SEPARATOR=",";
  LOAD f_e_bill TO EDGE BILLED_IN VALUES ($0, $1) USING HEADER="true", SEPARATOR=",";
  LOAD f_e_mail TO EDGE PURCHASER_EMAIL VALUES ($0, $1) USING HEADER="true", SEPARATOR=",";
}
```
