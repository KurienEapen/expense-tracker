from typing import Optional, Literal
from pydantic import BaseModel

class HeartbeatPayload(BaseModel):
    battery_pct: Optional[int] = None
    is_charging: Optional[bool] = None
    outbox_count: int = 0
    last_sms_received_at_ms: Optional[int] = None
    app_version: Optional[str] = None

class HeartbeatResponse(BaseModel):
    status: Literal["ok"] = "ok"
    server_time_utc: str
    message: Optional[str] = None
