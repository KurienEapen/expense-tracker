# Android Companion App (Phase 1)

Thin Kotlin companion app to capture financial SMS and notifications, queue them into a durable Room outbox, HMAC sign the payloads, and push them to the FastAPI backend with exponential backoff retry.

---

## 🎯 Architectural Principles

1. **Keep the App Dumb:** No parsing or business logic on the phone. Extraction and deduplication happen on the server.
2. **Durable Outbox:** Room SQLite table stores raw events. Messages are deleted **only** after receiving an HTTP 2xx from the server.
3. **HMAC Signing:** Every request carries `X-Device-Id`, `X-Timestamp`, and `X-Signature` using a device secret stored in EncryptedSharedPreferences.
4. **Idempotency Formula:**
   ```
   sha256(sender + "|" + body + "|" + received_ts_ms)
   ```
5. **Background Resilience:** WorkManager with network constraints (`NetworkType.CONNECTED`) + foreground service exemption to survive OEM background process kills.

---

## 📦 Core Components to Implement in Phase 1

1. **`SmsReceiver`**: Listens for `SMS_RECEIVED`, checks sender against a whitelist (`HDFCBK`, `ICICIB`, `SBICRD`, `AXISBK`, `JUPITR`, `SCAPIA`, etc.), redacts full card numbers (keeps last-4), and inserts into the Room outbox.
2. **`NotificationListener`**: Captures UPI notifications from GPay (`com.google.android.apps.nbu.paisa.user`) and bank apps.
3. **`OutboxWorker` (WorkManager)**: Reads un-sent rows, serializes JSON, signs HMAC-SHA256, POSTs to `/api/v1/ingest`, and deletes upon 2xx status.
4. **`HeartbeatWorker`**: Periodic worker (every 12–24h) posting battery, outbox size, and last SMS timestamp to `/api/v1/heartbeat`.
5. **`SmsBackfillActivity`**: One-time historical SMS reader to bootstrap the Phase 2 parser corpus.
