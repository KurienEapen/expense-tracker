from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.category_budget import CategoryBudget
from app.models.transaction import Transaction

router = APIRouter()

class CategoryBudgetRequest(BaseModel):
    category: str
    monthly_budget_inr: Optional[float] = None
    budget_limit_inr: Optional[float] = None

    @property
    def limit_inr(self) -> float:
        if self.monthly_budget_inr is not None:
            return self.monthly_budget_inr
        if self.budget_limit_inr is not None:
            return self.budget_limit_inr
        return 0.0

class CategoryBudgetResponse(BaseModel):
    id: int
    category: str
    monthly_budget_inr: float
    budget_limit_inr: float
    current_spent_inr: float
    spent_inr: float
    remaining_inr: float
    percentage: float
    status: str  # 'healthy' | 'warning' (>=80%) | 'exceeded' (>=100%)
    created_at_utc: datetime

@router.get("", response_model=List[CategoryBudgetResponse])
def list_category_budgets(db: Session = Depends(get_db)):
    """
    Lists category budgets with live spending totals, progress percentages, and alert statuses.
    """
    budgets = db.query(CategoryBudget).filter(CategoryBudget.is_active == True).all()
    all_txns = db.query(Transaction).filter(
        Transaction.status != "ignored",
        Transaction.transaction_type == "debit"
    ).all()

    # Aggregate spending per category
    spent_by_cat = {}
    for t in all_txns:
        cat_name = t.category or "Uncategorized"
        spent_by_cat[cat_name] = spent_by_cat.get(cat_name, 0.0) + (t.amount_paise / 100.0)

    result = []
    for b in budgets:
        limit_inr = b.budget_limit_paise / 100.0
        current_spent = round(spent_by_cat.get(b.category, 0.0), 2)
        remaining = round(max(0.0, limit_inr - current_spent), 2)
        pct = round((current_spent / limit_inr * 100.0), 1) if limit_inr > 0 else 0.0

        if pct >= 100.0:
            budget_status = "exceeded"
        elif pct >= 80.0:
            budget_status = "warning"
        else:
            budget_status = "healthy"

        result.append(CategoryBudgetResponse(
            id=b.id,
            category=b.category,
            monthly_budget_inr=limit_inr,
            budget_limit_inr=limit_inr,
            current_spent_inr=current_spent,
            spent_inr=current_spent,
            remaining_inr=remaining,
            percentage=pct,
            status=budget_status,
            created_at_utc=b.created_at_utc
        ))

    return result

@router.post("", response_model=CategoryBudgetResponse)
def set_category_budget(
    payload: CategoryBudgetRequest,
    db: Session = Depends(get_db)
):
    """
    Sets or updates a monthly budget limit for a category.
    """
    limit_val = payload.limit_inr
    if limit_val <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Budget limit must be greater than 0"
        )

    limit_paise = int(round(limit_val * 100))
    existing = db.query(CategoryBudget).filter(CategoryBudget.category == payload.category).first()

    if existing:
        existing.budget_limit_paise = limit_paise
        existing.is_active = True
        existing.updated_at_utc = datetime.utcnow()
        budget = existing
    else:
        budget = CategoryBudget(
            category=payload.category,
            budget_limit_paise=limit_paise,
            is_active=True,
            created_at_utc=datetime.utcnow(),
            updated_at_utc=datetime.utcnow()
        )
        db.add(budget)

    db.commit()
    db.refresh(budget)

    # Calculate current spending
    spent = db.query(Transaction).filter(
        Transaction.category == payload.category,
        Transaction.status != "ignored",
        Transaction.transaction_type == "debit"
    ).all()

    current_spent = round(sum(t.amount_paise for t in spent) / 100.0, 2)
    remaining = round(max(0.0, limit_val - current_spent), 2)
    pct = round((current_spent / limit_val * 100.0), 1) if limit_val > 0 else 0.0

    b_status = "exceeded" if pct >= 100.0 else ("warning" if pct >= 80.0 else "healthy")

    return CategoryBudgetResponse(
        id=budget.id,
        category=budget.category,
        monthly_budget_inr=limit_val,
        budget_limit_inr=limit_val,
        current_spent_inr=current_spent,
        spent_inr=current_spent,
        remaining_inr=remaining,
        percentage=pct,
        status=b_status,
        created_at_utc=budget.created_at_utc
    )

@router.delete("/{budget_id}")
def delete_category_budget(budget_id: int, db: Session = Depends(get_db)):
    """
    Deactivates a category budget.
    """
    budget = db.query(CategoryBudget).filter(CategoryBudget.id == budget_id).first()
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget {budget_id} not found"
        )
    budget.is_active = False
    db.commit()
    return {"status": "success", "message": f"Budget {budget_id} removed"}
