from datetime import datetime
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import authenticate_device
from app.models.device import Device
from app.models.raw_message import Heartbeat
from app.schemas.heartbeat import HeartbeatPayload, HeartbeatResponse

router = APIRouter()

@router.post("/heartbeat", response_model=HeartbeatResponse, status_code=status.HTTP_200_OK)
def receive_heartbeat(
    payload: HeartbeatPayload,
    db: Session = Depends(get_db),
    device: Device = Depends(authenticate_device)
):
    now = datetime.utcnow()
    
    # Record heartbeat event
    heartbeat_record = Heartbeat(
        device_id=device.id,
        battery_pct=payload.battery_pct,
        is_charging=payload.is_charging,
        outbox_count=payload.outbox_count,
        last_sms_received_at_ms=payload.last_sms_received_at_ms,
        app_version=payload.app_version,
        received_at_utc=now
    )
    db.add(heartbeat_record)
    
    # Update device last seen timestamp
    device.last_seen_utc = now
    db.commit()
    
    return HeartbeatResponse(
        status="ok",
        server_time_utc=now.isoformat() + "Z",
        message="Heartbeat acknowledged"
    )
