package com.expensetracker.companion.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import android.util.Log
import com.expensetracker.companion.data.PreferencesManager
import com.expensetracker.companion.data.local.AppDatabase
import com.expensetracker.companion.data.local.OutboxEntity
import com.expensetracker.companion.data.security.CryptoUtils
import com.expensetracker.companion.worker.OutboxWorker
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class SmsBroadcastReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return

        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
        if (messages.isNullOrEmpty()) return

        val prefs = PreferencesManager(context)
        val whitelist = prefs.getSenderWhitelistSet()

        // Group multi-part SMS messages by originating address
        val messagesBySender = messages.groupBy { it.originatingAddress ?: "UNKNOWN" }

        for ((rawSender, parts) in messagesBySender) {
            // Normalize Indian telecom headers (e.g. "VK-HDFCBK" -> "HDFCBK", "AD-ICICIB" -> "ICICIB")
            val normalizedSender = rawSender.replace(Regex("^[A-Za-z]{2}-?"), "").uppercase()

            val isWhitelisted = whitelist.any { whitelistedSender ->
                normalizedSender.contains(whitelistedSender) || rawSender.uppercase().contains(whitelistedSender)
            }

            if (!isWhitelisted) {
                Log.d(TAG, "Ignoring non-financial SMS sender: $rawSender (normalized: $normalizedSender)")
                continue
            }

            val fullBody = parts.joinToString("") { it.messageBody ?: "" }
            val receivedAtMs = parts.firstOrNull()?.timestampMillis ?: System.currentTimeMillis()

            // Redact full card numbers, CVVs, OTPs (keeps last-4)
            val redactedBody = CryptoUtils.redactSensitiveInfo(fullBody)
            val idempotencyKey = CryptoUtils.computeIdempotencyKey(normalizedSender, redactedBody, receivedAtMs)

            Log.i(TAG, "Capturing financial SMS from $normalizedSender. Enqueuing to outbox...")

            val pendingResult = goAsync()
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val db = AppDatabase.getDatabase(context)
                    val outboxItem = OutboxEntity(
                        idempotencyKey = idempotencyKey,
                        source = "sms",
                        sender = normalizedSender,
                        appPackage = null,
                        body = redactedBody,
                        receivedAtMs = receivedAtMs,
                        deviceTz = "Asia/Kolkata"
                    )
                    db.outboxDao().insert(outboxItem)
                    OutboxWorker.enqueue(context)
                } catch (e: Exception) {
                    Log.e(TAG, "Error inserting SMS to outbox: ${e.message}")
                } finally {
                    pendingResult.finish()
                }
            }
        }
    }

    companion object {
        private const val TAG = "SmsReceiver"
    }
}
