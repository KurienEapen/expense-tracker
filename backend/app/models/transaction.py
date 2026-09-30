from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, Float, Boolean, ForeignKey
from app.core.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_message_id = Column(Integer, ForeignKey("raw_messages.id"), nullable=True, index=True)
    source = Column(String(32), default="sms", nullable=False)  # sms | notification | manual | import
    issuer = Column(String(32), nullable=False, index=True)      # HDFC | ICICI | SBI | Axis | Scapia | Jupiter | HSBC | Unknown
    card_type = Column(String(32), default="credit", nullable=False)  # credit | debit | upi | account
    card_last4 = Column(String(4), nullable=True, index=True)
    transaction_type = Column(String(32), default="debit", nullable=False)  # debit | credit | surcharge_waiver
    amount_paise = Column(BigInteger, nullable=False)  # integer paise (e.g., 184000 = 1840.00 INR)
    currency = Column(String(3), default="INR", nullable=False)
    merchant_raw = Column(String(256), nullable=True)
    merchant_clean = Column(String(256), nullable=True, index=True)
    category = Column(String(64), nullable=True, index=True)
    needs_review = Column(Boolean, default=False, nullable=False, index=True)  # True = ambiguous, needs user tap
    review_source = Column(String(32), default="auto", nullable=False)         # auto | user_notification | web
    reviewed_at_utc = Column(DateTime, nullable=True)
    transacted_at_utc = Column(DateTime, nullable=False, index=True)
    parsed_by_template_id = Column(String(64), nullable=True)
    parser_confidence = Column(Float, default=1.0, nullable=False)  # 1.0 = template match, 0.5 = fallback
    status = Column(String(32), default="settled", nullable=False)  # settled | pending | reversed
    notes = Column(Text, nullable=True)
    created_at_utc = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at_utc = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
