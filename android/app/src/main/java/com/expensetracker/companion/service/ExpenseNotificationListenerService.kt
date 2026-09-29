package com.expensetracker.companion.service

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import com.expensetracker.companion.data.PreferencesManager
import com.expensetracker.companion.data.local.AppDatabase
import com.expensetracker.companion.data.local.OutboxEntity
import com.expensetracker.companion.data.security.CryptoUtils
import com.expensetracker.companion.worker.OutboxWorker
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class ExpenseNotificationListenerService : NotificationListenerService() {

    private val serviceScope = CoroutineScope(Dispatchers.IO)
    private val financialKeywordsRegex = Regex("""(?i)\b(paid|debited|spent|received|sent|credited|transfer|₹|INR|Rs\.?)\b""")

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        super.onNotificationPosted(sbn)
        if (sbn == null) return

        val packageName = sbn.packageName ?: return
        val prefs = PreferencesManager(applicationContext)
        val appWhitelist = prefs.getAppWhitelistSet()

        if (!appWhitelist.contains(packageName)) {
            return
        }

        val extras = sbn.notification.extras ?: return
        val title = extras.getString(Notification.EXTRA_TITLE) ?: ""
        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString() ?: ""
        val bigText = extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString() ?: ""

        val rawBody = when {
            bigText.isNotEmpty() -> "$title: $bigText"
            text.isNotEmpty() -> "$title: $text"
            else -> title
        }

        // Only capture notifications containing monetary or transactional keywords
        if (!financialKeywordsRegex.containsMatchIn(rawBody)) {
            Log.d(TAG, "Ignoring non-financial notification from $packageName: $rawBody")
            return
        }

        val receivedAtMs = sbn.postTime
        val redactedBody = CryptoUtils.redactSensitiveInfo(rawBody)
        val idempotencyKey = CryptoUtils.computeIdempotencyKey(packageName, redactedBody, receivedAtMs)

        Log.i(TAG, "Capturing notification from $packageName. Enqueuing to outbox...")

        serviceScope.launch {
            try {
                val db = AppDatabase.getDatabase(applicationContext)
                val outboxItem = OutboxEntity(
                    idempotencyKey = idempotencyKey,
                    source = "notification",
                    sender = packageName,
                    appPackage = packageName,
                    body = redactedBody,
                    receivedAtMs = receivedAtMs,
                    deviceTz = "Asia/Kolkata"
                )
                db.outboxDao().insert(outboxItem)
                OutboxWorker.enqueue(applicationContext)
            } catch (e: Exception) {
                Log.e(TAG, "Failed saving notification to outbox: ${e.message}")
            }
        }
    }

    companion object {
        private const val TAG = "NotificationListener"
    }
}
