from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.merchant_rule import MerchantRule
from app.models.transaction import Transaction

router = APIRouter()

class MerchantRuleRequest(BaseModel):
    pattern: Optional[str] = None
    merchant_pattern: Optional[str] = None
    category: Optional[str] = None
    target_category: Optional[str] = None

    @property
    def rule_pattern(self) -> str:
        return self.merchant_pattern or self.pattern or ""

    @property
    def rule_category(self) -> str:
        return self.target_category or self.category or ""

class MerchantRuleResponse(BaseModel):
    id: int
    pattern: str
    merchant_pattern: str
    category: str
    target_category: str
    is_user_defined: bool
    confidence: float
    created_at_utc: datetime
    updated_at_utc: datetime

    class Config:
        from_attributes = True

@router.get("/merchant", response_model=List[MerchantRuleResponse])
def list_merchant_rules(db: Session = Depends(get_db)):
    """
    Lists all active custom merchant categorization rules.
    """
    rules = db.query(MerchantRule).order_by(MerchantRule.updated_at_utc.desc()).all()
    return [
        MerchantRuleResponse(
            id=r.id,
            pattern=r.pattern,
            merchant_pattern=r.pattern,
            category=r.category,
            target_category=r.category,
            is_user_defined=r.is_user_defined,
            confidence=r.confidence,
            created_at_utc=r.created_at_utc,
            updated_at_utc=r.updated_at_utc
        )
        for r in rules
    ]

@router.post("/merchant", response_model=MerchantRuleResponse)
def create_or_update_merchant_rule(
    payload: MerchantRuleRequest,
    db: Session = Depends(get_db)
):
    """
    Creates or updates a custom merchant rule and cascades the category to all matching transactions.
    """
    clean_pattern = payload.rule_pattern.strip().lower()
    target_cat = payload.rule_category.strip()

    if not clean_pattern or not target_cat:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pattern and category are required"
        )

    rule = db.query(MerchantRule).filter(MerchantRule.pattern == clean_pattern).first()
    if rule:
        rule.category = target_cat
        rule.is_user_defined = True
        rule.confidence = 1.0
        rule.updated_at_utc = datetime.utcnow()
    else:
        rule = MerchantRule(
            pattern=clean_pattern,
            category=target_cat,
            is_user_defined=True,
            confidence=1.0,
            created_at_utc=datetime.utcnow(),
            updated_at_utc=datetime.utcnow()
        )
        db.add(rule)

    # Cascade to all past transactions matching this pattern
    matching_txns = db.query(Transaction).filter(
        Transaction.status != "ignored"
    ).all()

    for txn in matching_txns:
        merchant_str = (txn.merchant_clean or txn.merchant_raw or "").lower()
        if clean_pattern in merchant_str:
            txn.category = target_cat
            txn.needs_review = False
            txn.review_source = "user_rule_cascade"

    db.commit()
    db.refresh(rule)
    return MerchantRuleResponse(
        id=rule.id,
        pattern=rule.pattern,
        merchant_pattern=rule.pattern,
        category=rule.category,
        target_category=rule.category,
        is_user_defined=rule.is_user_defined,
        confidence=rule.confidence,
        created_at_utc=rule.created_at_utc,
        updated_at_utc=rule.updated_at_utc
    )

@router.delete("/merchant/{rule_id}")
def delete_merchant_rule(rule_id: int, db: Session = Depends(get_db)):
    """
    Deletes a merchant rule.
    """
    rule = db.query(MerchantRule).filter(MerchantRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    db.delete(rule)
    db.commit()
    return {"status": "success", "message": f"Rule {rule_id} deleted"}
