import json
import time
from app.core.config import settings
from app.core.security import calculate_hmac_signature, compute_idempotency_key

def _send_signed_ingest(client, sender: str, body: str, received_ms: int):
    now_ts = int(time.time())
    idempotency_key = compute_idempotency_key(sender, body, received_ms)
    payload = {
        "idempotency_key": idempotency_key,
        "source": "sms",
        "sender": sender,
        "body": body,
        "received_at_ms": received_ms,
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
    return client.post("/api/v1/ingest", content=raw_body, headers=headers)

def test_list_templates(client):
    response = client.get("/api/v1/parser/templates")
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) >= 7
    issuers = {t["issuer"] for t in templates}
    assert "HDFC" in issuers
    assert "ICICI" in issuers
    assert "SBI" in issuers
    assert "Axis" in issuers

def test_test_parse_endpoint(client):
    payload = {
        "sender": "VK-HDFCBK",
        "body": "Rs 1,840.00 spent on HDFC Bank Credit Card x4321 at ZOMATO on 29-09-2026. Avl Lmt: Rs 1,42,160.00"
    }
    response = client.post("/api/v1/parser/test", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data is not None
    assert data["amount_paise"] == 184000
    assert data["card_last4"] == "4321"
    assert data["merchant_clean"] == "Zomato"
    assert data["issuer"] == "HDFC"
    assert data["transaction_type"] == "debit"

def test_ingest_auto_creates_transaction(client):
    now_ts = int(time.time())
    received_ms = now_ts * 1000
    sender = "AD-ICICIB"
    body = "Dear Customer, INR 320.00 debited from ICICI Bank Card XX8910 at BLUE TOKAI COFFEE."
    
    res = _send_signed_ingest(client, sender, body, received_ms)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "stored"
    assert data["parsed_transaction_id"] is not None

    txn_id = data["parsed_transaction_id"]
    # Fetch transaction from API
    txn_res = client.get(f"/api/v1/transactions/{txn_id}")
    assert txn_res.status_code == 200
    txn = txn_res.json()
    assert txn["amount_paise"] == 32000
    assert txn["amount_inr"] == 320.0
    assert txn["card_last4"] == "8910"
    assert txn["merchant_clean"] == "Blue Tokai Coffee"
    assert txn["issuer"] == "ICICI"

def test_filter_transactions(client):
    now_ts = int(time.time())
    # Ingest an ICICI transaction first
    _send_signed_ingest(
        client,
        sender="AD-ICICIB",
        body="Dear Customer, INR 320.00 debited from ICICI Bank Card XX8910 at BLUE TOKAI COFFEE.",
        received_ms=now_ts * 1000
    )
    # Ingest an HDFC transaction
    _send_signed_ingest(
        client,
        sender="VK-HDFCBK",
        body="Rs 1,840.00 spent on HDFC Bank Credit Card x4321 at ZOMATO on 29-09-2026. Avl Lmt: Rs 1,42,160.00",
        received_ms=(now_ts - 50) * 1000
    )

    # Filter by issuer ICICI
    res = client.get("/api/v1/transactions?issuer=ICICI")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["issuer"] == "ICICI"
    assert items[0]["card_last4"] == "8910"

    # Filter by card_last4 4321
    res_hdfc = client.get("/api/v1/transactions?card_last4=4321")
    assert res_hdfc.status_code == 200
    items_hdfc = res_hdfc.json()
    assert len(items_hdfc) == 1
    assert items_hdfc[0]["issuer"] == "HDFC"

def test_reparse_endpoint(client):
    now_ts = int(time.time())
    # Ingest a message
    _send_signed_ingest(
        client,
        sender="VK-HDFCBK",
        body="Rs 1,840.00 spent on HDFC Bank Credit Card x4321 at ZOMATO on 29-09-2026. Avl Lmt: Rs 1,42,160.00",
        received_ms=now_ts * 1000
    )

    # Trigger reparse
    res = client.post("/api/v1/parser/reparse")
    assert res.status_code == 200
    stats = res.json()
    assert stats["total_raw"] >= 1
    assert stats["template_parsed"] >= 1
    assert stats["unparsed"] == 0
