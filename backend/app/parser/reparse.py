import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.models.raw_message import RawMessage
from app.models.transaction import Transaction
from app.parser.engine import parse_message
from app.categorizer.service import apply_categorization_to_transaction

logger = logging.getLogger(__name__)

def reparse_raw_message(db: Session, raw: RawMessage) -> Optional[Transaction]:
    """
    Parses a single RawMessage, upserts the corresponding Transaction record,
    and applies multi-tier auto-categorization.
    """
    parsed = parse_message(raw.sender, raw.body, raw.received_at_utc)
    if not parsed:
        return None

    # Check for existing transaction linked to this raw_message_id
    txn = db.query(Transaction).filter(Transaction.raw_message_id == raw.id).first()
    if txn:
        txn.source = raw.source
        txn.issuer = parsed.issuer
        txn.card_type = parsed.card_type
        txn.card_last4 = parsed.card_last4
        txn.transaction_type = parsed.transaction_type
        txn.amount_paise = parsed.amount_paise
        txn.currency = parsed.currency
        txn.merchant_raw = parsed.merchant_raw
        txn.merchant_clean = parsed.merchant_clean
        # Retain category if already reviewed by user, else use template category
        if not txn.review_source or txn.review_source == "auto":
            txn.category = parsed.category
        txn.transacted_at_utc = parsed.transacted_at_utc
        txn.parsed_by_template_id = parsed.parsed_by_template_id
        txn.parser_confidence = parsed.parser_confidence
        txn.status = parsed.status
    else:
        txn = Transaction(
            raw_message_id=raw.id,
            source=raw.source,
            issuer=parsed.issuer,
            card_type=parsed.card_type,
            card_last4=parsed.card_last4,
            transaction_type=parsed.transaction_type,
            amount_paise=parsed.amount_paise,
            currency=parsed.currency,
            merchant_raw=parsed.merchant_raw,
            merchant_clean=parsed.merchant_clean,
            category=parsed.category,
            transacted_at_utc=parsed.transacted_at_utc,
            parsed_by_template_id=parsed.parsed_by_template_id,
            parser_confidence=parsed.parser_confidence,
            status=parsed.status,
        )
        db.add(txn)

    # Apply auto-categorization if not explicitly reviewed by user
    if not txn.reviewed_at_utc or txn.review_source == "auto":
        apply_categorization_to_transaction(db, txn)

    db.commit()
    db.refresh(txn)
    return txn

def reparse_all(db: Session, limit: Optional[int] = None) -> Dict[str, int]:
    """
    Reparses all or batch of RawMessages in SQLite database and updates Transactions.
    """
    query = db.query(RawMessage).order_by(RawMessage.id.asc())
    if limit:
        query = query.limit(limit)

    raw_messages = query.all()
    total = len(raw_messages)
    parsed_count = 0
    fallback_count = 0
    unparsed_count = 0

    for raw in raw_messages:
        txn = reparse_raw_message(db, raw)
        if txn:
            if txn.parser_confidence >= 1.0:
                parsed_count += 1
            else:
                fallback_count += 1
        else:
            unparsed_count += 1

    return {
        "total_raw": total,
        "template_parsed": parsed_count,
        "fallback_parsed": fallback_count,
        "unparsed": unparsed_count,
    }
