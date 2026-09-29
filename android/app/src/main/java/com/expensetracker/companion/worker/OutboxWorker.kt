package com.expensetracker.companion.worker

import android.content.Context
import android.util.Log
import androidx.work.*
import com.expensetracker.companion.data.PreferencesManager
import com.expensetracker.companion.data.local.AppDatabase
import com.expensetracker.companion.data.security.CryptoUtils
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

class OutboxWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    private val db = AppDatabase.getDatabase(appContext)
    private val prefs = PreferencesManager(appContext)
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build()

    override suspend fun doWork(): Result {
        val pendingItems = db.outboxDao().getPending(limit = 50)
        if (pendingItems.isEmpty()) {
            return Result.success()
        }

        Log.i(TAG, "Processing ${pendingItems.size} pending outbox items...")

        val serverUrl = prefs.serverUrl
        val deviceId = prefs.deviceId
        val deviceSecret = prefs.deviceSecret

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
                        // Strict rule: delete outbox row ONLY after successful server ACK (2xx)
                        db.outboxDao().deleteById(item.id)
                        Log.d(TAG, "Successfully synced message ${item.id} (status: ${response.code})")
                    } else if (response.code == 401 || response.code == 403) {
                        Log.e(TAG, "Authentication failed with server: ${response.code} ${response.message}")
                        // Stop processing further to prevent burning server on invalid credentials
                        return Result.failure()
                    } else {
                        Log.w(TAG, "Server returned error: ${response.code}. Will retry later.")
                        return Result.retry()
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Network exception syncing outbox: ${e.message}")
                return Result.retry()
            }
        }

        // If there are more pending items, trigger another work request
        if (db.outboxDao().getPendingCount() > 0) {
            enqueue(applicationContext)
        }

        return Result.success()
    }

    companion object {
        private const val TAG = "OutboxWorker"
        private const val UNIQUE_WORK_NAME = "expense_outbox_sync_work"

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
                ExistingWorkPolicy.KEEP,
                workRequest
            )
        }
    }
}
