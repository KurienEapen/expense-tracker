package com.expensetracker.companion.worker

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.work.*
import com.expensetracker.companion.data.PreferencesManager
import com.expensetracker.companion.data.local.AppDatabase
import com.expensetracker.companion.data.security.CryptoUtils
import com.expensetracker.companion.receiver.CategoryActionReceiver
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.Locale
import java.util.concurrent.TimeUnit

class OutboxWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result {
        val synced = syncOutboxDirect(applicationContext)
        val remaining = AppDatabase.getDatabase(applicationContext).outboxDao().getPendingCount()
        return if (remaining > 0 && synced == 0) {
            Result.retry()
        } else {
            Result.success()
        }
    }

    companion object {
        private const val TAG = "OutboxWorker"
        private const val UNIQUE_WORK_NAME = "expense_outbox_sync_work"
        private const val CHANNEL_ID = "expense_ambiguity_channel"

        suspend fun syncOutboxDirect(context: Context): Int {
            val db = AppDatabase.getDatabase(context)
            val prefs = PreferencesManager(context)
            val httpClient = OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(15, TimeUnit.SECONDS)
                .build()

            var totalSynced = 0
            while (true) {
                val pendingItems = db.outboxDao().getPending(limit = 50)
                if (pendingItems.isEmpty()) {
                    break
                }

                val serverUrl = prefs.serverUrl.trim().trimEnd('/')
                val deviceId = prefs.deviceId.trim()
                val deviceSecret = prefs.deviceSecret.trim()

                var batchSuccessCount = 0
                for (item in pendingItems) {
                    val jsonPayload = JsonObject().apply {
                        addProperty("idempotency_key", item.idempotencyKey)
                        addProperty("source", item.source)
                        addProperty("sender", item.sender)
                        if (item.appPackage != null) {
                            addProperty("app_package", item.appPackage)
                        } else {
                            add("app_package", null)
                        }
                        addProperty("body", item.body)
                        addProperty("received_at_ms", item.receivedAtMs)
                        addProperty("device_tz", item.deviceTz)
                        if (item.locationJson != null) {
                            try {
                                add("location", JsonParser.parseString(item.locationJson))
                            } catch (e: Exception) {
                                add("location", null)
                            }
                        } else {
                            add("location", null)
                        }
                        if (item.ocrConfidence != null) {
                            addProperty("ocr_confidence", item.ocrConfidence)
                        } else {
                            add("ocr_confidence", null)
                        }
                        addProperty("app_version", item.appVersion)
                    }

                    val rawBody = jsonPayload.toString()
                    val nowSeconds = System.currentTimeMillis() / 1000
                    val signature = CryptoUtils.calculateHmac(deviceSecret, nowSeconds.toString(), rawBody)

                    val request = Request.Builder()
                        .url("$serverUrl/api/v1/ingest")
                        .header("X-Device-Id", deviceId)
                        .header("X-Timestamp", nowSeconds.toString())
                        .header("X-Signature", signature)
                        .header("Content-Type", "application/json")
                        .post(rawBody.toRequestBody("application/json; charset=utf-8".toMediaType()))
                        .build()

                    try {
                        httpClient.newCall(request).execute().use { response ->
                            if (response.isSuccessful) {
                                val respBodyStr = response.body?.string()
                                db.outboxDao().deleteById(item.id)
                                batchSuccessCount++
                                totalSynced++
                                Log.d(TAG, "Synced message ${item.id} (status: ${response.code})")

                                // If ambiguous, trigger actionable 1-tap review notification
                                if (!respBodyStr.isNullOrEmpty()) {
                                    try {
                                        val respJson = JsonParser.parseString(respBodyStr).asJsonObject
                                        val needsReview = respJson.get("needs_review")?.asBoolean ?: false
                                        val txnId = respJson.get("parsed_transaction_id")?.let { if (it.isJsonNull) -1 else it.asInt } ?: -1
                                        val merchant = respJson.get("merchant")?.let { if (it.isJsonNull) null else it.asString }
                                        val amountInr = respJson.get("amount_inr")?.let { if (it.isJsonNull) null else it.asDouble }

                                        if (needsReview && txnId > 0 && amountInr != null) {
                                            val locationName = respJson.get("location_name")?.let { if (it.isJsonNull) null else it.asString }
                                            showAmbiguityNotification(context, txnId, merchant ?: "Unknown", amountInr, locationName)
                                        }
                                    } catch (e: Exception) {
                                        Log.w(TAG, "Error checking ambiguity review: ${e.message}")
                                    }
                                }
                            } else if (response.code == 401 || response.code == 403) {
                                Log.e(TAG, "Authentication failed with server: ${response.code} ${response.message}")
                                return totalSynced
                            } else {
                                Log.w(TAG, "Server returned error: ${response.code}")
                                return totalSynced
                            }
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Network exception syncing outbox: ${e.message}")
                        return totalSynced
                    }
                }

                if (batchSuccessCount == 0) {
                    break
                }
            }
            return totalSynced
        }

        private fun showAmbiguityNotification(
            context: Context,
            txnId: Int,
            merchant: String,
            amountInr: Double,
            locationName: String? = null
        ) {
            val notifManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val channel = NotificationChannel(
                    CHANNEL_ID,
                    "Expense Category Review",
                    NotificationManager.IMPORTANCE_HIGH
                ).apply {
                    description = "Prompts for 1-tap categorization only when merchant is ambiguous"
                }
                notifManager.createNotificationChannel(channel)
            }

            fun createAction(categoryLabel: String, categoryVal: String, reqCode: Int): NotificationCompat.Action {
                val intent = Intent(context, CategoryActionReceiver::class.java).apply {
                    putExtra(CategoryActionReceiver.EXTRA_TXN_ID, txnId)
                    putExtra(CategoryActionReceiver.EXTRA_CATEGORY, categoryVal)
                    putExtra(CategoryActionReceiver.EXTRA_NOTIFICATION_ID, txnId)
                }
                val pendingIntent = PendingIntent.getBroadcast(
                    context,
                    reqCode + (txnId * 10),
                    intent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
                return NotificationCompat.Action.Builder(0, categoryLabel, pendingIntent).build()
            }

            val formattedAmount = String.format(Locale.getDefault(), "₹%.2f", amountInr)
            val subText = if (!locationName.isNullOrBlank()) "$locationName • Tap category to save:" else "Tap category to save and remember:"
            val notif = NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle("$formattedAmount at $merchant")
                .setContentText(subText)
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .addAction(createAction("🍔 Dining", "Food & Dining", 1))
                .addAction(createAction("🛒 Groceries", "Groceries & Essentials", 2))
                .addAction(createAction("🛍️ Shopping", "Shopping & E-Commerce", 3))
                .build()

            notifManager.notify(txnId, notif)
        }

        fun enqueue(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val workRequest = OneTimeWorkRequestBuilder<OutboxWorker>()
                .setConstraints(constraints)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    15,
                    TimeUnit.SECONDS
                )
                .build()

            WorkManager.getInstance(context).enqueueUniqueWork(
                UNIQUE_WORK_NAME,
                ExistingWorkPolicy.REPLACE,
                workRequest
            )
        }
    }
}
