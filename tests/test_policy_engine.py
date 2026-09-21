"""
tests/test_policy_engine.py — Policy Engine Sanity & Compliance Tests

Verifies:
1. R7 recurring charge dispute must NOT block and includes WARN_CUSTOMER
2. FILE_REPORT must always have route L2
3. Low probability leads to CLOSE_NO_FRAUD
4. BLOCK_CARD route: L1 if <= 2500, L2 if > 2500
5. BLOCK_ALL_CARDS route is always L2
6. SAR is required iff FILE_REPORT is in actions
"""

import pytest
from src.policy.policy_engine import decide_initial, decide_after_evidence


def test_r7_recurring_charge():
    # R7: Recurring charge dispute must NOT block
    r7 = decide_initial('uncertain', 0.45, 49.0, 0, [], 'none', 'customer_report', True)
    actions = [a['action'] for a in r7['actions']]
    assert 'BLOCK_CARD' not in actions, 'R7 FAIL: blocking a recurring charge'
    assert 'WARN_CUSTOMER' in actions, 'R7 FAIL: missing WARN_CUSTOMER'
    assert 'CREATE_CASE' in actions, 'R7 FAIL: missing CREATE_CASE'
    assert 'VERIFY_WITH_CUSTOMER' in actions, 'R7 FAIL: missing VERIFY_WITH_CUSTOMER'
    assert r7['sar_required'] is False


def test_file_report_always_l2():
    # R2 with exposure > 1000 -> FILE_REPORT (L2)
    r2 = decide_after_evidence('fraud', 0.88, 1500.0, 0, [], 'card_not_present_fraud', 'risk_score', False, 'denied')
    file_reports = [a for a in r2['actions'] if a['action'] == 'FILE_REPORT']
    assert len(file_reports) > 0, "Missing FILE_REPORT"
    for fr in file_reports:
        assert fr['route'] == 'L2', f"FILE_REPORT route is {fr['route']}, expected L2"
    assert r2['sar_required'] is True


def test_legitimate_close_no_fraud():
    # Low probability -> CLOSE_NO_FRAUD
    r3 = decide_initial('legitimate', 0.08, 49.0, 0, [], 'none', 'risk_score', False)
    actions = [a['action'] for a in r3['actions']]
    assert 'CLOSE_NO_FRAUD' in actions, 'Legit FAIL: missing CLOSE_NO_FRAUD'
    assert 'BLOCK_CARD' not in actions
    assert r3['sar_required'] is False


def test_block_card_routes():
    # Exposure <= 2500 -> L1
    res_l1 = decide_after_evidence('fraud', 0.88, 1500.0, 0, [], 'card_not_present_fraud', 'risk_score', False, 'denied')
    block_l1 = next(a for a in res_l1['actions'] if a['action'] == 'BLOCK_CARD')
    assert block_l1['route'] == 'L1'

    # Exposure > 2500 -> L2
    res_l2 = decide_after_evidence('fraud', 0.88, 3000.0, 0, [], 'card_not_present_fraud', 'risk_score', False, 'denied')
    block_l2 = next(a for a in res_l2['actions'] if a['action'] == 'BLOCK_CARD')
    assert block_l2['route'] == 'L2'


def test_block_all_cards_l2():
    res = decide_after_evidence('fraud', 0.88, 500.0, 0, [], 'card_not_present_fraud', 'risk_score', False, 'denied', confirmed_fraud_card_count=2)
    block_all = next(a for a in res['actions'] if a['action'] == 'BLOCK_ALL_CARDS')
    assert block_all['route'] == 'L2'
