from datetime import datetime
from fastapi.testclient import TestClient
from app.models.raw_message import RawMessage
from app.models.transaction import Transaction
from app.models.merchant_rule import MerchantRule

def test_raw_messages_and_convert_endpoint(client: TestClient, db):
    # 1. Insert an unparsed raw SMS message
    raw = RawMessage(
        source="sms",
        sender="AD-NEWBNK",
        body="Alert: Rs 499.00 spent at UrbanCompany on card ending 8812.",
        idempotency_key="test_raw_unique_key_1",
        received_at_ms=1696123456789,
        device_id="test_dev",
        received_at_utc=datetime.utcnow()
    )
    db.add(raw)
    db.commit()
    db.refresh(raw)

    # 2. Query /api/v1/ingest/raw-messages
    res = client.get("/api/v1/ingest/raw-messages?unparsed_only=true")
    assert res.status_code == 200
    data = res.json()
    assert any(m["id"] == raw.id and m["is_parsed"] is False for m in data)

    # 3. Convert raw message to transaction
    convert_payload = {
        "amount_inr": 499.0,
        "merchant": "UrbanCompany",
        "category": "Services",
        "transaction_type": "debit"
    }
    conv_res = client.post(f"/api/v1/ingest/convert-raw/{raw.id}", json=convert_payload)
    assert conv_res.status_code == 200
    conv_data = conv_res.json()
    assert conv_data["merchant"] == "UrbanCompany"
    assert conv_data["amount_inr"] == 499.0
    assert conv_data["category"] == "Services"

    # 4. Verify transaction exists and merchant rule created
    txn = db.query(Transaction).filter(Transaction.raw_message_id == raw.id).first()
    assert txn is not None
    assert txn.amount_paise == 49900
    assert txn.merchant_clean == "UrbanCompany"

    rule = db.query(MerchantRule).filter(MerchantRule.pattern == "urbancompany").first()
    assert rule is not None
    assert rule.category == "Services"
