package com.expensetracker.companion.receiver

import android.app.NotificationManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.expensetracker.companion.data.PreferencesManager
import com.google.gson.JsonObject
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

class CategoryActionReceiver : BroadcastReceiver() {

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .build()

    override fun onReceive(context: Context, intent: Intent) {
        val txnId = intent.getIntExtra(EXTRA_TXN_ID, -1)
        val category = intent.getStringExtra(EXTRA_CATEGORY) ?: return
        val notifId = intent.getIntExtra(EXTRA_NOTIFICATION_ID, txnId)

        if (txnId <= 0) return

        Log.i(TAG, "User selected category '$category' for txn #$txnId from notification")

        // Dismiss the notification immediately for snappy user experience
        val notifManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        notifManager.cancel(notifId)

        // Asynchronously post to backend
        val prefs = PreferencesManager(context)
        val serverUrl = prefs.serverUrl.trim().trimEnd('/')

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val jsonPayload = JsonObject().apply {
                    addProperty("category", category)
                }
                val reqBody = jsonPayload.toString().toRequestBody("application/json; charset=utf-8".toMediaType())

                val request = Request.Builder()
                    .url("$serverUrl/api/v1/categories/$txnId/categorize")
                    .post(reqBody)
                    .build()

                httpClient.newCall(request).execute().use { response ->
                    if (response.isSuccessful) {
                        Log.i(TAG, "Successfully categorized txn #$txnId as '$category'. Merchant memory learned.")
                    } else {
                        Log.w(TAG, "Failed to submit category: HTTP ${response.code}")
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Network exception submitting category: ${e.message}")
            }
        }
    }

    companion object {
        private const val TAG = "CategoryActionReceiver"
        const val EXTRA_TXN_ID = "extra_txn_id"
        const val EXTRA_CATEGORY = "extra_category"
        const val EXTRA_NOTIFICATION_ID = "extra_notification_id"
    }
}
