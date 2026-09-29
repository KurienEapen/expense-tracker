from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, BigInteger
from app.core.database import Base

class RawMessage(Base):
    __tablename__ = "raw_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idempotency_key = Column(String(64), unique=True, index=True, nullable=False)
    source = Column(String(32), nullable=False)  # sms | notification | screenshot_ocr | share_text
    sender = Column(String(64), nullable=False, index=True)
    app_package = Column(String(128), nullable=True)
    body = Column(Text, nullable=False)
    received_at_ms = Column(BigInteger, nullable=False)
    received_at_utc = Column(DateTime, nullable=False)
    device_tz = Column(String(64), default="Asia/Kolkata", nullable=False)
    location_json = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    device_id = Column(String(64), nullable=False, index=True)
    app_version = Column(String(32), nullable=True)
    ingested_at_utc = Column(DateTime, default=datetime.utcnow, nullable=False)

class Heartbeat(Base):
    __tablename__ = "heartbeats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), nullable=False, index=True)
    battery_pct = Column(Integer, nullable=True)
    is_charging = Column(Boolean, nullable=True)
    outbox_count = Column(Integer, default=0, nullable=False)
    last_sms_received_at_ms = Column(BigInteger, nullable=True)
    app_version = Column(String(32), nullable=True)
    received_at_utc = Column(DateTime, default=datetime.utcnow, nullable=False)
