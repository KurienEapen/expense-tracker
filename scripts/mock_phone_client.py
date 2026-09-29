#!/usr/bin/env python3
"""
Mock Phone Client for Personal Expense Tracker.
Simulates Android companion app signing, outbox queuing, and sending:
- SMS ingestion
- Heartbeats
- Replay / Skew testing
"""

import sys
import json
import time
import hmac
import hashlib
import argparse
import requests

DEFAULT_SERVER_URL = "http://127.0.0.1:8000"
DEFAULT_DEVICE_ID = "pixel-companion-01"
DEFAULT_DEVICE_SECRET = "dev_secret_change_in_production_32bytes"

SAMPLE_MESSAGES = [
    {
        "source": "sms",
        "sender": "HDFCBK",
        "body": "Rs 1,840.00 spent on HDFC Bank Card x4321 at ZOMATO on 29-09-2026. Avl Lmt: Rs 1,42,160.00",
    },
    {
        "source": "sms",
        "sender": "ICICIB",
        "body": "Dear Customer, INR 320.00 debited from ICICI Bank Card XX8910 at BLUE TOKAI COFFEE.",
    },
    {
        "source": "sms",
        "sender": "SBICRD",
        "body": "Your SBI Credit Card ending 7654 was used for Rs 4,500.00 at RELIANCE DIGITAL on 29-Sep-2026.",
    },
    {
        "source": "sms",
        "sender": "AXISBK",
        "body": "INR 2,000.00 spent on Axis IOCL Card ending 1122 at INDIAN OIL CORP on 29-09-2026. Surcharge waiver eligible.",
    },
    {
        "source": "notification",
        "sender": "Google Pay",
        "app_package": "com.google.android.apps.nbu.paisa.user",
        "body": "Paid ₹340 to Ramesh Kirana using HDFC Bank xx9876. UPI Ref: 627389102938",
    }
]

def calculate_hmac(secret: str, timestamp_str: str, body_bytes: bytes) -> str:
    message = timestamp_str.encode("utf-8") + b"." + body_bytes
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

def compute_idempotency_key(sender: str, body: str, received_at_ms: int) -> str:
    data = f"{sender}|{body}|{received_at_ms}".encode("utf-8")
    return hashlib.sha256(data).hexdigest()

def send_ingest(server_url: str, device_id: str, secret: str, sample_idx: int = 0):
    sample = SAMPLE_MESSAGES[sample_idx % len(SAMPLE_MESSAGES)]
    now_ts = int(time.time())
    received_ms = now_ts * 1000
    
    key = compute_idempotency_key(sample["sender"], sample["body"], received_ms)
    
    payload = {
        "idempotency_key": key,
        "source": sample["source"],
        "sender": sample["sender"],
        "app_package": sample.get("app_package"),
        "body": sample["body"],
        "received_at_ms": received_ms,
        "device_tz": "Asia/Kolkata",
        "location": {"lat": 12.9716, "lon": 77.5946, "accuracy_m": 20.0, "fix_age_s": 15},
        "app_version": "0.1.0-sim"
    }
    
    body_bytes = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    sig = calculate_hmac(secret, str(now_ts), body_bytes)
    
    headers = {
        "X-Device-Id": device_id,
        "X-Timestamp": str(now_ts),
        "X-Signature": sig,
        "Content-Type": "application/json"
    }
    
    url = f"{server_url}/api/v1/ingest"
    print(f"\n[POST] {url}")
    print(f"Device: {device_id} | Sender: {sample['sender']}")
    print(f"Body: {sample['body']}")
    
    res = requests.post(url, data=body_bytes, headers=headers)
    print(f"Status: {res.status_code} => {res.text}")

def send_heartbeat(server_url: str, device_id: str, secret: str):
    now_ts = int(time.time())
    payload = {
        "battery_pct": 89,
        "is_charging": False,
        "outbox_count": 0,
        "last_sms_received_at_ms": (now_ts - 60) * 1000,
        "app_version": "0.1.0-sim"
    }
    
    body_bytes = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    sig = calculate_hmac(secret, str(now_ts), body_bytes)
    
    headers = {
        "X-Device-Id": device_id,
        "X-Timestamp": str(now_ts),
        "X-Signature": sig,
        "Content-Type": "application/json"
    }
    
    url = f"{server_url}/api/v1/heartbeat"
    print(f"\n[POST] {url}")
    res = requests.post(url, data=body_bytes, headers=headers)
    print(f"Status: {res.status_code} => {res.text}")

def main():
    parser = argparse.ArgumentParser(description="Simulate Phone Companion Client")
    parser.add_argument("--server", default=DEFAULT_SERVER_URL, help="Base server URL")
    parser.add_argument("--device-id", default=DEFAULT_DEVICE_ID, help="Device ID")
    parser.add_argument("--secret", default=DEFAULT_DEVICE_SECRET, help="Device HMAC secret")
    parser.add_argument("--action", choices=["ingest", "heartbeat", "all"], default="all")
    args = parser.parse_args()
    
    if args.action in ("ingest", "all"):
        for i in range(len(SAMPLE_MESSAGES)):
            send_ingest(args.server, args.device_id, args.secret, i)
            time.sleep(0.2)
            
    if args.action in ("heartbeat", "all"):
        send_heartbeat(args.server, args.device_id, args.secret)

if __name__ == "__main__":
    main()
