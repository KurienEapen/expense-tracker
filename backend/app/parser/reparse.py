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
    from app.categorizer.ignore_service import check_if_message_ignored
    ignored_rule = check_if_message_ignored(db, raw.body, raw.sender)
    if ignored_rule:
        logger.info(f"RawMessage #{raw.id} skipped by IgnoreRule #{ignored_rule.id}: {ignored_rule.description}")
        return None

    parsed = parse_message(raw.sender, raw.body, raw.received_at_utc)
    if not parsed:
        return None

    # Parse location from raw_message if available
    loc_lat, loc_lng, loc_name, loc_addr = None, None, None, None
    if raw.location_json:
        try:
            import json
            from app.services.geocoding import reverse_geocode
            loc_data = json.loads(raw.location_json)
            loc_lat = loc_data.get("lat") or loc_data.get("latitude")
            loc_lng = loc_data.get("lng") or loc_data.get("longitude")
            if loc_lat and loc_lng:
                loc_name, loc_addr = reverse_geocode(loc_lat, loc_lng, parsed.merchant_clean or parsed.merchant_raw)
        except Exception as e:
            logger.warning(f"Location parsing failed for RawMessage #{raw.id}: {e}")

    # Check for existing transaction linked to this raw_message_id
    txn = db.query(Transaction).filter(Transaction.raw_message_id == raw.id).first()

    # Check for near-duplicate transaction created from another raw_message
    if not txn:
        existing_dup = db.query(Transaction).filter(
            Transaction.issuer == parsed.issuer,
            Transaction.amount_paise == parsed.amount_paise,
            Transaction.merchant_raw == parsed.merchant_raw,
            Transaction.transacted_at_utc == parsed.transacted_at_utc
        ).first()
        if existing_dup:
            logger.info(f"RawMessage #{raw.id} matches existing Transaction #{existing_dup.id}, skipping duplicate insertion")
            return existing_dup

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
        if not txn.review_source or txn.review_source == "auto":
            txn.category = parsed.category
        txn.transacted_at_utc = parsed.transacted_at_utc
        txn.parsed_by_template_id = parsed.parsed_by_template_id
        txn.parser_confidence = parsed.parser_confidence
        txn.status = parsed.status
        if loc_lat and loc_lng:
            txn.location_lat = loc_lat
            txn.location_lng = loc_lng
            txn.location_name = loc_name
            txn.location_address = loc_addr
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
            location_lat=loc_lat,
            location_lng=loc_lng,
            location_name=loc_name,
            location_address=loc_addr
        )
        db.add(txn)

    # Apply auto-categorization if not explicitly reviewed by user
    if not txn.reviewed_at_utc or txn.review_source == "auto":
        apply_categorization_to_transaction(db, txn)

    # Apply date-range auto-tagging (e.g. active trips/events)
    from app.services.tag_service import auto_tag_transaction
    auto_tag_transaction(db, txn)

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
