from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class TemplateTestCaseExpected(BaseModel):
    amount_paise: Optional[int] = None
    card_last4: Optional[str] = None
    merchant: Optional[str] = None
    transaction_type: Optional[str] = None
    category_override: Optional[str] = None

class TemplateTestCase(BaseModel):
    input: str
    expected: TemplateTestCaseExpected

class TemplateDefinition(BaseModel):
    id: str
    issuer: str
    card_type: str = "credit"
    senders: List[str]
    transaction_type: str = "debit"
    regex: str
    groups: Dict[str, int]
    category_override: Optional[str] = None
    test_cases: List[TemplateTestCase] = Field(default_factory=list)

class ParsedTransaction(BaseModel):
    issuer: str
    card_type: str = "credit"
    card_last4: Optional[str] = None
    transaction_type: str = "debit"
    amount_paise: int
    currency: str = "INR"
    merchant_raw: Optional[str] = None
    merchant_clean: Optional[str] = None
    category: Optional[str] = None
    transacted_at_utc: datetime = Field(default_factory=datetime.utcnow)
    parsed_by_template_id: Optional[str] = None
    parser_confidence: float = 1.0
    status: str = "settled"
