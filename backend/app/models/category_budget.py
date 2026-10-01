from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.core.database import Base

class CategoryBudget(Base):
    __tablename__ = "category_budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(64), unique=True, index=True, nullable=False)
    budget_limit_paise = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at_utc = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at_utc = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
