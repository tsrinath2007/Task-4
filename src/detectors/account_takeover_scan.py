"""
src/detectors/account_takeover_scan.py — Account Takeover Scan Detector

Checks for:
1. Significant deviation in match flags (M3, M4, M6) compared to >= 90% of prior history.
2. Mixed-channel shifts: Established in-person cardholder pattern preceding sudden online burst.
"""

import pandas as pd


def account_takeover_scan(card_id, txn_id, transactions_df, identity_df=None):
    def _not_triggered(reason):
        return {
            "detector": "account_takeover_scan",
            "triggered": False,
            "confidence": "low",
            "findings": reason,
            "entity_ids": [card_id],
            "transaction_ids": [str(txn_id)],
            "explanation": f"ATO scan on card {card_id} (txn {txn_id}): {reason}",
            "limitations": "Changes in user billing address or credential updates can cause benign match-flag shifts."
        }

    txn_str = str(txn_id)
    curr_match = transactions_df[transactions_df["TransactionID"] == txn_str]
    if curr_match.empty:
        curr_match = transactions_df[transactions_df["TransactionID"] == txn_id]
    if curr_match.empty:
        return _not_triggered(f"Transaction {txn_id} not found.")

    curr_txn = curr_match.iloc[0]

    # Historical transactions for this card
    card_txns = transactions_df[
        (transactions_df["card_id"] == card_id) &
        (transactions_df["TransactionID"] != txn_str)
    ].copy()

    if len(card_txns) < 5:
        return _not_triggered("Fewer than 5 historical transactions to establish M-flag baselines.")

    # Check M-flag consistency (M3, M4, M6)
    m_flags = ["M3", "M4", "M6"]
    anomalous_flags = []

    for flag in m_flags:
        if flag in curr_txn.index and pd.notna(curr_txn[flag]):
            curr_val = str(curr_txn[flag]).strip()
            hist_vals = card_txns[flag].dropna().astype(str).str.strip()
            if len(hist_vals) >= 5:
                mode_val = hist_vals.mode().iloc[0]
                dominant_ratio = (hist_vals == mode_val).mean()
                if dominant_ratio >= 0.90 and curr_val != mode_val:
                    anomalous_flags.append(f"{flag}: '{curr_val}' vs dominant '{mode_val}' ({dominant_ratio*100:.0f}%)")

    # Check mixed-channel: predominantly in-person history followed by online burst
    in_person_count = (card_txns["ProductCD"] == "W").sum()
    in_person_ratio = in_person_count / len(card_txns)
    is_curr_online = (curr_txn["ProductCD"] != "W")
    has_mixed_channel = (in_person_ratio >= 0.70 and is_curr_online)

    if not anomalous_flags and not (has_mixed_channel and len(anomalous_flags) > 0):
        if not anomalous_flags:
            return _not_triggered(f"M flags (M3, M4, M6) consistent with >= 90% of cardholder's prior history.")

    confidence = "high" if (len(anomalous_flags) >= 2 and has_mixed_channel) else ("medium" if len(anomalous_flags) >= 1 else "low")

    findings = f"M-flag anomaly detected ({'; '.join(anomalous_flags)})" + (
        f" with mixed-channel shift (predominantly in-person {in_person_ratio*100:.0f}% transitioned to online)." if has_mixed_channel else "."
    )

    return {
        "detector": "account_takeover_scan",
        "triggered": True,
        "confidence": confidence,
        "findings": findings,
        "entity_ids": [card_id],
        "transaction_ids": [txn_str],
        "explanation": f"Card {card_id} exhibited credential compromise / account takeover signatures: {'; '.join(anomalous_flags)} inconsistent with established card history."
                       + (" Mixed-channel pattern indicates credential theft rather than card cloning." if has_mixed_channel else ""),
        "limitations": "Does not prove identity compromise without external password reset or credential dump telemetry."
    }
