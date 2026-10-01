from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.raw_message import RawMessage

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_message_id = Column(Integer, ForeignKey("raw_messages.id"), nullable=True, index=True)
    raw_message = relationship("RawMessage", foreign_keys=[raw_message_id])
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
    is_split = Column(Boolean, default=False, nullable=False, index=True)
    my_share_paise = Column(BigInteger, nullable=True)  # Nullable: if None, 100% my share
    reimbursable_paise = Column(BigInteger, default=0, nullable=False)
    split_ratio_label = Column(String(32), nullable=True)  # 1/2 | 1/3 | 1/4 | custom
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    location_name = Column(String(256), nullable=True, index=True)
    location_address = Column(String(512), nullable=True)
    notes = Column(Text, nullable=True)
    created_at_utc = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at_utc = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tags = relationship("Tag", secondary="transaction_tags", back_populates="transactions", lazy="joined")
