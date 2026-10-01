import re
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.raw_message import RawMessage
from app.models.ignore_rule import IgnoreRule
from app.categorizer.ignore_extractor import extract_ignore_rule_for_message

def dismiss_as_non_transactional(db: Session, txn_id: int) -> Tuple[Optional[Transaction], Optional[IgnoreRule], int]:
    """
    Dismisses a falsely categorized transaction as non-transactional:
    1. Extracts an intelligent ignore pattern from the raw SMS.
    2. Creates and persists an IgnoreRule.
    3. Flags the current transaction as 'ignored' (removes from expenses & review queue).
    4. Cascades the rule to any other pending unreviewed transactions matching this pattern.
    """
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        return None, None, 0

    raw_msg = txn.raw_message
    body = (raw_msg.body if raw_msg and raw_msg.body else (txn.notes or txn.merchant_raw or f"{txn.issuer} non-expense transaction")).strip()
    sender = (raw_msg.sender if raw_msg and raw_msg.sender else (txn.issuer or "BANK")).strip()

    # Extract pattern and metadata
    pattern, description, sender_filter = extract_ignore_rule_for_message(body, sender)

    # Check if a matching rule already exists
    existing_rule = db.query(IgnoreRule).filter(
        IgnoreRule.pattern == pattern,
        IgnoreRule.sender_filter == sender_filter,
        IgnoreRule.is_active == True
    ).first()

    if existing_rule:
        rule = existing_rule
        rule.match_count += 1
    else:
        sample_snippet = body.strip()[:200]
        rule = IgnoreRule(
            pattern=pattern,
            pattern_type="regex",
            sender_filter=sender_filter,
            description=description,
            sample_text=sample_snippet,
            match_count=1,
            is_active=True,
            created_at_utc=datetime.utcnow()
        )
        db.add(rule)
        db.flush()

    # Mark current transaction as ignored
    txn.status = "ignored"
    txn.needs_review = False
    txn.category = "Non-Expense"
    txn.review_source = "user_dismissed"
    txn.reviewed_at_utc = datetime.utcnow()

    # Cascade to any other pending unreviewed transactions matching this rule
    cascaded_count = 0
    pending_txns = db.query(Transaction).filter(
        Transaction.needs_review == True,
        Transaction.id != txn.id
    ).all()

    regex = re.compile(rule.pattern, re.IGNORECASE)
    for p_txn in pending_txns:
        p_raw = p_txn.raw_message
        p_body = p_raw.body if p_raw else (p_txn.notes or "")
        p_sender = p_raw.sender if p_raw else p_txn.issuer
        p_clean_sender = p_sender.split("-")[0].strip().upper() if p_sender else None

        if rule.sender_filter and p_clean_sender != rule.sender_filter:
            continue

        if regex.search(p_body):
            p_txn.status = "ignored"
            p_txn.needs_review = False
            p_txn.category = "Non-Expense"
            p_txn.review_source = "rule_cascade"
            p_txn.reviewed_at_utc = datetime.utcnow()
            cascaded_count += 1
            rule.match_count += 1

    db.commit()
    db.refresh(txn)
    db.refresh(rule)
    return txn, rule, cascaded_count

def get_active_ignore_rules(db: Session) -> List[IgnoreRule]:
    """Returns all active learned ignore rules sorted by recency."""
    return db.query(IgnoreRule).filter(
        IgnoreRule.is_active == True
    ).order_by(IgnoreRule.created_at_utc.desc()).all()

def delete_ignore_rule(db: Session, rule_id: int) -> bool:
    """Deletes/deactivates an ignore rule."""
    rule = db.query(IgnoreRule).filter(IgnoreRule.id == rule_id).first()
    if not rule:
        return False
    rule.is_active = False
    db.commit()
    return True

def check_if_message_ignored(db: Session, body: str, sender: Optional[str] = None) -> Optional[IgnoreRule]:
    """
    Checks if an incoming message body matches any active IgnoreRule.
    Used by parser ingestion to skip non-transactional messages at the source.
    """
    rules = get_active_ignore_rules(db)
    clean_sender = sender.split("-")[0].strip().upper() if sender else None

    for rule in rules:
        if rule.sender_filter and clean_sender != rule.sender_filter:
            continue
        try:
            if re.search(rule.pattern, body, re.IGNORECASE):
                rule.match_count += 1
                db.commit()
                return rule
        except re.error:
            continue
    return None
