from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from app.core.database import Base

class Device(Base):
    __tablename__ = "devices"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    secret = Column(String(256), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_seen_utc = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at_utc = Column(DateTime, default=datetime.utcnow, nullable=False)
