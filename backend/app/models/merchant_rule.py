from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from app.core.database import Base

class MerchantRule(Base):
    __tablename__ = "merchant_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern = Column(String(128), unique=True, index=True, nullable=False)  # Normalized clean merchant substring
    category = Column(String(64), nullable=False, index=True)
    is_user_defined = Column(Boolean, default=True, nullable=False)  # True = learned from user, False = seeded catalog
    confidence = Column(Float, default=1.0, nullable=False)
    created_at_utc = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at_utc = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
