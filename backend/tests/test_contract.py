import json
import time
from app.core.config import settings
from app.core.security import calculate_hmac_signature, compute_idempotency_key

def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "ok"

def test_ingest_valid_signed_message(client):
    now_ts = int(time.time())
    received_ms = now_ts * 1000
    sender = "HDFCBK"
    body = "Rs 1,250.00 spent on HDFC Bank Card x1234 at SWIGGY on 29-09-2026. Avl Lmt: Rs 1,45,000.00"
    
    idempotency_key = compute_idempotency_key(sender, body, received_ms)
    
    payload = {
        "idempotency_key": idempotency_key,
        "source": "sms",
        "sender": sender,
        "app_package": None,
        "body": body,
        "received_at_ms": received_ms,
        "device_tz": "Asia/Kolkata",
        "location": {"lat": 12.9716, "lon": 77.5946, "accuracy_m": 15.0, "fix_age_s": 20},
        "ocr_confidence": None,
        "app_version": "0.1.0"
    }
    
    raw_body = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    sig = calculate_hmac_signature(settings.BOOTSTRAP_DEVICE_SECRET, str(now_ts), raw_body)
    
    headers = {
        "X-Device-Id": settings.BOOTSTRAP_DEVICE_ID,
        "X-Timestamp": str(now_ts),
        "X-Signature": sig,
        "Content-Type": "application/json"
    }
    
    response = client.post("/api/v1/ingest", content=raw_body, headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "stored"
    assert data["raw_id"] is not None

def test_ingest_duplicate_idempotency_returns_duplicate_status(client):
    now_ts = int(time.time())
    received_ms = now_ts * 1000
    sender = "ICICIB"
    body = "Dear Customer, INR 550.00 debited from ICICI Bank Card XX5678 at STARBUCKS."
    
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
    
    # First ingest -> stored
    res1 = client.post("/api/v1/ingest", content=raw_body, headers=headers)
    assert res1.status_code == 200
    assert res1.json()["status"] == "stored"
    raw_id = res1.json()["raw_id"]
    
    # Second ingest -> duplicate (with same raw_id)
    res2 = client.post("/api/v1/ingest", content=raw_body, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["status"] == "duplicate"
    assert res2.json()["raw_id"] == raw_id

def test_ingest_rejects_invalid_signature(client):
    now_ts = int(time.time())
    payload = {
        "idempotency_key": "some_key",
        "source": "sms",
        "sender": "HDFCBK",
        "body": "Test message",
        "received_at_ms": now_ts * 1000
    }
    raw_body = json.dumps(payload).encode("utf-8")
    
    headers = {
        "X-Device-Id": settings.BOOTSTRAP_DEVICE_ID,
        "X-Timestamp": str(now_ts),
        "X-Signature": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "Content-Type": "application/json"
    }
    
    response = client.post("/api/v1/ingest", content=raw_body, headers=headers)
    assert response.status_code == 401
    assert "Invalid HMAC signature" in response.json()["detail"]

def test_ingest_rejects_stale_timestamp(client):
    # Timestamp skewed by 10 minutes (600 seconds)
    stale_ts = int(time.time()) - 600
    payload = {
        "idempotency_key": "stale_key",
        "source": "sms",
        "sender": "HDFCBK",
        "body": "Test message",
        "received_at_ms": stale_ts * 1000
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = calculate_hmac_signature(settings.BOOTSTRAP_DEVICE_SECRET, str(stale_ts), raw_body)
    
    headers = {
        "X-Device-Id": settings.BOOTSTRAP_DEVICE_ID,
        "X-Timestamp": str(stale_ts),
        "X-Signature": sig,
        "Content-Type": "application/json"
    }
    
    response = client.post("/api/v1/ingest", content=raw_body, headers=headers)
    assert response.status_code == 401
    assert "skew exceeds" in response.json()["detail"]

def test_heartbeat_updates_device_and_records_event(client):
    now_ts = int(time.time())
    payload = {
        "battery_pct": 82,
        "is_charging": True,
        "outbox_count": 0,
        "last_sms_received_at_ms": (now_ts - 120) * 1000,
        "app_version": "0.1.0"
    }
    raw_body = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    sig = calculate_hmac_signature(settings.BOOTSTRAP_DEVICE_SECRET, str(now_ts), raw_body)
    
    headers = {
        "X-Device-Id": settings.BOOTSTRAP_DEVICE_ID,
        "X-Timestamp": str(now_ts),
        "X-Signature": sig,
        "Content-Type": "application/json"
    }
    
    response = client.post("/api/v1/heartbeat", content=raw_body, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "server_time_utc" in data
