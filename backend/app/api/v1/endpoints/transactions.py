from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
import csv
import io
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
    is_split: bool = False
    my_share_inr: Optional[float] = None
    reimbursable_inr: float = 0.0
    split_ratio_label: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    location_name: Optional[str] = None
    location_address: Optional[str] = None
    raw_body: Optional[str] = None
    raw_sender: Optional[str] = None

    @classmethod
    def from_orm_model(cls, t: Transaction) -> "TransactionResponse":
        my_share = (t.my_share_paise / 100.0) if getattr(t, 'my_share_paise', None) is not None else (t.amount_paise / 100.0)
        reimbursable = (getattr(t, 'reimbursable_paise', 0) or 0) / 100.0
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
            is_split=getattr(t, 'is_split', False),
            my_share_inr=my_share,
            reimbursable_inr=reimbursable,
            split_ratio_label=getattr(t, 'split_ratio_label', None),
            location_lat=getattr(t, 'location_lat', None),
            location_lng=getattr(t, 'location_lng', None),
            location_name=getattr(t, 'location_name', None),
            location_address=getattr(t, 'location_address', None),
            raw_body=t.raw_message.body if t.raw_message else None,
            raw_sender=t.raw_message.sender if t.raw_message else None,
        )

class CategoryStat(BaseModel):
    category: str
    amount_inr: float
    percentage: float
    count: int

class IssuerStat(BaseModel):
    issuer: str
    amount_inr: float
    count: int

class DailyTrendStat(BaseModel):
    date: str
    amount_inr: float

class SummaryStatsResponse(BaseModel):
    app_title: str
    total_spend_inr: float
    net_receivables_inr: float
    total_transactions_count: int
    unreviewed_count: int
    category_breakdown: List[CategoryStat]
    issuer_breakdown: List[IssuerStat]
    daily_trends: List[DailyTrendStat]

@router.get("", response_model=List[TransactionResponse])
def list_transactions(
    issuer: Optional[str] = Query(None, description="Filter by card issuer, e.g. HDFC, ICICI"),
    card_last4: Optional[str] = Query(None, description="Filter by card last 4 digits"),
    transaction_type: Optional[str] = Query(None, description="debit | credit | surcharge_waiver"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search merchant or notes"),
    needs_review: Optional[bool] = Query(None, description="Filter by needs_review status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Lists parsed transactions with optional filtering and pagination.
    """
    query = db.query(Transaction).filter(Transaction.status != "ignored")
    if issuer:
        query = query.filter(Transaction.issuer.ilike(f"%{issuer}%"))
    if card_last4:
        query = query.filter(Transaction.card_last4 == card_last4)
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    if category:
        query = query.filter(Transaction.category == category)
    if needs_review is not None:
        query = query.filter(Transaction.needs_review == needs_review)
    if search:
        s = f"%{search}%"
        query = query.filter(
            (Transaction.merchant_raw.ilike(s)) |
            (Transaction.merchant_clean.ilike(s)) |
            (Transaction.issuer.ilike(s)) |
            (Transaction.category.ilike(s))
        )

    query = query.order_by(Transaction.transacted_at_utc.desc())
    items = query.offset(offset).limit(limit).all()
    return [TransactionResponse.from_orm_model(t) for t in items]

@router.get("/summary", response_model=SummaryStatsResponse)
@router.get("/stats/summary", response_model=SummaryStatsResponse)
def get_summary_stats(db: Session = Depends(get_db)):
    """
    Returns high-density financial metrics, category breakdown, issuer breakdown, and trends.
    """
    from app.core.config import settings
    from sqlalchemy import func
    from collections import defaultdict

    all_txns = db.query(Transaction).filter(Transaction.status != "ignored").all()
    
    # Calculate net personal spend (my share) & total reimbursable group receivables
    total_personal_paise = sum(
        (t.my_share_paise if (t.is_split and t.my_share_paise is not None) else t.amount_paise)
        for t in all_txns if t.transaction_type == "debit"
    )
    reimbursable_paise = sum(
        (t.reimbursable_paise or 0)
        for t in all_txns if t.transaction_type == "debit"
    )

    total_spend_inr = round(total_personal_paise / 100.0, 2)
    net_receivables_inr = round(reimbursable_paise / 100.0, 2)
    unreviewed_count = sum(1 for t in all_txns if t.needs_review)

    # Category breakdown
    cat_amounts = defaultdict(float)
    cat_counts = defaultdict(int)
    for t in all_txns:
        if t.transaction_type == "debit":
            cat_name = t.category or "Uncategorized"
            my_share = (t.my_share_paise / 100.0) if (t.is_split and t.my_share_paise is not None) else (t.amount_paise / 100.0)
            cat_amounts[cat_name] += my_share
            cat_counts[cat_name] += 1

    category_breakdown = []
    for cat_name, amt in sorted(cat_amounts.items(), key=lambda x: x[1], reverse=True):
        pct = round((amt / total_spend_inr * 100.0), 1) if total_spend_inr > 0 else 0.0
        category_breakdown.append(CategoryStat(
            category=cat_name,
            amount_inr=round(amt, 2),
            percentage=pct,
            count=cat_counts[cat_name]
        ))

    # Issuer breakdown
    iss_amounts = defaultdict(float)
    iss_counts = defaultdict(int)
    for t in all_txns:
        if t.transaction_type == "debit":
            iss_name = t.issuer or "Other"
            my_share = (t.my_share_paise / 100.0) if (t.is_split and t.my_share_paise is not None) else (t.amount_paise / 100.0)
            iss_amounts[iss_name] += my_share
            iss_counts[iss_name] += 1

    issuer_breakdown = []
    for iss_name, amt in sorted(iss_amounts.items(), key=lambda x: x[1], reverse=True):
        issuer_breakdown.append(IssuerStat(
            issuer=iss_name,
            amount_inr=round(amt, 2),
            count=iss_counts[iss_name]
        ))

    # Daily trends (last 30 days)
    daily_amounts = defaultdict(float)
    for t in all_txns:
        if t.transaction_type == "debit" and t.transacted_at_utc:
            d_str = t.transacted_at_utc.strftime("%b %d")
            my_share = (t.my_share_paise / 100.0) if (t.is_split and t.my_share_paise is not None) else (t.amount_paise / 100.0)
            daily_amounts[d_str] += my_share

    daily_trends = [
        DailyTrendStat(date=d, amount_inr=round(a, 2))
        for d, a in list(daily_amounts.items())[-14:]
    ]

    return SummaryStatsResponse(
        app_title=settings.PROJECT_NAME,
        total_spend_inr=total_spend_inr,
        net_receivables_inr=net_receivables_inr,
        total_transactions_count=len(all_txns),
        unreviewed_count=unreviewed_count,
        category_breakdown=category_breakdown,
        issuer_breakdown=issuer_breakdown,
        daily_trends=daily_trends
    )

@router.get("/export/csv")
def export_transactions_csv(
    category: Optional[str] = Query(None),
    issuer: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Exports parsed transactions as a downloadable CSV file.
    """
    query = db.query(Transaction).filter(Transaction.status != "ignored")
    if category:
        query = query.filter(Transaction.category == category)
    if issuer:
        query = query.filter(Transaction.issuer.ilike(f"%{issuer}%"))

    items = query.order_by(Transaction.transacted_at_utc.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Transaction ID", "Date (UTC)", "Merchant Clean", "Merchant Raw",
        "Category", "Issuer", "Card Type", "Card Last4",
        "Transaction Type", "Amount (INR)", "Status"
    ])

    for t in items:
        writer.writerow([
            t.id,
            t.transacted_at_utc.isoformat() if t.transacted_at_utc else "",
            t.merchant_clean or "",
            t.merchant_raw or "",
            t.category or "Uncategorized",
            t.issuer,
            t.card_type,
            t.card_last4 or "",
            t.transaction_type,
            f"{(t.amount_paise / 100.0):.2f}",
            t.status
        ])

    output.seek(0)
    filename = f"AdultMoney_Export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

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

class SplitRequest(BaseModel):
    my_share_inr: float
    ratio_label: Optional[str] = None  # 1/2 | 1/3 | 1/4 | custom

@router.post("/{txn_id}/split", response_model=TransactionResponse)
def split_transaction(
    txn_id: int,
    payload: SplitRequest,
    db: Session = Depends(get_db)
):
    """
    Marks a transaction as split, setting your share and calculating reimbursable group outflow.
    """
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {txn_id} not found"
        )

    total_inr = txn.amount_paise / 100.0
    if payload.my_share_inr < 0 or payload.my_share_inr > total_inr:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"My share must be between 0 and total transaction amount ({total_inr} INR)"
        )

    my_share_paise = int(round(payload.my_share_inr * 100))
    reimbursable_paise = txn.amount_paise - my_share_paise

    txn.is_split = True
    txn.my_share_paise = my_share_paise
    txn.reimbursable_paise = reimbursable_paise
    txn.split_ratio_label = payload.ratio_label or "custom"
    txn.updated_at_utc = datetime.utcnow()

    db.commit()
    db.refresh(txn)
    return TransactionResponse.from_orm_model(txn)

@router.post("/{txn_id}/unsplit", response_model=TransactionResponse)
def unsplit_transaction(
    txn_id: int,
    db: Session = Depends(get_db)
):
    """
    Resets a transaction back to 100% personal expense.
    """
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {txn_id} not found"
        )

    txn.is_split = False
    txn.my_share_paise = None
    txn.reimbursable_paise = 0
    txn.split_ratio_label = None
    txn.updated_at_utc = datetime.utcnow()

    db.commit()
    db.refresh(txn)
    return TransactionResponse.from_orm_model(txn)
