import json
from datetime import datetime
from fastapi import Header, HTTPException, Request, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import verify_timestamp, calculate_hmac_signature
from app.models.device import Device

async def authenticate_device(
    request: Request,
    db: Session = Depends(get_db),
    x_device_id: str = Header(..., alias="X-Device-Id"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    x_signature: str = Header(..., alias="X-Signature")
) -> Device:
    # 1. Validate timestamp skew to prevent replay attacks
    is_valid_ts, ts_err = verify_timestamp(x_timestamp)
    if not is_valid_ts:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Replay protection error: {ts_err}"
        )
    
    # 2. Lookup device in database
    device = db.query(Device).filter(Device.id == x_device_id, Device.is_active == True).first()
    
    # Bootstrap fallback: If the database is new and device matches bootstrap config, seed it
    if not device and x_device_id == settings.BOOTSTRAP_DEVICE_ID:
        device = Device(
            id=settings.BOOTSTRAP_DEVICE_ID,
            name="Primary Phone Companion (Bootstrap)",
            secret=settings.BOOTSTRAP_DEVICE_SECRET,
            is_active=True,
            created_at_utc=datetime.utcnow(),
            last_seen_utc=datetime.utcnow()
        )
        db.add(device)
        db.commit()
        db.refresh(device)
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unregistered or deactivated device ID"
        )
    
    # 3. Read raw request body bytes for HMAC verification
    raw_body = await request.body()
    
    # 4. Verify HMAC signature
    expected_signature = calculate_hmac_signature(device.secret, x_timestamp, raw_body)
    if not hmac_compare_safe(expected_signature, x_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HMAC signature"
        )
    
    # Update device last_seen timestamp
    device.last_seen_utc = datetime.utcnow()
    db.commit()
    
    return device

def hmac_compare_safe(a: str, b: str) -> bool:
    import hmac
    return hmac.compare_digest(a.lower(), b.lower())
