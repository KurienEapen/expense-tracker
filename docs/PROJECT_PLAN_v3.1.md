# Personal Expense Tracker: Project Plan (v3.1)

Automatic capture of credit card, bank and UPI transactions from SMS and notifications, with counterparty-aware splits, statement reconciliation and a lightweight self-hosted backend.

**Status:** In Progress (Phase 0 Complete, Phase 1 Underway)  
**Last updated:** 29 Sep 2026

---

## 1. Goals and non-goals

### Goals
1. Capture every transaction from your credit cards, debit cards and UPI/GPay with no manual entry for the normal case. Cash is supported as an optional manual entry.
2. Never silently lose a transaction. Anything missed must be detectable (reconciliation).
3. Compute true personal net expense when paying for groups or when others pay for you.
4. Survive format changes: adding or fixing a bank format is a data change, not a code deploy.
5. Run on a free-tier 1 GB VM. Keep all images and heavy work on the phone.

### Non-goals (for now)
- Multi-user app (Splitwise-style). Counterparties are just names in your own ledger.
- Investment, loan or net-worth tracking.
- Uploading screenshots to any server. Images never leave the phone.
- Play Store distribution. The app is sideloaded for personal use.

---

## 2. Key decisions (locked unless noted)

| # | Decision | Choice | Reason |
|---|---|---|---|
| D1 | Phone client | **Thin Kotlin companion app** (Tasker only as an optional stopgap) | Durable outbox, HMAC, ML Kit OCR, share sheet, SMS backfill are all native |
| D2 | Ingestion principle | **Store raw first, parse later** | Parsers rot; raw history lets you re-parse |
| D3 | Parsing | **Template registry (regex, data-driven)** plus generic fallback | Handles 5+ banks and drift |
| D4 | Jev role | **Classifier only**, never an extractor | Jev returns typed decisions (Choice / Score / Noul), not free text |
| D5 | Dedup | **Layered:** idempotency key, then strong reference, then fuzzy fingerprint | Sources differ in what identifiers they carry |
| D6 | Ledger | **Double-entry, signed integer paise, counterparty-aware** | Net expense is a query, not a stored split |
| D7 | Safety net | **Monthly statement import and reconciliation** | Only ground truth catches misses |
| D8 | Backend | **FastAPI + SQLite (WAL) with Litestream continuous replication off the VM**, SQLAlchemy + Alembic so Postgres stays an option | ~1 KB posts won't stress 1 GB RAM. Single user means a single writer is fine, and there is no Postgres process eating RAM |
| D9 | Location | **Optional, async, best-effort, coarse** | GPS reflects where you were at SMS time, not the merchant |
| D10 | OCR | **On-device ML Kit**, send text only | Privacy and efficiency |
| D11 | Alerts | **Telegram bot** (heartbeat, parse failures, reconciliation, optional quick actions) | Simple, free, works on any phone |
| D12 | Bank accounts | **Not tracked as ledger accounts.** UPI is recorded as an expense, settlement or income, with the funding bank kept as a tag | All bank activity is via UPI for now |
| D13 | Cash | **Provision built in, manual entry only** | Cheap to support now, painful to retrofit |
| D14 | Build method | **AI coding agent builds the app**, guided by specs, contract tests and human review of risky parts | See section 12b |
| D15 | Ingress | **Dedicated subdomain (expense.domain.com)** on Port 8000 via Nginx | Clean separation alongside existing /ipo/ service |
