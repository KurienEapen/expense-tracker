import hmac
import hashlib
import time
from typing import Tuple
from app.core.config import settings

def calculate_hmac_signature(secret: str, timestamp_str: str, raw_body: bytes) -> str:
    """Computes hex(HMAC_SHA256(secret, timestamp + "." + raw_body))"""
    message = timestamp_str.encode("utf-8") + b"." + raw_body
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

def verify_timestamp(timestamp_str: str, tolerance_seconds: int = None) -> Tuple[bool, str]:
    """Ensures timestamp is within acceptable skew to prevent replay attacks."""
    if tolerance_seconds is None:
        tolerance_seconds = settings.TIMESTAMP_SKEW_TOLERANCE_SECONDS
    try:
        ts = int(timestamp_str)
    except (ValueError, TypeError):
        return False, "Invalid timestamp format (must be integer unix epoch seconds)"
    
    current_ts = int(time.time())
    if abs(current_ts - ts) > tolerance_seconds:
        return False, f"Timestamp skew exceeds {tolerance_seconds}s (server: {current_ts}, client: {ts})"
    return True, ""

def compute_idempotency_key(sender: str, body: str, received_at_ms: int) -> str:
    """
    Computes sha256(sender + '|' + body + '|' + time_bucket).
    Buckets timestamp into 5-minute windows to ensure duplicate SMS broadcasts 
    received milliseconds/seconds apart produce identical idempotency keys.
    """
    time_bucket = (received_at_ms // 300000) if received_at_ms else 0
    data = f"{sender.strip().lower()}|{body.strip().lower()}|{time_bucket}".encode("utf-8")
    return hashlib.sha256(data).hexdigest()

