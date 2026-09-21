"""
src/detectors/recurring_merchant_scan.py — Recurring Merchant Scan Detector

Identifies legitimate subscriptions / recurring charges (R7 cases).
"""

import pandas as pd


def recurring_merchant_scan(card_id, amount, txn_id, transactions_df):
    def _not_triggered(reason):
        return {
            "detector": "recurring_merchant_scan",
            "triggered": False,
            "confidence": "low",
            "findings": reason,
            "entity_ids": [card_id],
            "transaction_ids": [],
            "explanation": f"Checked recurring pattern for card {card_id} with amount ${float(amount):.2f}: {reason}",
            "limitations": "Cannot confirm merchant name without external merchant descriptor data."
        }

    card_txns = transactions_df[
        (transactions_df['card_id'] == card_id) &
        (transactions_df['TransactionID'] != txn_id)
    ].copy()
    if card_txns.empty:
        return _not_triggered("No prior transactions on this card.")
        
    curr = transactions_df[transactions_df['TransactionID'] == txn_id]
    if curr.empty:
        return _not_triggered("Flagged transaction not found.")
        
    curr_product = curr.iloc[0]['ProductCD']
    card_txns['TransactionAmt'] = pd.to_numeric(card_txns['TransactionAmt'], errors='coerce')
    card_txns['ts'] = pd.to_datetime(card_txns['ts'])
    
    amount_f = float(amount)
    low, high = amount_f * 0.97, amount_f * 1.03
    matches = card_txns[
        (card_txns['TransactionAmt'] >= low) &
        (card_txns['TransactionAmt'] <= high) &
        (card_txns['ProductCD'] == curr_product)
    ].sort_values('ts')
    
    if len(matches) < 3:
        return _not_triggered(f"Only {len(matches)} prior matching charges (need >= 3).")
        
    # 1. Check simple consecutive gaps
    gaps = matches['ts'].diff().dt.days.dropna()
    monthly = gaps[(gaps >= 25) & (gaps <= 35)]
    triggered = (len(monthly) >= (len(gaps) * 0.6) and len(monthly) >= 2) if len(gaps) > 0 else False
    
    # 2. Check monthly representative cadence (for active cards with multiple transactions in range)
    if not triggered:
        curr_ts = pd.to_datetime(curr.iloc[0]['ts']) if pd.notna(curr.iloc[0].get('ts')) else None
        curr_day = curr_ts.day if curr_ts is not None else 15
        matches_copy = matches.copy()
        matches_copy['month'] = matches_copy['ts'].dt.to_period('M')
        matches_copy['day_diff'] = (matches_copy['ts'].dt.day - curr_day).abs()
        monthly_reps = matches_copy.sort_values(['month', 'day_diff']).groupby('month').first().reset_index()
        
        if len(monthly_reps) >= 3:
            rep_gaps = monthly_reps['ts'].diff().dt.days.dropna()
            rep_monthly = rep_gaps[(rep_gaps >= 24) & (rep_gaps <= 38)]
            if len(rep_monthly) >= (len(rep_gaps) * 0.5) and len(rep_monthly) >= 2:
                triggered = True
                matches = monthly_reps
                gaps = rep_gaps

    if not triggered:
        return _not_triggered(f"Amounts match but cadence not monthly (gaps: {gaps.tolist()}).")
        
    return {
        "detector": "recurring_merchant_scan",
        "triggered": True,
        "confidence": "high" if len(matches) >= 5 else "medium",
        "findings": f"{len(matches)} prior charges of ${amount_f:.2f} ±3% on ProductCD '{curr_product}' with monthly cadence on card {card_id}.",
        "entity_ids": [card_id],
        "transaction_ids": matches['TransactionID'].astype(str).tolist(),
        "explanation": f"Card {card_id} has {len(matches)} prior transactions matching amount ${amount_f:.2f} ±3% and ProductCD '{curr_product}', spaced approximately monthly (avg gap: {gaps.mean():.0f} days). Consistent with a recurring subscription charge.",
        "limitations": "Cannot confirm merchant name. Customer may still dispute a genuine recurring charge."
    }
