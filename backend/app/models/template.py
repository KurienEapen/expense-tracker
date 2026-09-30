from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from app.core.database import Base

class ParserTemplateModel(Base):
    __tablename__ = "parser_templates"

    id = Column(String(64), primary_key=True)
    issuer = Column(String(32), nullable=False, index=True)
    card_type = Column(String(32), nullable=False)
    senders_json = Column(Text, nullable=False)  # JSON array of uppercase senders
    transaction_type = Column(String(32), nullable=False)  # debit | credit | surcharge_waiver
    regex = Column(Text, nullable=False)
    groups_json = Column(Text, nullable=False)  # JSON object mapping field names to group indices
    category_override = Column(String(64), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at_utc = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at_utc = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
