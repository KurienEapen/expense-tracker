package com.expensetracker.companion.data

import android.content.Context
import android.net.Uri
import android.provider.Telephony
import android.util.Log
import com.expensetracker.companion.data.local.AppDatabase
import com.expensetracker.companion.data.local.OutboxEntity
import com.expensetracker.companion.data.security.CryptoUtils
import com.expensetracker.companion.worker.OutboxWorker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class SmsBackfillHelper(private val context: Context) {

    suspend fun backfillRecentBankSms(daysBack: Int = 90): Int = withContext(Dispatchers.IO) {
        val prefs = PreferencesManager(context)
        val whitelist = prefs.getSenderWhitelistSet()
        val db = AppDatabase.getDatabase(context)

        val cutoffMs = System.currentTimeMillis() - (daysBack.toLong() * 24 * 60 * 60 * 1000)
        val uri: Uri = Telephony.Sms.Inbox.CONTENT_URI
        val projection = arrayOf(
            Telephony.Sms.ADDRESS,
            Telephony.Sms.BODY,
            Telephony.Sms.DATE
        )
        val selection = "${Telephony.Sms.DATE} >= ?"
        val selectionArgs = arrayOf(cutoffMs.toString())
        val sortOrder = "${Telephony.Sms.DATE} ASC"

        var importedCount = 0

        context.contentResolver.query(uri, projection, selection, selectionArgs, sortOrder)?.use { cursor ->
            val addressIdx = cursor.getColumnIndex(Telephony.Sms.ADDRESS)
            val bodyIdx = cursor.getColumnIndex(Telephony.Sms.BODY)
            val dateIdx = cursor.getColumnIndex(Telephony.Sms.DATE)

            while (cursor.moveToNext()) {
                val rawSender = cursor.getString(addressIdx) ?: continue
                val body = cursor.getString(bodyIdx) ?: continue
                val dateMs = cursor.getLong(dateIdx)

                val normalizedSender = rawSender.replace(Regex("^[A-Za-z]{2}-?"), "").uppercase()
                val isWhitelisted = whitelist.any {
                    normalizedSender.contains(it) || rawSender.uppercase().contains(it)
                }
                val isFinancial = com.expensetracker.companion.receiver.SmsBroadcastReceiver.isFinancialSms(body)

                if (!isWhitelisted && !isFinancial) continue

                val redactedBody = CryptoUtils.redactSensitiveInfo(body)
                val idempotencyKey = CryptoUtils.computeIdempotencyKey(normalizedSender, redactedBody, dateMs)

                val entity = OutboxEntity(
                    idempotencyKey = idempotencyKey,
                    source = "sms",
                    sender = normalizedSender,
                    body = redactedBody,
                    receivedAtMs = dateMs,
                    deviceTz = "Asia/Kolkata"
                )

                val rowId = db.outboxDao().insert(entity)
                if (rowId > 0) {
                    importedCount++
                }
            }
        }

        if (importedCount > 0) {
            Log.i("SmsBackfillHelper", "Enqueued $importedCount historical bank SMS to outbox.")
            OutboxWorker.enqueue(context)
        }

        importedCount
    }
}
