import json
from datetime import datetime
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import authenticate_device
from app.models.device import Device
from app.models.raw_message import RawMessage
from pydantic import BaseModel
from app.schemas.ingest import IngestPayload, IngestResponse
from app.core.security import compute_idempotency_key
from app.parser.reparse import reparse_raw_message

router = APIRouter()

@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_200_OK)
def ingest_message(
    payload: IngestPayload,
    db: Session = Depends(get_db),
    device: Device = Depends(authenticate_device)
):
    # 1. Calculate canonical idempotency key
    canonical_key = compute_idempotency_key(
        sender=payload.sender,
        body=payload.body,
        received_at_ms=payload.received_at_ms
    )
    
    # Use client key or canonical key if they match, else prefer canonical
    idempotency_key = payload.idempotency_key or canonical_key

    # 2. Check for duplicate idempotency key
    existing = db.query(RawMessage).filter(RawMessage.idempotency_key == idempotency_key).first()
    if existing:
        return IngestResponse(
            status="duplicate",
            raw_id=existing.id,
            message="Message with this idempotency key was already stored"
        )
    
    # 3. Serialize location if provided
    location_json = json.dumps(payload.location.model_dump()) if payload.location else None
    
    # 4. Construct and persist RawMessage
    received_utc = datetime.utcfromtimestamp(payload.received_at_ms / 1000.0)
    raw_message = RawMessage(
        idempotency_key=idempotency_key,
        source=payload.source,
        sender=payload.sender,
        app_package=payload.app_package,
        body=payload.body,
        received_at_ms=payload.received_at_ms,
        received_at_utc=received_utc,
        device_tz=payload.device_tz,
        location_json=location_json,
        ocr_confidence=payload.ocr_confidence,
        device_id=device.id,
        app_version=payload.app_version,
        ingested_at_utc=datetime.utcnow()
    )
    
    db.add(raw_message)
    db.commit()
    db.refresh(raw_message)

    # 5. Automatically parse message into Transaction record
    txn = reparse_raw_message(db, raw_message)
    
    return IngestResponse(
        status="stored",
        raw_id=raw_message.id,
        parsed_transaction_id=txn.id if txn else None,
        needs_review=txn.needs_review if txn else False,
        merchant=txn.merchant_clean if txn else None,
        amount_inr=(txn.amount_paise / 100.0) if txn else None,
        category=txn.category if txn else None,
        location_name=txn.location_name if txn else None,
        message="Successfully ingested and parsed raw message"
    )

class ConvertRawRequest(BaseModel):
    amount_inr: float
    merchant: str
    category: str
    transaction_type: str = "debit"

@router.post("/convert-raw/{raw_id}", response_model=IngestResponse)
def convert_raw_to_transaction(
    raw_id: int,
    payload: ConvertRawRequest,
    db: Session = Depends(get_db)
):
    """
    Manually converts an unparsed or missed RawMessage into a full Transaction record
    from the Android Companion App or Web Dashboard, and creates a long-term merchant rule
    so all future messages from this sender/merchant are automatically recognized.
    """
    from fastapi import HTTPException
    from app.models.merchant_rule import MerchantRule

    raw = db.query(RawMessage).filter(RawMessage.id == raw_id).first()
    if not raw:
        raise HTTPException(status_code=404, detail=f"RawMessage #{raw_id} not found")

    amount_paise = int(round(payload.amount_inr * 100))
    merchant_clean = payload.merchant.strip()

    txn = db.query(Transaction).filter(Transaction.raw_message_id == raw.id).first()
    if not txn:
        txn = Transaction(
            raw_message_id=raw.id,
            source=raw.source,
            issuer=raw.sender,
            card_type="debit" if payload.transaction_type == "debit" else "credit",
            card_last4=None,
            transaction_type=payload.transaction_type,
            amount_paise=amount_paise,
            currency="INR",
            merchant_raw=merchant_clean,
            merchant_clean=merchant_clean,
            category=payload.category,
            transacted_at_utc=raw.received_at_utc,
            parsed_by_template_id="manual_conversion",
            parser_confidence=1.0,
            status="settled",
            needs_review=False,
            review_source="user_converted",
            reviewed_at_utc=datetime.utcnow()
        )
        db.add(txn)
    else:
        txn.merchant_raw = merchant_clean
        txn.merchant_clean = merchant_clean
        txn.amount_paise = amount_paise
        txn.category = payload.category
        txn.needs_review = False
        txn.review_source = "user_converted"

    pattern = merchant_clean.lower()
    existing_rule = db.query(MerchantRule).filter(MerchantRule.pattern == pattern).first()
    if not existing_rule:
        new_rule = MerchantRule(
            pattern=pattern,
            category=payload.category,
            is_user_defined=True,
            confidence=1.0,
            created_at_utc=datetime.utcnow()
        )
        db.add(new_rule)

    db.commit()
    db.refresh(txn)

    return IngestResponse(
        status="stored",
        raw_id=raw.id,
        parsed_transaction_id=txn.id,
        needs_review=False,
        merchant=txn.merchant_clean,
        amount_inr=txn.amount_paise / 100.0,
        category=txn.category,
        message=f"Successfully converted SMS into transaction and learned rule for '{merchant_clean}'"
    )

