from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.core.database import Base

transaction_tags = Table(
    "transaction_tags",
    Base.metadata,
    Column("transaction_id", Integer, ForeignKey("transactions.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at_utc", DateTime, default=datetime.utcnow, nullable=False),
)

class TagExclusion(Base):
    """
    Tracks transactions that the user explicitly untagged from a tag.
    Prevents auto-tagging (e.g. date-range trip tagging) from re-adding the tag
    if re-evaluated or reparsed.
    """
    __tablename__ = "tag_exclusions"

    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    created_at_utc = Column(DateTime, default=datetime.utcnow, nullable=False)

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), unique=True, nullable=False, index=True)
    color = Column(String(32), default="#6366F1", nullable=False)
    icon = Column(String(32), default="🏷️", nullable=False)
    description = Column(String(256), nullable=True)
    
    # Optional date range for Trip / Event auto-tagging
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    auto_tag_active = Column(Boolean, default=True, nullable=False)

    created_at_utc = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at_utc = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    transactions = relationship("Transaction", secondary=transaction_tags, back_populates="tags")
