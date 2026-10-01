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

            val fullBody = parts.joinToString("") { it.messageBody ?: "" }
            val isFinancialContent = isFinancialSms(fullBody)

            if (!isWhitelisted && !isFinancialContent) {
                Log.d(TAG, "Ignoring non-financial SMS sender: $rawSender (normalized: $normalizedSender)")
                continue
            }
            val receivedAtMs = parts.firstOrNull()?.timestampMillis ?: System.currentTimeMillis()

            // Redact full card numbers, CVVs, OTPs (keeps last-4)
            val redactedBody = CryptoUtils.redactSensitiveInfo(fullBody)
            val idempotencyKey = CryptoUtils.computeIdempotencyKey(normalizedSender, redactedBody, receivedAtMs)

            Log.i(TAG, "Capturing financial SMS from $normalizedSender. Enqueuing to outbox...")

            // Capture phone location if permissions granted
            var locationJson: String? = null
            try {
                if (androidx.core.content.ContextCompat.checkSelfPermission(context, android.Manifest.permission.ACCESS_FINE_LOCATION) == android.content.pm.PackageManager.PERMISSION_GRANTED ||
                    androidx.core.content.ContextCompat.checkSelfPermission(context, android.Manifest.permission.ACCESS_COARSE_LOCATION) == android.content.pm.PackageManager.PERMISSION_GRANTED) {
                    
                    val locationManager = context.getSystemService(Context.LOCATION_SERVICE) as? android.location.LocationManager
                    val lastGps = locationManager?.getLastKnownLocation(android.location.LocationManager.GPS_PROVIDER)
                    val lastNet = locationManager?.getLastKnownLocation(android.location.LocationManager.NETWORK_PROVIDER)
                    val bestLocation = if (lastGps != null && lastNet != null) {
                        if (lastGps.time > lastNet.time) lastGps else lastNet
                    } else lastGps ?: lastNet

                    if (bestLocation != null) {
                        locationJson = """{"lat": ${bestLocation.latitude}, "lng": ${bestLocation.longitude}}"""
                        Log.d(TAG, "Captured location coordinates: ${bestLocation.latitude}, ${bestLocation.longitude}")
                    }
                }
            } catch (e: Exception) {
                Log.w(TAG, "Failed to capture location: ${e.message}")
            }

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
                        deviceTz = "Asia/Kolkata",
                        locationJson = locationJson
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

        fun isFinancialSms(body: String): Boolean {
            val lower = body.lowercase()
            val hasAmount = lower.contains("rs.") || lower.contains("rs ") || lower.contains("inr") || lower.contains("₹")
            val hasAction = lower.contains("spent") || lower.contains("debited") || lower.contains("credited") ||
                    lower.contains("paid") || lower.contains("withdrawn") || lower.contains("transferred") ||
                    lower.contains("txn") || lower.contains("card no") || lower.contains("wallet") ||
                    lower.contains("bal")
            return hasAmount && hasAction
        }
    }
}
