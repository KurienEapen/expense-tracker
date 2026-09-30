from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.template import ParserTemplateModel
from app.parser.engine import parse_message
from app.parser.models import ParsedTransaction
from app.parser.registry import get_registry
from app.parser.reparse import reparse_all

router = APIRouter()

class TemplateInfo(BaseModel):
    id: str
    issuer: str
    card_type: str
    senders: List[str]
    transaction_type: str
    category_override: Optional[str] = None
    is_active: bool = True

class TestParseRequest(BaseModel):
    sender: str
    body: str

class ReparseResponse(BaseModel):
    total_raw: int
    template_parsed: int
    fallback_parsed: int
    unparsed: int

@router.get("/templates", response_model=List[TemplateInfo])
def list_templates():
    """
    Returns list of all active parser templates loaded in memory.
    """
    registry = get_registry()
    result = []
    for compiled in registry.get_all_templates():
        t = compiled.definition
        result.append(
            TemplateInfo(
                id=t.id,
                issuer=t.issuer,
                card_type=t.card_type,
                senders=t.senders,
                transaction_type=t.transaction_type,
                category_override=t.category_override,
                is_active=True,
            )
        )
    return result

@router.post("/test", response_model=Optional[ParsedTransaction])
def test_parse(payload: TestParseRequest):
    """
    Tests raw sender + body against registered templates and fallback parser.
    """
    return parse_message(sender=payload.sender, body=payload.body)

@router.post("/reparse", response_model=ReparseResponse)
def trigger_reparse(
    limit: Optional[int] = Query(None, description="Max messages to reparse"),
    db: Session = Depends(get_db)
):
    """
    Reparses stored raw messages in SQLite database.
    """
    stats = reparse_all(db, limit=limit)
    return ReparseResponse(**stats)
