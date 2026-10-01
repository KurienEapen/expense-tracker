from datetime import datetime, timedelta
import pytest
from app.models.transaction import Transaction
from app.models.tag import Tag, TagExclusion
from app.models.raw_message import RawMessage
from app.parser.reparse import reparse_raw_message

def test_create_tag_and_manual_attach(client, db):
    # 1. Create a transaction
    txn = Transaction(
        source="sms",
        issuer="HDFC",
        card_type="credit",
        transaction_type="debit",
        amount_paise=150000, # 1500 INR
        currency="INR",
        merchant_raw="SWIGGY BANGALORE",
        merchant_clean="Swiggy",
        category="Food & Dining",
        transacted_at_utc=datetime.utcnow(),
        status="settled"
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    # 2. Create Tag via API
    res = client.post("/api/v1/tags", json={
        "name": "Foodie Weekend",
        "color": "#10B981",
        "icon": "🍔",
        "description": "Weekend food exploration"
    })
    assert res.status_code == 201
    tag_data = res.json()
    assert tag_data["name"] == "Foodie Weekend"
    assert tag_data["icon"] == "🍔"

    # 3. Manually attach tag to transaction
    res = client.post(f"/api/v1/transactions/{txn.id}/tags", json={
        "tag_name": "Foodie Weekend"
    })
    assert res.status_code == 200
    txn_data = res.json()
    assert "Foodie Weekend" in txn_data["tags"]
    assert len(txn_data["tag_details"]) == 1
    assert txn_data["tag_details"][0]["name"] == "Foodie Weekend"

    # 4. Filter transactions by tag
    res = client.get("/api/v1/transactions?tag=Foodie Weekend")
    assert res.status_code == 200
    filtered = res.json()
    assert len(filtered) == 1
    assert filtered[0]["id"] == txn.id

    # 5. Remove tag from transaction
    res = client.delete(f"/api/v1/transactions/{txn.id}/tags/Foodie Weekend")
    assert res.status_code == 200
    updated_txn = res.json()
    assert "Foodie Weekend" not in updated_txn["tags"]

def test_trip_date_range_auto_tagging(client, db):
    # Create two transactions: one inside trip window, one outside
    now = datetime.utcnow()
    trip_start = now - timedelta(days=2)
    trip_end = now + timedelta(days=2)

    # In-trip transaction
    txn_in = Transaction(
        source="sms",
        issuer="ICICI",
        card_type="credit",
        transaction_type="debit",
        amount_paise=450000, # 4500 INR
        currency="INR",
        merchant_raw="TAJ RESORT GOA",
        merchant_clean="Taj Resort",
        category="Travel",
        transacted_at_utc=now,
        status="settled"
    )
    # Outside-trip transaction
    txn_out = Transaction(
        source="sms",
        issuer="ICICI",
        card_type="credit",
        transaction_type="debit",
        amount_paise=80000, # 800 INR
        currency="INR",
        merchant_raw="SHELL FUEL PUMP",
        merchant_clean="Shell",
        category="Fuel",
        transacted_at_utc=now - timedelta(days=10),
        status="settled"
    )
    db.add_all([txn_in, txn_out])
    db.commit()

    # Create Goa Trip tag with date range covering now
    res = client.post("/api/v1/tags", json={
        "name": "Goa Trip",
        "color": "#F59E0B",
        "icon": "🏖️",
        "start_date": trip_start.isoformat(),
        "end_date": trip_end.isoformat(),
        "auto_tag_active": True,
        "apply_to_existing": True
    })
    assert res.status_code == 201
    trip_data = res.json()
    assert trip_data["name"] == "Goa Trip"
    assert trip_data["retroactively_tagged_count"] >= 1
    assert trip_data["is_active_trip"] is True

    # Check that txn_in got tagged automatically
    db.refresh(txn_in)
    db.refresh(txn_out)
    assert any(t.name == "Goa Trip" for t in txn_in.tags)
    assert not any(t.name == "Goa Trip" for t in txn_out.tags)

    # Check active trip endpoint
    res = client.get("/api/v1/tags/active-trip")
    assert res.status_code == 200
    active = res.json()["active_trip"]
    assert active is not None
    assert active["name"] == "Goa Trip"

    # Now simulate a NEW SMS arriving during the trip
    from app.core.config import settings
    raw = RawMessage(
        idempotency_key="sms_hdfc_cafe_mambo_123",
        sender="HDFCBK",
        body="Rs 350.00 spent on HDFC Card 1234 at CAFE MAMBO GOA on 02-Oct-26. Avl bal Rs 50000.",
        source="sms",
        device_id=settings.BOOTSTRAP_DEVICE_ID,
        received_at_ms=int(now.timestamp() * 1000),
        received_at_utc=now
    )
    db.add(raw)
    db.commit()

    new_txn = reparse_raw_message(db, raw)
    assert new_txn is not None
    # Auto-tagging must have tagged this new transaction as Goa Trip!
    assert any(t.name == "Goa Trip" for t in new_txn.tags)

    # Now test the user's requirement:
    # "In case there was another transaction that is not part of that tag, later I should be able to use the website to move the tag from that transaction."
    # Remove Goa Trip tag from new_txn
    res = client.delete(f"/api/v1/transactions/{new_txn.id}/tags/Goa Trip")
    assert res.status_code == 200
    assert "Goa Trip" not in res.json()["tags"]

    # Verify that re-evaluating / reparsing does NOT re-tag it due to exclusion!
    db.refresh(new_txn)
    from app.services.tag_service import auto_tag_transaction
    auto_tag_transaction(db, new_txn)
    assert not any(t.name == "Goa Trip" for t in new_txn.tags)
