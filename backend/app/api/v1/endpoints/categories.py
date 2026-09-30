from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.transaction import Transaction
from app.api.v1.endpoints.transactions import TransactionResponse
from app.categorizer.catalog import MERCHANT_CATEGORY_CATALOG
from app.categorizer.service import (
    learn_and_categorize,
    categorize_all_transactions,
)

router = APIRouter()

class CategorizeRequest(BaseModel):
    category: str

class CategorizeResponse(BaseModel):
    transaction: TransactionResponse
    learned_rule_pattern: Optional[str]
    message: str

class BatchCategorizeResponse(BaseModel):
    total: int
    auto_categorized: int
    needs_review: int

@router.get("/catalog", response_model=List[str])
def get_category_catalog():
    """
    Returns list of all available standard categories.
    """
    categories = list(MERCHANT_CATEGORY_CATALOG.keys())
    if "Other" not in categories:
        categories.append("Other")
    return categories

@router.get("/unreviewed", response_model=List[TransactionResponse])
def get_unreviewed_transactions(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Fetches only ambiguous transactions requiring quick 1-tap user review.
    """
    items = db.query(Transaction).filter(
        Transaction.needs_review == True
    ).order_by(Transaction.transacted_at_utc.desc()).limit(limit).all()
    return [TransactionResponse.from_orm_model(t) for t in items]

@router.post("/{txn_id}/categorize", response_model=CategorizeResponse)
def submit_category(
    txn_id: int,
    payload: CategorizeRequest,
    db: Session = Depends(get_db)
):
    """
    1-tap category assignment for an ambiguous transaction:
    - Sets transaction category and removes from review queue.
    - Saves merchant into long-term memory so future expenses from this merchant are silent.
    - Cascades category to any other pending transactions matching this merchant.
    """
    txn = learn_and_categorize(db, txn_id, payload.category, review_source="user")
    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with id {txn_id} not found"
        )

    return CategorizeResponse(
        transaction=TransactionResponse.from_orm_model(txn),
        learned_rule_pattern=txn.merchant_clean.lower() if txn.merchant_clean else None,
        message=f"Categorized as '{payload.category}'. Merchant memory updated."
    )

@router.post("/batch-run", response_model=BatchCategorizeResponse)
def batch_categorize_all(db: Session = Depends(get_db)):
    """
    Runs multi-tier auto-categorizer across all stored transactions in database.
    """
    stats = categorize_all_transactions(db)
    return BatchCategorizeResponse(**stats)
