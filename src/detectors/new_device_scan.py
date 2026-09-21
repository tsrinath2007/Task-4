"""
src/detectors/new_device_scan.py — New Device Scan Detector

Checks for:
1. Online transaction marked with id_15 == 'New'.
2. Device profile never observed on this card's prior history.
3. Proxy indicators in id_23 (e.g. IP_PROXY:ANONYMOUS).
Note: ProductCD == 'W' (in-person) has no device records — this is normal and never triggers.
"""

import pandas as pd


def new_device_scan(txn_id, card_id, transactions_df, identity_df=None):
    def _not_triggered(reason, entity_ids=None):
        return {
            "detector": "new_device_scan",
            "triggered": False,
            "confidence": "low",
            "findings": reason,
            "entity_ids": entity_ids or [card_id],
            "transaction_ids": [str(txn_id)],
            "explanation": f"New device scan on txn {txn_id} (card {card_id}): {reason}",
            "limitations": "Legitimate users regularly purchase new phones or laptops, which naturally generate 'New' device profiles."
        }

    txn_str = str(txn_id)
    curr_match = transactions_df[transactions_df["TransactionID"] == txn_str]
    if curr_match.empty:
        curr_match = transactions_df[transactions_df["TransactionID"] == txn_id]
    if curr_match.empty:
        return _not_triggered(f"Transaction {txn_id} not found.")

    curr_txn = curr_match.iloc[0]

    # In-person rule: ProductCD == 'W' has no device record; this is normal
    if curr_txn["ProductCD"] == "W" or curr_txn["channel"] == "in_person":
        return _not_triggered("In-person transaction (ProductCD='W'); lack of device record is normal.")

    id_15 = str(curr_txn.get("id_15", "")).strip()
    id_23 = str(curr_txn.get("id_23", "")).strip()
    curr_device = str(curr_txn.get("device_id", "")).strip()

    if not curr_device or curr_device == "nan":
        return _not_triggered("No device profile captured for this transaction.")

    # Check card history
    card_txns = transactions_df[
        (transactions_df["card_id"] == card_id) &
        (transactions_df["TransactionID"] != txn_str)
    ].copy()

    prior_devices = set(card_txns["device_id"].dropna().astype(str).unique())
    is_new_device_for_card = (curr_device not in prior_devices)

    is_marked_new = (id_15.lower() == "new")

    # Trigger rule: id_15 == 'New' AND device not seen before on this card
    if is_marked_new and is_new_device_for_card:
        is_proxy = "anonymous" in id_23.lower() or "proxy" in id_23.lower()
        confidence = "high" if is_proxy else ("medium" if len(card_txns) >= 5 else "low")
        
        proxy_note = f" via anonymous proxy ({id_23})" if is_proxy else ""
        findings = f"Online purchase using new device profile {curr_device} (id_15=New){proxy_note}, never seen in {len(card_txns)} prior transactions on card {card_id}."

        return {
            "detector": "new_device_scan",
            "triggered": True,
            "confidence": confidence,
            "findings": findings,
            "entity_ids": [card_id, curr_device],
            "transaction_ids": [txn_str],
            "explanation": f"Card {card_id} transacted online with device profile {curr_device}, which was flagged as 'New' by the identity service and has no prior history on this card."
                           + (f" Additionally, proxy rating indicates {id_23}." if is_proxy else ""),
            "limitations": "Customers legitimately replace hardware or upgrade browsers; cannot distinguish replacement from theft without behavioral context."
        }

    return _not_triggered(
        f"Device {curr_device} is not novel or not marked New (id_15='{id_15}', prior_seen={not is_new_device_for_card}).",
        entity_ids=[card_id, curr_device]
    )
