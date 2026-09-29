# Personal Expense Tracker

Automatic capture of credit card, debit card, and UPI transactions from SMS and phone notifications, with counterparty-aware splits, statement reconciliation, and a lightweight self-hosted backend.

---

## 🏗️ Architecture & Quick Reference

* **Phone Client:** Kotlin Companion App (Room outbox + WorkManager exponential backoff retry + HMAC signing).
* **Ingestion Backend:** FastAPI + SQLite with WAL mode (`PRAGMA journal_mode = WAL; PRAGMA synchronous = NORMAL;`).
* **Ingress:** Dedicated subdomain (e.g. `expense.yourdomain.com`) reverse-proxied through Nginx on Port `8000`.
* **Process Manager:** PM2 (running as `kurieneapenk_dev` on GCP VM).
* **Testing:** Pytest contract test suite enforcing HMAC signatures, timestamp skew replay protection, and idempotency key uniqueness.

---

## 📁 Repository Layout

```
expense-tracker/
├── backend/
│   ├── app/
│   │   ├── api/             # API v1 routes & dependencies (deps.py)
│   │   │   └── v1/endpoints # /ingest, /heartbeat, /health
│   │   ├── core/            # config.py, security.py (HMAC/idempotency), database.py
│   │   ├── models/          # SQLAlchemy models (devices, raw_messages, heartbeats)
│   │   └── schemas/         # Pydantic contract schemas (IngestPayload, HeartbeatPayload)
│   ├── tests/               # Contract test suite (test_contract.py)
│   └── main.py              # FastAPI application entrypoint
├── scripts/
│   └── mock_phone_client.py # CLI simulator to test HMAC-signed ingests & heartbeats
├── deploy/
│   └── nginx/               # Nginx server block for expense.yourdomain.com
├── docs/
│   └── PROJECT_PLAN_v3.1.md # Full architectural project plan
├── ecosystem.config.js      # PM2 configuration for GCP VM
└── requirements.txt         # Backend Python dependencies
```

---

## 🚀 Local Development

1. **Activate virtual environment:**
   ```bash
   cd /Users/kurieneapen/Projects/expense-tracker
   source .venv/bin/activate
   ```

2. **Run contract tests:**
   ```bash
   pytest backend/tests/test_contract.py -v
   ```

3. **Start local API server:**
   ```bash
   cd backend
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

4. **Simulate phone companion ingestion:**
   ```bash
   python scripts/mock_phone_client.py --action all
   ```

---

## ☁️ Deployment on GCP VM (`e2-micro`)

The application is optimized for low memory usage (< 50MB RSS), running safely alongside `ipo-wise-bot`:

1. **Clone repository to VM:**
   ```bash
   cd /home/kurieneapenk_dev/
   git clone <repo-url> expense-tracker
   cd expense-tracker
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Nginx Subdomain:**
   Copy `deploy/nginx/expense.domain.com.conf` to `/etc/nginx/sites-available/expense.yourdomain.com` and enable it:
   ```bash
   sudo ln -s /etc/nginx/sites-available/expense.yourdomain.com /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   sudo certbot --nginx -d expense.yourdomain.com
   ```

3. **Start & Register Process with PM2:**
   ```bash
   pm2 start ecosystem.config.js
   pm2 save
   ```
