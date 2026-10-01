from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.transaction import Transaction

router = APIRouter()

class MonthlyTotalStat(BaseModel):
    month_key: str  # YYYY-MM
    month_label: str  # e.g., "Oct 2026"
    total_spend_inr: float
    transaction_count: int
    top_category: str
    mom_change_pct: Optional[float] = None

class CategoryMonthlyStat(BaseModel):
    category: str
    amount_inr: float
    percentage: float

class MonthlyCategoryMatrix(BaseModel):
    month_key: str
    month_label: str
    categories: List[CategoryMonthlyStat]

class OverallCategoryStat(BaseModel):
    category: str
    amount_inr: float
    percentage: float
    color_hex: str

class AnalyticsTrendsResponse(BaseModel):
    cumulative_spend_inr: float
    avg_monthly_spend_inr: float
    peak_month_label: str
    peak_month_spend_inr: float
    total_months_count: int
    monthly_totals: List[MonthlyTotalStat]
    monthly_matrix: List[MonthlyCategoryMatrix]
    overall_category_distribution: List[OverallCategoryStat]
    insights: List[str]

CATEGORY_COLORS = [
    "#38BDF8",  # Sky blue
    "#34D399",  # Emerald green
    "#F59E0B",  # Amber
    "#EC4899",  # Pink
    "#A855F7",  # Purple
    "#6366F1",  # Indigo
    "#F43F5E",  # Rose
    "#0EA5E9",  # Ocean blue
    "#10B981",  # Mint
    "#8B5CF6",  # Violet
]

@router.get("/monthly-trends", response_model=AnalyticsTrendsResponse)
def get_monthly_trends(db: Session = Depends(get_db)):
    """
    Returns monthly spending trends, category distributions over time, and spending insights.
    """
    txns = db.query(Transaction).filter(
        Transaction.status != "ignored",
        Transaction.transaction_type == "debit"
    ).order_by(Transaction.transacted_at_utc.asc()).all()

    if not txns:
        return AnalyticsTrendsResponse(
            cumulative_spend_inr=0.0,
            avg_monthly_spend_inr=0.0,
            peak_month_label="N/A",
            peak_month_spend_inr=0.0,
            total_months_count=0,
            monthly_totals=[],
            monthly_matrix=[],
            overall_category_distribution=[],
            insights=["No transaction data available yet."]
        )

    # Group spending by month and category
    monthly_spends = defaultdict(float)  # month_key -> total_inr
    monthly_counts = defaultdict(int)    # month_key -> count
    monthly_cat_spends = defaultdict(lambda: defaultdict(float))  # month_key -> cat -> inr
    overall_cat_spends = defaultdict(float)  # cat -> total_inr
    cumulative_spend = 0.0

    for t in txns:
        dt = t.transacted_at_utc
        month_key = dt.strftime("%Y-%m")
        amount = t.amount_paise / 100.0
        cat = t.category or "Uncategorized"

        monthly_spends[month_key] += amount
        monthly_counts[month_key] += 1
        monthly_cat_spends[month_key][cat] += amount
        overall_cat_spends[cat] += amount
        cumulative_spend += amount

    sorted_months = sorted(monthly_spends.keys())
    monthly_totals_list = []
    prev_total = None

    for m_key in sorted_months:
        dt_obj = datetime.strptime(m_key, "%Y-%m")
        m_label = dt_obj.strftime("%b %Y")
        m_total = round(monthly_spends[m_key], 2)
        m_count = monthly_counts[m_key]

        # Find top category for this month
        top_cat = "N/A"
        top_cat_amt = 0.0
        for c_name, c_amt in monthly_cat_spends[m_key].items():
            if c_amt > top_cat_amt:
                top_cat_amt = c_amt
                top_cat = c_name

        mom_change = None
        if prev_total is not None and prev_total > 0:
            mom_change = round(((m_total - prev_total) / prev_total) * 100.0, 1)

        monthly_totals_list.append(MonthlyTotalStat(
            month_key=m_key,
            month_label=m_label,
            total_spend_inr=m_total,
            transaction_count=m_count,
            top_category=top_cat,
            mom_change_pct=mom_change
        ))
        prev_total = m_total

    # Category monthly matrix
    monthly_matrix_list = []
    for m_key in sorted_months:
        dt_obj = datetime.strptime(m_key, "%Y-%m")
        m_label = dt_obj.strftime("%b %Y")
        m_total = monthly_spends[m_key]
        
        cat_stats = []
        for cat_name, cat_amt in sorted(monthly_cat_spends[m_key].items(), key=lambda x: x[1], reverse=True):
            pct = round((cat_amt / m_total * 100.0), 1) if m_total > 0 else 0.0
            cat_stats.append(CategoryMonthlyStat(
                category=cat_name,
                amount_inr=round(cat_amt, 2),
                percentage=pct
            ))
        monthly_matrix_list.append(MonthlyCategoryMatrix(
            month_key=m_key,
            month_label=m_label,
            categories=cat_stats
        ))

    # Overall Category Distribution
    overall_cat_list = []
    sorted_overall_cats = sorted(overall_cat_spends.items(), key=lambda x: x[1], reverse=True)
    for idx, (cat_name, cat_amt) in enumerate(sorted_overall_cats):
        pct = round((cat_amt / cumulative_spend * 100.0), 1) if cumulative_spend > 0 else 0.0
        color = CATEGORY_COLORS[idx % len(CATEGORY_COLORS)]
        overall_cat_list.append(OverallCategoryStat(
            category=cat_name,
            amount_inr=round(cat_amt, 2),
            percentage=pct,
            color_hex=color
        ))

    # General KPI Metrics
    total_months = len(sorted_months)
    avg_monthly_spend = round(cumulative_spend / total_months, 2) if total_months > 0 else 0.0
    
    peak_month = max(monthly_totals_list, key=lambda x: x.total_spend_inr) if monthly_totals_list else None
    peak_month_label = peak_month.month_label if peak_month else "N/A"
    peak_month_spend = peak_month.total_spend_inr if peak_month else 0.0

    # Insights Generation
    insights = []
    if peak_month:
        insights.append(f"Highest spending month: {peak_month.month_label} (₹{peak_month.total_spend_inr:,.0f}).")
    if overall_cat_list:
        top_overall = overall_cat_list[0]
        insights.append(f"Top overall spending category: {top_overall.category} accounting for {top_overall.percentage}% (₹{top_overall.amount_inr:,.0f}).")
    if len(monthly_totals_list) >= 2:
        latest = monthly_totals_list[-1]
        if latest.mom_change_pct is not None:
            direction = "increased" if latest.mom_change_pct >= 0 else "decreased"
            insights.append(f"Spending in {latest.month_label} {direction} by {abs(latest.mom_change_pct)}% compared to prior month.")
    insights.append(f"Average monthly outflow across {total_months} month(s) is ₹{avg_monthly_spend:,.0f}.")

    return AnalyticsTrendsResponse(
        cumulative_spend_inr=round(cumulative_spend, 2),
        avg_monthly_spend_inr=avg_monthly_spend,
        peak_month_label=peak_month_label,
        peak_month_spend_inr=peak_month_spend,
        total_months_count=total_months,
        monthly_totals=monthly_totals_list,
        monthly_matrix=monthly_matrix_list,
        overall_category_distribution=overall_cat_list,
        insights=insights
    )
