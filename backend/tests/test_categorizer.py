import json
import time
from datetime import datetime
from app.core.config import settings
from app.core.security import calculate_hmac_signature, compute_idempotency_key
from app.categorizer.catalog import match_catalog_category
from app.categorizer.engine import categorize_transaction
from app.categorizer.service import learn_and_categorize
from app.models.merchant_rule import MerchantRule
from app.models.transaction import Transaction

def test_catalog_matching():
    assert match_catalog_category("Zomato") == "Food & Dining"
    assert match_catalog_category("Swiggy") == "Food & Dining"
    assert match_catalog_category("Blue Tokai Coffee") == "Food & Dining"
    assert match_catalog_category("Blinkit") == "Groceries & Essentials"
    assert match_catalog_category("Amazon") == "Shopping & E-Commerce"
    assert match_catalog_category("Reliance Digital") == "Shopping & E-Commerce"
    assert match_catalog_category("Indian Oil Corp") == "Fuel"
    assert match_catalog_category("Uber") == "Travel & Commute"
    assert match_catalog_category("Unknown Random Shop") is None

def test_categorize_transaction_engine(db):
    # 1. Override hint takes priority
    res1 = categorize_transaction(db, merchant="Shell", transaction_type="surcharge_waiver", category_override="Fuel")
    assert res1.category == "Fuel"
    assert res1.needs_review is False

    # 2. Credit bill payment -> Transfers
    res2 = categorize_transaction(db, merchant="HDFC Bank", transaction_type="credit")
    assert res2.category == "Transfers"
    assert res2.needs_review is False

    # 3. Known catalog merchant -> Auto-categorized
    res3 = categorize_transaction(db, merchant="Starbucks", transaction_type="debit")
    assert res3.category == "Food & Dining"
    assert res3.needs_review is False

    # 4. Unknown merchant -> Flagged for review
    res4 = categorize_transaction(db, merchant="Apex Engineering Services", transaction_type="debit")
    assert res4.category == "Uncategorized"
    assert res4.needs_review is True

def test_learn_and_cascade_rule(db):
    # Insert two transactions with the same unreviewed merchant
    now_utc = datetime.utcnow()
    t1 = Transaction(
        issuer="Axis",
        card_type="credit",
        card_last4="9456",
        transaction_type="debit",
        amount_paise=50000,
        currency="INR",
        merchant_clean="Kerala Store",
        category="Uncategorized",
        needs_review=True,
        transacted_at_utc=now_utc
    )
    t2 = Transaction(
        issuer="Axis",
        card_type="credit",
        card_last4="9456",
        transaction_type="debit",
        amount_paise=75000,
        currency="INR",
        merchant_clean="Kerala Store",
        category="Uncategorized",
        needs_review=True,
        transacted_at_utc=now_utc
    )
    db.add(t1)
    db.add(t2)
    db.commit()

    # User reviews and categorizes t1 as "Groceries & Essentials"
    updated_t1 = learn_and_categorize(db, txn_id=t1.id, category="Groceries & Essentials")
    assert updated_t1.category == "Groceries & Essentials"
    assert updated_t1.needs_review is False

    # Verify merchant rule was learned
    rule = db.query(MerchantRule).filter(MerchantRule.pattern == "kerala store").first()
    assert rule is not None
    assert rule.category == "Groceries & Essentials"

    # Verify t2 was automatically cascaded and marked reviewed
    db.refresh(t2)
    assert t2.category == "Groceries & Essentials"
    assert t2.needs_review is False
    assert t2.review_source == "learned_cascade"

def test_unreviewed_and_categorize_api(client):
    now_ts = int(time.time())
    # Ingest an SMS from an uncataloged merchant
    body = "INR 1,250.00 spent on Axis IOCL Card ending 1122 at Apex Engineering on 29-09-2026."
    idempotency_key = compute_idempotency_key("AXISBK", body, now_ts * 1000)
    payload = {
        "idempotency_key": idempotency_key,
        "source": "sms",
        "sender": "AXISBK",
        "body": body,
        "received_at_ms": now_ts * 1000,
        "device_tz": "Asia/Kolkata"
    }
    raw_body = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    sig = calculate_hmac_signature(settings.BOOTSTRAP_DEVICE_SECRET, str(now_ts), raw_body)
    headers = {
        "X-Device-Id": settings.BOOTSTRAP_DEVICE_ID,
        "X-Timestamp": str(now_ts),
        "X-Signature": sig,
        "Content-Type": "application/json"
    }
    res = client.post("/api/v1/ingest", content=raw_body, headers=headers)
    assert res.status_code == 200
    txn_id = res.json()["parsed_transaction_id"]

    # 1. Fetch unreviewed transactions
    unreviewed_res = client.get("/api/v1/categories/unreviewed")
    assert unreviewed_res.status_code == 200
    unreviewed_items = unreviewed_res.json()
    assert any(item["id"] == txn_id for item in unreviewed_items)

    # 2. 1-tap categorize
    cat_res = client.post(
        f"/api/v1/categories/{txn_id}/categorize",
        json={"category": "Services & Repairs"}
    )
    assert cat_res.status_code == 200
    cat_data = cat_res.json()
    assert cat_data["transaction"]["category"] == "Services & Repairs"

    # 3. Verify it is no longer in unreviewed list
    unreviewed_after = client.get("/api/v1/categories/unreviewed").json()
    assert not any(item["id"] == txn_id for item in unreviewed_after)
