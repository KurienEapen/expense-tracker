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

class CreateTemplateRequest(BaseModel):
    template_id: str
    issuer: str
    senders: List[str]
    regex: str
    transaction_type: str = "debit"
    card_type: str = "credit"
    amount_group: int = 1
    merchant_group: Optional[int] = None
    card_last4_group: Optional[int] = None

@router.post("/templates/create")
def create_custom_template(payload: CreateTemplateRequest, db: Session = Depends(get_db)):
    """
    Creates and saves a new custom YAML parser template.
    All future matching messages will automatically be parsed with 100% confidence.
    """
    import yaml
    from app.parser.registry import TEMPLATES_DIR, get_registry
    
    custom_yaml_path = TEMPLATES_DIR / "custom_user_templates.yaml"
    existing_data = []
    if custom_yaml_path.exists():
        with open(custom_yaml_path, "r", encoding="utf-8") as f:
            existing_data = yaml.safe_load(f) or []
    
    groups = {"amount": payload.amount_group}
    if payload.merchant_group:
        groups["merchant"] = payload.merchant_group
    if payload.card_last4_group:
        groups["card_last4"] = payload.card_last4_group

    new_template = {
        "id": payload.template_id,
        "issuer": payload.issuer,
        "card_type": payload.card_type,
        "senders": payload.senders,
        "transaction_type": payload.transaction_type,
        "regex": payload.regex,
        "groups": groups
    }
    
    existing_data.append(new_template)
    with open(custom_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(existing_data, f, sort_keys=False)

    registry = get_registry()
    registry.load_from_yaml()
    registry.sync_to_db(db)
    reparse_all(db)

    return {"status": "success", "message": f"Successfully registered template '{payload.template_id}'. Future matching transactions will be parsed automatically."}

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


from fastapi import UploadFile, File
import csv
import io
import hashlib
from datetime import datetime
from app.models.raw_message import RawMessage

class UploadStatementResponse(BaseModel):
    filename: str
    total_lines: int
    ingested_count: int
    reparsed_stats: ReparseResponse
    message: str

@router.post("/upload-statement", response_model=UploadStatementResponse)
async def upload_bank_statement(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Uploads a bank statement (CSV or text file) for automatic parsing and auto-categorization.
    """
    contents = await file.read()
    text = contents.decode("utf-8", errors="ignore")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    ingested = 0
    now_ms = int(datetime.utcnow().timestamp() * 1000)

    for idx, line in enumerate(lines):
        if not line or line.startswith("#") or line.lower().startswith("date,"):
            continue

        # Generate unique idempotency key for statement record
        hash_digest = hashlib.sha256(f"statement_{file.filename}_{idx}_{line}".encode("utf-8")).hexdigest()[:24]
        idempotency_key = f"stmt_{hash_digest}"

        existing = db.query(RawMessage).filter(RawMessage.idempotency_key == idempotency_key).first()
        if not existing:
            raw_msg = RawMessage(
                idempotency_key=idempotency_key,
                source="statement_csv",
                sender="STATEMENT_IMPORT",
                app_package="csv.upload",
                body=line,
                received_at_ms=now_ms,
                device_id="pwa_upload",
                received_at_utc=datetime.utcnow()
            )
            db.add(raw_msg)
            ingested += 1

    if ingested > 0:
        db.commit()

    stats = reparse_all(db, limit=None)

    return UploadStatementResponse(
        filename=file.filename or "statement.csv",
        total_lines=len(lines),
        ingested_count=ingested,
        reparsed_stats=ReparseResponse(**stats),
        message=f"Successfully ingested {ingested} new transaction records from statement."
    )

