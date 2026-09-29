# Product

<!-- impeccable:product-schema 1 -->

## Platform
adaptive

## Stack
Vite + React / TypeScript (PWA frontend) + FastAPI (Python 3.12 backend) + SQLite (WAL mode) + Android Companion (Native Kotlin)

## Users
Single personal user tracking daily expenses, group splits, and monthly card settlements in India across multiple payment cards and UPI accounts.

## Product Purpose
Automatically captures credit card, debit card, and UPI/GPay transactions via a native Android companion app and notification listener, routes raw messages to a lightweight self-hosted backend, computes true net personal expenses via counterparty-aware double-entry accounting, and reconciles monthly statements with zero silent loss.

## Positioning
Unlike Splitwise, counterparties and settlements are tracked as your own personal ledger assets/liabilities with 1-tap settlement matching. Unlike commercial expense trackers, no financial screenshots or unredacted credentials leave your private infrastructure; it operates on a free-tier 1 GB VM with zero cloud database overhead.

## Operating Context
- Real-time notification swipes and SMS arrivals on an Android device on Indian telecom networks.
- On-the-go review of splits ("Mine", "Split", "Skip") via phone notifications, Telegram bot, or PWA.
- End-of-month reconciliation of password-protected or CSV bank statements via PWA drag-and-drop.
- Free-tier GCP VM (`e2-micro`, 1GB RAM) running alongside `ipo-wise-bot` behind Nginx.

## Capabilities and Constraints
- **9 Cards across 7 Banks:** HDFC, HSBC (credit + debit), ICICI (credit + debit), SBI, Federal (Scapia), CSB (Jupiter), Axis (Indian Oil).
- **UPI / GPay:** Funding bank tagged as metadata; bank account balances are not tracked.
- **Cash:** Manual entry support with asset account representation.
- **Durable Storage:** Store raw messages first, parse later.
- **Double-Entry Ledger:** Signed integer paise arithmetic; net personal expense is a dynamic query over category debits.
- **Privacy & Security:** PII redacted on-device; requests HMAC-SHA256 signed with replay protection.
- **Reconciliation:** 3-way gap report (Missing from SMS, Orphaned SMS, Amount Mismatches).

## Brand Commitments
- Name: Personal Expense Tracker
- Tone: Crisp, quiet, utilitarian luxury, trustworthy, highly legible financial data presentation.
- Visuals: Dark & light theme, dense data density without visual clutter, tabular numbers, clear debit/credit contrast.

## Evidence on Hand
- Full architectural plan: `docs/PROJECT_PLAN_v3.1.md`.
- Phase 0 backend contract tests: `backend/tests/test_contract.py`.
- Phase 1 Android Kotlin companion app: `android/`.

## Product Principles
1. **Never Silently Lose a Transaction:** Store raw first; if a format changes or parsing fails, route to `needs_review` and reparse historically.
2. **True Personal Net Expense:** When you pay for others, it's a receivable, not your expense; when others pay for you, it's a payable virtual expense.
3. **Extreme Resource Efficiency:** Zero node/python daemon bloat in production; runs comfortably in < 50MB RAM on a 1GB shared VM.
4. **Deterministic Precision over LLM Hallucinations:** Deterministic regex templates extract exact amounts and dates; AI is reserved strictly for non-destructive classification.
