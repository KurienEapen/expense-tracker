from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.transaction import Transaction

client = TestClient(app)

def test_monthly_trends_analytics_endpoint(db: Session):
    # Seed mock debit transactions across two different months
    t1 = Transaction(
        source="sms_ingest",
        issuer="HDFC",
        card_type="credit_card",
        transaction_type="debit",
        amount_paise=250000,  # ₹2500
        currency="INR",
        merchant_raw="SWIGGY BANGALORE",
        merchant_clean="Swiggy",
        category="Food & Dining",
        transacted_at_utc=datetime(2026, 9, 15, 12, 0, 0),
        status="parsed"
    )
    t2 = Transaction(
        source="sms_ingest",
        issuer="ICICI",
        card_type="credit_card",
        transaction_type="debit",
        amount_paise=500000,  # ₹5000
        currency="INR",
        merchant_raw="AMAZON INDIA",
        merchant_clean="Amazon",
        category="Shopping & E-Commerce",
        transacted_at_utc=datetime(2026, 9, 20, 15, 0, 0),
        status="parsed"
    )
    t3 = Transaction(
        source="sms_ingest",
        issuer="HDFC",
        card_type="credit_card",
        transaction_type="debit",
        amount_paise=400000,  # ₹4000
        currency="INR",
        merchant_raw="SWIGGY BANGALORE",
        merchant_clean="Swiggy",
        category="Food & Dining",
        transacted_at_utc=datetime(2026, 10, 1, 10, 0, 0),
        status="parsed"
    )

    db.add_all([t1, t2, t3])
    db.commit()

    response = client.get("/api/v1/analytics/monthly-trends")
    assert response.status_code == 200
    data = response.json()

    assert "cumulative_spend_inr" in data
    assert data["cumulative_spend_inr"] >= 11500.0
    assert len(data["monthly_totals"]) >= 2

    # Check overall category distribution
    assert len(data["overall_category_distribution"]) > 0

    # Insights exist
    assert len(data["insights"]) > 0
