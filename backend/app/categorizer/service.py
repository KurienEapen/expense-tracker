from datetime import datetime
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.models.merchant_rule import MerchantRule
from app.models.transaction import Transaction
from app.categorizer.engine import categorize_transaction

def apply_categorization_to_transaction(db: Session, txn: Transaction) -> bool:
    """
    Applies categorizer to a single transaction.
    """
    res = categorize_transaction(
        db=db,
        merchant=txn.merchant_clean,
        transaction_type=txn.transaction_type,
        category_override=txn.category
    )
    txn.category = res.category
    txn.needs_review = res.needs_review
    if not res.needs_review:
        txn.review_source = "auto"
        txn.reviewed_at_utc = datetime.utcnow()
    return not res.needs_review

def learn_and_categorize(
    db: Session,
    txn_id: int,
    category: str,
    review_source: str = "user"
) -> Optional[Transaction]:
    """
    Saves user-selected category for a transaction, marks it reviewed,
    persists a learned rule in merchant_rules memory, and cascades
    the new category to any other pending transactions with the same merchant!
    """
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        return None

    txn.category = category
    txn.needs_review = False
    txn.review_source = review_source
    txn.reviewed_at_utc = datetime.utcnow()

    # Learn merchant memory rule if clean merchant is known
    if txn.merchant_clean:
        pattern = txn.merchant_clean.strip().lower()
        existing_rule = db.query(MerchantRule).filter(MerchantRule.pattern == pattern).first()
        if existing_rule:
            existing_rule.category = category
            existing_rule.updated_at_utc = datetime.utcnow()
        else:
            new_rule = MerchantRule(
                pattern=pattern,
                category=category,
                is_user_defined=True,
                confidence=1.0,
                created_at_utc=datetime.utcnow()
            )
            db.add(new_rule)

        # Cascade rule to any other uncategorized transactions with the same merchant
        other_txns = db.query(Transaction).filter(
            Transaction.merchant_clean.ilike(txn.merchant_clean),
            Transaction.needs_review == True
        ).all()
        for other in other_txns:
            other.category = category
            other.needs_review = False
            other.review_source = "learned_cascade"
            other.reviewed_at_utc = datetime.utcnow()

    db.commit()
    db.refresh(txn)
    return txn

def categorize_all_transactions(db: Session) -> Dict[str, int]:
    """
    Runs auto-categorizer across all stored transactions in database.
    """
    transactions = db.query(Transaction).all()
    total = len(transactions)
    auto_count = 0
    review_count = 0

    for txn in transactions:
        auto = apply_categorization_to_transaction(db, txn)
        if auto:
            auto_count += 1
        else:
            review_count += 1

    db.commit()
    return {
        "total": total,
        "auto_categorized": auto_count,
        "needs_review": review_count,
    }
