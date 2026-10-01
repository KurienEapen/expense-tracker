from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.tag import Tag, TagExclusion
from app.models.transaction import Transaction
from app.services.tag_service import (
    get_or_create_tag,
    apply_tag_to_date_range,
    attach_tag_to_transaction,
    detach_tag_from_transaction,
    get_tag_summary,
    get_active_trip,
    normalize_date_range
)

router = APIRouter()

class CreateTagRequest(BaseModel):
    name: str
    color: Optional[str] = "#6366F1"
    icon: Optional[str] = "🏷️"
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    auto_tag_active: bool = True
    apply_to_existing: bool = True

class UpdateTagRequest(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    auto_tag_active: Optional[bool] = None
    reapply_date_range: bool = False

@router.get("", response_model=List[Dict[str, Any]])
def list_tags(db: Session = Depends(get_db)):
    """
    Returns all tags with total spend, transaction counts, and category breakdowns.
    """
    tags = db.query(Tag).order_by(Tag.name.asc()).all()
    return [get_tag_summary(db, t) for t in tags]

@router.get("/active-trip")
def get_current_active_trip(db: Session = Depends(get_db)):
    """
    Returns the currently active trip tag (where now is between start_date and end_date),
    or null if no trip is currently active.
    """
    trip = get_active_trip(db)
    if not trip:
        return {"active_trip": None}
    return {"active_trip": get_tag_summary(db, trip)}

@router.post("", status_code=status.HTTP_201_CREATED)
def create_tag(payload: CreateTagRequest, db: Session = Depends(get_db)):
    """
    Creates a new tag (e.g. for an upcoming trip).
    If start_date and end_date are provided and apply_to_existing is True,
    all transactions falling in this date range are automatically tagged.
    """
    clean_name = payload.name.strip()
    if clean_name.startswith("#"):
        clean_name = clean_name[1:].strip()

    if not clean_name:
        raise HTTPException(status_code=400, detail="Tag name cannot be empty")

    existing = db.query(Tag).filter(Tag.name.ilike(clean_name)).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Tag '{clean_name}' already exists")

    start_date, end_date = normalize_date_range(payload.start_date, payload.end_date)

    tag = Tag(
        name=clean_name,
        color=payload.color or "#6366F1",
        icon=payload.icon or "🏷️",
        description=payload.description,
        start_date=start_date,
        end_date=end_date,
        auto_tag_active=payload.auto_tag_active,
        created_at_utc=datetime.utcnow()
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)

    retroactive_count = 0
    if payload.apply_to_existing and tag.start_date and tag.end_date and tag.auto_tag_active:
        retroactive_count = apply_tag_to_date_range(db, tag)

    summary = get_tag_summary(db, tag)
    summary["retroactively_tagged_count"] = retroactive_count
    return summary

@router.get("/{tag_id}")
def get_tag_details(tag_id: int, db: Session = Depends(get_db)):
    """
    Retrieves detailed metrics and transactions for a specific tag.
    """
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail=f"Tag #{tag_id} not found")

    summary = get_tag_summary(db, tag)
    # Include list of transaction IDs and basic details
    summary["transactions"] = [
        {
            "id": t.id,
            "merchant": t.merchant_clean or t.merchant_raw,
            "amount_inr": (t.amount_paise / 100.0),
            "category": t.category,
            "transacted_at_utc": t.transacted_at_utc.isoformat() if t.transacted_at_utc else None
        }
        for t in tag.transactions if t.status != "ignored"
    ]
    return summary

@router.put("/{tag_id}")
def update_tag(tag_id: int, payload: UpdateTagRequest, db: Session = Depends(get_db)):
    """
    Updates an existing tag's details or date range.
    """
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail=f"Tag #{tag_id} not found")

    if payload.name is not None:
        new_name = payload.name.strip().lstrip("#")
        if new_name:
            tag.name = new_name
    if payload.color is not None:
        tag.color = payload.color
    if payload.icon is not None:
        tag.icon = payload.icon
    if payload.description is not None:
        tag.description = payload.description
    if payload.auto_tag_active is not None:
        tag.auto_tag_active = payload.auto_tag_active

    if payload.start_date is not None or payload.end_date is not None:
        new_start = payload.start_date if payload.start_date is not None else tag.start_date
        new_end = payload.end_date if payload.end_date is not None else tag.end_date
        tag.start_date, tag.end_date = normalize_date_range(new_start, new_end)

    tag.updated_at_utc = datetime.utcnow()
    db.commit()
    db.refresh(tag)

    if payload.reapply_date_range and tag.start_date and tag.end_date and tag.auto_tag_active:
        apply_tag_to_date_range(db, tag)

    return get_tag_summary(db, tag)

@router.delete("/{tag_id}", status_code=status.HTTP_200_OK)
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    """
    Deletes a tag. Transactions themselves are preserved with the tag removed.
    """
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail=f"Tag #{tag_id} not found")

    tag_name = tag.name
    # Explicitly clear exclusions and associations
    db.query(TagExclusion).filter(TagExclusion.tag_id == tag.id).delete()
    tag.transactions.clear()
    db.delete(tag)
    db.commit()
    return {"status": "deleted", "tag_name": tag_name, "message": f"Tag '{tag_name}' deleted"}

@router.post("/{tag_id}/transactions/{txn_id}")
def attach_tag(tag_id: int, txn_id: int, db: Session = Depends(get_db)):
    """
    Associates a tag with a transaction.
    """
    try:
        tag = attach_tag_to_transaction(db, txn_id=txn_id, tag_name_or_id=tag_id)
        return {"status": "attached", "tag": tag.name, "transaction_id": txn_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{tag_id}/transactions/{txn_id}")
def detach_tag(tag_id: int, txn_id: int, db: Session = Depends(get_db)):
    """
    Removes a tag from a transaction and records an exclusion so auto-tagging won't re-add it.
    """
    try:
        success = detach_tag_from_transaction(db, txn_id=txn_id, tag_name_or_id=tag_id)
        if not success:
            raise HTTPException(status_code=404, detail="Tag not associated with transaction")
        return {"status": "detached", "tag_id": tag_id, "transaction_id": txn_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
