import json
from datetime import datetime
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import authenticate_device
from app.models.device import Device
from app.models.raw_message import RawMessage
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
        message="Successfully ingested and parsed raw message"
    )
