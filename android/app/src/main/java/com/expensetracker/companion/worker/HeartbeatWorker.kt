package com.expensetracker.companion.worker

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.util.Log
import androidx.work.*
import com.expensetracker.companion.data.PreferencesManager
import com.expensetracker.companion.data.local.AppDatabase
import com.expensetracker.companion.data.security.CryptoUtils
import com.google.gson.JsonObject
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

class HeartbeatWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    private val db = AppDatabase.getDatabase(appContext)
    private val prefs = PreferencesManager(appContext)
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .build()

    override suspend fun doWork(): Result {
        val serverUrl = prefs.serverUrl
        val deviceId = prefs.deviceId
        val deviceSecret = prefs.deviceSecret

        val batteryIntent = applicationContext.registerReceiver(
            null,
            IntentFilter(Intent.ACTION_BATTERY_CHANGED)
        )
        val level = batteryIntent?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
        val scale = batteryIntent?.getIntExtra(BatteryManager.EXTRA_SCALE, -1) ?: -1
        val batteryPct = if (level >= 0 && scale > 0) (level * 100) / scale else null

        val status = batteryIntent?.getIntExtra(BatteryManager.EXTRA_STATUS, -1) ?: -1
        val isCharging = status == BatteryManager.BATTERY_STATUS_CHARGING ||
                status == BatteryManager.BATTERY_STATUS_FULL

        val outboxCount = db.outboxDao().getPendingCount()

        val jsonPayload = JsonObject().apply {
            if (batteryPct != null) addProperty("battery_pct", batteryPct)
            addProperty("is_charging", isCharging)
            addProperty("outbox_count", outboxCount)
            addProperty("app_version", "0.1.0")
        }

        val rawBody = jsonPayload.toString()
        val nowSeconds = System.currentTimeMillis() / 1000
        val signature = CryptoUtils.calculateHmac(deviceSecret, nowSeconds.toString(), rawBody)

        val request = Request.Builder()
            .url("$serverUrl/api/v1/heartbeat")
            .header("X-Device-Id", deviceId)
            .header("X-Timestamp", nowSeconds.toString())
            .header("X-Signature", signature)
            .header("Content-Type", "application/json")
            .post(rawBody.toRequestBody("application/json; charset=utf-8".toMediaType()))
            .build()

        return try {
            httpClient.newCall(request).execute().use { response ->
                if (response.isSuccessful) {
                    Log.i(TAG, "Heartbeat sent successfully (status: ${response.code})")
                    Result.success()
                } else {
                    Log.w(TAG, "Heartbeat failed with code: ${response.code}")
                    Result.retry()
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Heartbeat connection error: ${e.message}")
            Result.retry()
        }
    }

    companion object {
        private const val TAG = "HeartbeatWorker"
        private const val PERIODIC_WORK_NAME = "expense_daily_heartbeat_work"

        fun schedulePeriodic(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val periodicRequest = PeriodicWorkRequestBuilder<HeartbeatWorker>(
                12, TimeUnit.HOURS,
                1, TimeUnit.HOURS
            ).setConstraints(constraints).build()

            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                PERIODIC_WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                periodicRequest
            )
        }
    }
}
