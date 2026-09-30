from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.transaction import Transaction

router = APIRouter()

class TransactionResponse(BaseModel):
    id: int
    raw_message_id: Optional[int]
    source: str
    issuer: str
    card_type: str
    card_last4: Optional[str]
    transaction_type: str
    amount_paise: int
    amount_inr: float
    currency: str
    merchant_raw: Optional[str]
    merchant_clean: Optional[str]
    category: Optional[str]
    transacted_at_utc: datetime
    parsed_by_template_id: Optional[str]
    parser_confidence: float
    status: str
    raw_body: Optional[str] = None
    raw_sender: Optional[str] = None

    @classmethod
    def from_orm_model(cls, t: Transaction) -> "TransactionResponse":
        return cls(
            id=t.id,
            raw_message_id=t.raw_message_id,
            source=t.source,
            issuer=t.issuer,
            card_type=t.card_type,
            card_last4=t.card_last4,
            transaction_type=t.transaction_type,
            amount_paise=t.amount_paise,
            amount_inr=t.amount_paise / 100.0,
            currency=t.currency,
            merchant_raw=t.merchant_raw,
            merchant_clean=t.merchant_clean,
            category=t.category,
            transacted_at_utc=t.transacted_at_utc,
            parsed_by_template_id=t.parsed_by_template_id,
            parser_confidence=t.parser_confidence,
            status=t.status,
            raw_body=t.raw_message.body if t.raw_message else None,
            raw_sender=t.raw_message.sender if t.raw_message else None,
        )

@router.get("", response_model=List[TransactionResponse])
def list_transactions(
    issuer: Optional[str] = Query(None, description="Filter by card issuer, e.g. HDFC, ICICI"),
    card_last4: Optional[str] = Query(None, description="Filter by card last 4 digits"),
    transaction_type: Optional[str] = Query(None, description="debit | credit | surcharge_waiver"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Lists parsed transactions with optional filtering and pagination.
    """
    query = db.query(Transaction)
    if issuer:
        query = query.filter(Transaction.issuer.ilike(f"%{issuer}%"))
    if card_last4:
        query = query.filter(Transaction.card_last4 == card_last4)
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)

    query = query.order_by(Transaction.transacted_at_utc.desc())
    items = query.offset(offset).limit(limit).all()
    return [TransactionResponse.from_orm_model(t) for t in items]

@router.get("/{txn_id}", response_model=TransactionResponse)
def get_transaction(txn_id: int, db: Session = Depends(get_db)):
    """
    Retrieves a single parsed transaction by ID.
    """
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with id {txn_id} not found"
        )
    return TransactionResponse.from_orm_model(txn)
