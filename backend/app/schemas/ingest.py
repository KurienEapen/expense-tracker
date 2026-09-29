from typing import Optional, Literal
from pydantic import BaseModel, Field

class LocationPayload(BaseModel):
    lat: float
    lon: float
    accuracy_m: Optional[float] = None
    fix_age_s: Optional[int] = None

class IngestPayload(BaseModel):
    idempotency_key: str = Field(..., description="sha256(sender + '|' + body + '|' + received_ts_ms)")
    source: Literal["sms", "notification", "screenshot_ocr", "share_text"]
    sender: str = Field(..., min_length=1)
    app_package: Optional[str] = None
    body: str = Field(..., min_length=1)
    received_at_ms: int = Field(..., description="Epoch milliseconds when message was received on phone")
    device_tz: str = Field(default="Asia/Kolkata")
    location: Optional[LocationPayload] = None
    ocr_confidence: Optional[float] = None
    app_version: Optional[str] = None

class IngestResponse(BaseModel):
    status: Literal["stored", "duplicate"]
    raw_id: Optional[int] = None
    message: Optional[str] = None
