from datetime import datetime
from app.models.raw_message import RawMessage
from app.models.transaction import Transaction
from app.categorizer.ignore_service import (
    dismiss_as_non_transactional,
    get_active_ignore_rules,
    delete_ignore_rule,
    check_if_message_ignored
)

def test_dismiss_non_transactional_flow(db):
    # 1. Create a dummy promo raw message and false-positive transaction
    raw = RawMessage(
        idempotency_key="promo_test_123",
        source="sms",
        sender="HDFCBK-S",
        body="You've won Rs.500 voucher on HDFC Bank Credit Card. Use code 123.",
        received_at_ms=1680000000000,
        device_id="test_dev",
        received_at_utc=datetime.utcnow()
    )
    db.add(raw)
    db.commit()

    txn = Transaction(
        raw_message_id=raw.id,
        source="sms",
        issuer="HDFC",
        card_type="credit",
        transaction_type="debit",
        amount_paise=50000,
        merchant_raw="Unknown",
        transacted_at_utc=datetime.utcnow(),
        needs_review=True,
        status="settled"
    )
    db.add(txn)
    db.commit()

    # 2. Dismiss as non-transactional
    dismissed_txn, rule, cascaded = dismiss_as_non_transactional(db, txn.id)
    assert dismissed_txn is not None
    assert dismissed_txn.status == "ignored"
    assert dismissed_txn.needs_review is False
    assert dismissed_txn.category == "Non-Expense"
    assert rule is not None
    assert "voucher" in rule.pattern
    assert rule.sender_filter == "HDFCBK"

    # 3. Verify rule is active and blocks future incoming SMS
    matched_rule = check_if_message_ignored(
        db,
        "Congrats! You won Rs.1000 voucher on card.",
        sender="HDFCBK-T"
    )
    assert matched_rule is not None
    assert matched_rule.id == rule.id

    # 4. Delete rule
    success = delete_ignore_rule(db, rule.id)
    assert success is True
    assert len(get_active_ignore_rules(db)) == 0
