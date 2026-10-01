from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_split_and_unsplit_transaction():
    # 1. Fetch transactions list
    txns_res = client.get("/api/v1/transactions")
    assert txns_res.status_code == 200
    txns = txns_res.json()
    assert len(txns) > 0

    target_txn = next(t for t in txns if t["transaction_type"] == "debit")
    txn_id = target_txn["id"]
    total_inr = target_txn["amount_inr"]
    half_share = round(total_inr / 2.0, 2)

    # 2. Split Bill with 1/2 ratio preset
    split_res = client.post(f"/api/v1/transactions/{txn_id}/split", json={
        "my_share_inr": half_share,
        "ratio_label": "1/2"
    })
    assert split_res.status_code == 200
    data = split_res.json()
    assert data["is_split"] is True
    assert data["my_share_inr"] == half_share
    assert data["reimbursable_inr"] == round(total_inr - half_share, 2)
    assert data["split_ratio_label"] == "1/2"

    # 3. Check summary stats reflects net personal spend & net receivables
    stats_res = client.get("/api/v1/transactions/stats/summary")
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert "net_receivables_inr" in stats_data
    assert stats_data["net_receivables_inr"] >= round(total_inr - half_share, 2)

    # 4. Unsplit transaction
    unsplit_res = client.post(f"/api/v1/transactions/{txn_id}/unsplit")
    assert unsplit_res.status_code == 200
    unsplit_data = unsplit_res.json()
    assert unsplit_data["is_split"] is False
    assert unsplit_data["reimbursable_inr"] == 0.0
