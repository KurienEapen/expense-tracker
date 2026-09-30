from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from app.core.database import Base

class IgnoreRule(Base):
    __tablename__ = "ignore_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern = Column(String(256), nullable=False, index=True)
    pattern_type = Column(String(32), default="regex", nullable=False)  # regex | keyword
    sender_filter = Column(String(64), nullable=True, index=True)       # e.g., 'HDFCBK' or None for all
    description = Column(String(256), nullable=True)
    sample_text = Column(Text, nullable=True)
    match_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at_utc = Column(DateTime, default=datetime.utcnow, nullable=False)
