from datetime import datetime
from app.models.transaction import Transaction

def test_custom_merchant_rule_flow(client):
    # 1. Create a dummy transaction
    txn = Transaction(
        source="sms",
        issuer="HDFC",
        card_type="credit",
        transaction_type="debit",
        amount_paise=150000,
        merchant_raw="Swiggy Instamart Order",
        merchant_clean="Swiggy Instamart",
        transacted_at_utc=datetime.utcnow(),
        needs_review=True,
        status="settled"
    )
    # Add via endpoint or DB
    res = client.post("/api/v1/rules/merchant", json={
        "pattern": "swiggy instamart",
        "category": "Groceries & Essentials"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["pattern"] == "swiggy instamart"
    assert data["category"] == "Groceries & Essentials"

    # List rules
    list_res = client.get("/api/v1/rules/merchant")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

def test_category_budget_flow(client):
    # 1. Set budget
    set_res = client.post("/api/v1/budgets", json={
        "category": "Dining",
        "budget_limit_inr": 10000.0
    })
    assert set_res.status_code == 200
    b_data = set_res.json()
    assert b_data["category"] == "Dining"
    assert b_data["budget_limit_inr"] == 10000.0
    assert "status" in b_data

    # 2. List budgets
    list_res = client.get("/api/v1/budgets")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

def test_csv_export_endpoint(client):
    res = client.get("/api/v1/transactions/export/csv")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert "Transaction ID" in res.text
