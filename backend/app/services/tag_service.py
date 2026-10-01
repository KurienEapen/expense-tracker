from datetime import datetime, time
from typing import List, Optional, Union, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.tag import Tag, TagExclusion, transaction_tags
from app.models.transaction import Transaction

def normalize_date_range(start_date: Optional[datetime], end_date: Optional[datetime]):
    """
    Ensures start_date begins at 00:00:00 and end_date ends at 23:59:59
    if only dates or zeroed times were provided.
    """
    if start_date and start_date.time() == time(0, 0):
        start_date = datetime.combine(start_date.date(), time(0, 0, 0))
    if end_date and end_date.time() == time(0, 0):
        end_date = datetime.combine(end_date.date(), time(23, 59, 59, 999999))
    return start_date, end_date

def auto_tag_transaction(db: Session, txn: Transaction) -> List[Tag]:
    """
    Evaluates active date-range tags against a transaction's timestamp.
    Attaches any matching tags that haven't been manually excluded by the user.
    """
    if not txn.transacted_at_utc:
        return []

    matching_tags = db.query(Tag).filter(
        Tag.auto_tag_active == True,
        Tag.start_date != None,
        Tag.end_date != None,
        Tag.start_date <= txn.transacted_at_utc,
        Tag.end_date >= txn.transacted_at_utc
    ).all()

    if not matching_tags:
        return []

    # Get set of excluded tag IDs for this transaction
    excluded_ids = set(
        row[0] for row in db.query(TagExclusion.tag_id).filter(
            TagExclusion.transaction_id == txn.id
        ).all()
    )

    current_tag_ids = {t.id for t in txn.tags} if txn.tags else set()
    added_tags = []

    for tag in matching_tags:
        if tag.id not in excluded_ids and tag.id not in current_tag_ids:
            txn.tags.append(tag)
            added_tags.append(tag)

    return added_tags

def apply_tag_to_date_range(db: Session, tag: Tag) -> int:
    """
    Retroactively applies a tag to all existing transactions that fall within
    the tag's [start_date, end_date] window (unless explicitly excluded).
    """
    if not (tag.start_date and tag.end_date and tag.auto_tag_active):
        return 0

    txns = db.query(Transaction).filter(
        Transaction.status != "ignored",
        Transaction.transacted_at_utc >= tag.start_date,
        Transaction.transacted_at_utc <= tag.end_date
    ).all()

    if not txns:
        return 0

    # Get all exclusions for this tag
    excluded_txn_ids = set(
        row[0] for row in db.query(TagExclusion.transaction_id).filter(
            TagExclusion.tag_id == tag.id
        ).all()
    )

    tagged_count = 0
    for txn in txns:
        if txn.id not in excluded_txn_ids:
            if tag not in txn.tags:
                txn.tags.append(tag)
                tagged_count += 1

    db.commit()
    return tagged_count

def get_or_create_tag(
    db: Session,
    name: str,
    color: Optional[str] = None,
    icon: Optional[str] = None,
    description: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    auto_tag_active: bool = True
) -> Tag:
    """
    Gets an existing tag by name or creates a new one.
    """
    clean_name = name.strip()
    if clean_name.startswith("#"):
        clean_name = clean_name[1:].strip()

    tag = db.query(Tag).filter(Tag.name.ilike(clean_name)).first()
    if tag:
        return tag

    start_date, end_date = normalize_date_range(start_date, end_date)

    tag = Tag(
        name=clean_name,
        color=color or "#6366F1",
        icon=icon or "🏷️",
        description=description,
        start_date=start_date,
        end_date=end_date,
        auto_tag_active=auto_tag_active,
        created_at_utc=datetime.utcnow()
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag

def attach_tag_to_transaction(
    db: Session,
    txn_id: int,
    tag_name_or_id: Union[int, str],
    color: Optional[str] = None,
    icon: Optional[str] = None
) -> Tag:
    """
    Attaches a tag to a transaction. Clears any manual exclusion.
    """
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise ValueError(f"Transaction #{txn_id} not found")

    if isinstance(tag_name_or_id, int):
        tag = db.query(Tag).filter(Tag.id == tag_name_or_id).first()
        if not tag:
            raise ValueError(f"Tag #{tag_name_or_id} not found")
    else:
        tag = get_or_create_tag(db, name=tag_name_or_id, color=color, icon=icon)

    # Remove any exclusion record if user is explicitly re-adding the tag
    db.query(TagExclusion).filter(
        TagExclusion.transaction_id == txn.id,
        TagExclusion.tag_id == tag.id
    ).delete()

    if tag not in txn.tags:
        txn.tags.append(tag)
        txn.updated_at_utc = datetime.utcnow()
        db.commit()
        db.refresh(txn)

    return tag

def detach_tag_from_transaction(
    db: Session,
    txn_id: int,
    tag_name_or_id: Union[int, str]
) -> bool:
    """
    Detaches a tag from a transaction and records an exclusion so auto-tagging
    will not re-add it.
    """
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise ValueError(f"Transaction #{txn_id} not found")

    if isinstance(tag_name_or_id, int):
        tag = db.query(Tag).filter(Tag.id == tag_name_or_id).first()
    else:
        clean_name = tag_name_or_id.strip()
        if clean_name.startswith("#"):
            clean_name = clean_name[1:].strip()
        tag = db.query(Tag).filter(Tag.name.ilike(clean_name)).first()

    if not tag:
        return False

    if tag in txn.tags:
        txn.tags.remove(tag)
        txn.updated_at_utc = datetime.utcnow()

    # Record exclusion so date-range trip auto-tagging won't re-add it
    existing_ex = db.query(TagExclusion).filter(
        TagExclusion.transaction_id == txn.id,
        TagExclusion.tag_id == tag.id
    ).first()
    if not existing_ex:
        db.add(TagExclusion(
            transaction_id=txn.id,
            tag_id=tag.id,
            created_at_utc=datetime.utcnow()
        ))

    db.commit()
    return True

def get_tag_summary(db: Session, tag: Tag) -> Dict[str, Any]:
    """
    Calculates detailed metrics for a tag:
    spend amount, transaction count, category breakdown, active status.
    """
    from collections import defaultdict

    txns = tag.transactions
    total_personal_paise = sum(
        (t.my_share_paise if (t.is_split and t.my_share_paise is not None) else t.amount_paise)
        for t in txns if t.status != "ignored" and t.transaction_type == "debit"
    )
    total_spend_inr = round(total_personal_paise / 100.0, 2)

    cat_amounts = defaultdict(float)
    cat_counts = defaultdict(int)
    for t in txns:
        if t.status != "ignored" and t.transaction_type == "debit":
            cat = t.category or "Uncategorized"
            my_share = (t.my_share_paise / 100.0) if (t.is_split and t.my_share_paise is not None) else (t.amount_paise / 100.0)
            cat_amounts[cat] += my_share
            cat_counts[cat] += 1

    category_breakdown = []
    for cat, amt in sorted(cat_amounts.items(), key=lambda x: x[1], reverse=True):
        pct = round((amt / total_spend_inr * 100.0), 1) if total_spend_inr > 0 else 0.0
        category_breakdown.append({
            "category": cat,
            "amount_inr": round(amt, 2),
            "percentage": pct,
            "count": cat_counts[cat]
        })

    now = datetime.utcnow()
    is_active_trip = bool(
        tag.start_date and tag.end_date and
        tag.start_date <= now <= tag.end_date and
        tag.auto_tag_active
    )

    return {
        "id": tag.id,
        "name": tag.name,
        "color": tag.color,
        "icon": tag.icon,
        "description": tag.description,
        "start_date": tag.start_date.isoformat() if tag.start_date else None,
        "end_date": tag.end_date.isoformat() if tag.end_date else None,
        "auto_tag_active": tag.auto_tag_active,
        "transaction_count": len([t for t in txns if t.status != "ignored"]),
        "total_spend_inr": total_spend_inr,
        "category_breakdown": category_breakdown,
        "is_active_trip": is_active_trip,
        "created_at_utc": tag.created_at_utc.isoformat() if tag.created_at_utc else None
    }

def get_active_trip(db: Session) -> Optional[Tag]:
    """
    Returns the currently active trip tag (where now is between start_date and end_date).
    If multiple, returns the most recently updated one.
    """
    now = datetime.utcnow()
    return db.query(Tag).filter(
        Tag.auto_tag_active == True,
        Tag.start_date != None,
        Tag.end_date != None,
        Tag.start_date <= now,
        Tag.end_date >= now
    ).order_by(Tag.id.desc()).first()
