from typing import Optional, NamedTuple
from sqlalchemy.orm import Session

from app.models.merchant_rule import MerchantRule
from app.categorizer.catalog import match_catalog_category

class CategorizationResult(NamedTuple):
    category: str
    confidence: float
    needs_review: bool

def categorize_transaction(
    db: Session,
    merchant: Optional[str],
    transaction_type: str,
    category_override: Optional[str] = None
) -> CategorizationResult:
    """
    Multi-tier zero-friction auto-categorization algorithm:
    1. Template category override (e.g. Fuel waiver, Cashback) -> 100% confidence, silent.
    2. Credit / bill payments -> Transfers & Payments, 100% confidence, silent.
    3. Learned user merchant memory in SQLite -> 100% confidence, silent.
    4. Curated Indian merchant catalog matching -> 90% confidence, silent.
    5. Ambiguous merchant -> Uncategorized, 0% confidence, needs_review = True.
    """
    # 1. Template-level category override (ignore if None or placeholder 'Uncategorized')
    if category_override and category_override != "Uncategorized":
        return CategorizationResult(
            category=category_override,
            confidence=1.0,
            needs_review=False
        )

    # 2. Credit or payment received without specific merchant
    if transaction_type == "credit" and (not merchant or any(k in merchant.lower() for k in ["bank", "payment", "card", "online"])):
        return CategorizationResult(
            category="Transfers & Payments",
            confidence=1.0,
            needs_review=False
        )

    if not merchant:
        return CategorizationResult(
            category="Uncategorized",
            confidence=0.0,
            needs_review=True
        )

    norm_merchant = merchant.strip().lower()

    # 3. Check learned merchant rules in database
    # Check exact match or substring match
    rule = db.query(MerchantRule).filter(
        (MerchantRule.pattern == norm_merchant) |
        (MerchantRule.pattern.ilike(f"%{norm_merchant}%"))
    ).first()

    if rule:
        return CategorizationResult(
            category=rule.category,
            confidence=rule.confidence,
            needs_review=False
        )

    # 4. Check curated merchant catalog
    matched = match_catalog_category(merchant)
    if matched:
        return CategorizationResult(
            category=matched,
            confidence=0.9,
            needs_review=False
        )

    # 5. Unknown merchant -> Flag for quick 1-tap review
    return CategorizationResult(
        category="Uncategorized",
        confidence=0.0,
        needs_review=True
    )
