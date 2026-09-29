package com.expensetracker.companion.ui

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import android.view.View
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.expensetracker.companion.R
import com.expensetracker.companion.data.PreferencesManager
import com.expensetracker.companion.data.SmsBackfillHelper
import com.expensetracker.companion.data.local.AppDatabase
import com.expensetracker.companion.databinding.ActivityMainBinding
import com.expensetracker.companion.worker.OutboxWorker
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var prefs: PreferencesManager
    private var isSettingsVisible = false

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .build()

    private val requestSmsPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val smsGranted = permissions[Manifest.permission.RECEIVE_SMS] == true
        val readGranted = permissions[Manifest.permission.READ_SMS] == true
        updatePermissionTiles()
        if (smsGranted && readGranted) {
            showSnackbar("SMS permissions granted! Bank messages will now be captured.")
        } else {
            showSnackbar("SMS permissions needed — tap the SMS tile to try again.", isError = true)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        prefs = PreferencesManager(this)
        initViews()
        observeOutbox()
        checkServerHealth()
    }

    override fun onResume() {
        super.onResume()
        updatePermissionTiles()
    }

    private fun initViews() {
        // Load saved settings into fields
        binding.etServerUrl.setText(prefs.serverUrl)
        binding.etDeviceId.setText(prefs.deviceId)
        binding.etDeviceSecret.setText(prefs.deviceSecret)

        // Settings toggle button
        binding.btnToggleSettings.setOnClickListener {
            isSettingsVisible = !isSettingsVisible
            binding.cardSettings.visibility = if (isSettingsVisible) View.VISIBLE else View.GONE
            binding.btnToggleSettings.text = if (isSettingsVisible) "Done" else "Settings"
        }

        // Save settings
        binding.btnSaveSettings.setOnClickListener {
            prefs.serverUrl = binding.etServerUrl.text.toString()
            prefs.deviceId = binding.etDeviceId.text.toString()
            prefs.deviceSecret = binding.etDeviceSecret.text.toString()
            isSettingsVisible = false
            binding.cardSettings.visibility = View.GONE
            binding.btnToggleSettings.text = "Settings"
            showSnackbar("Configuration saved.")
            checkServerHealth()
        }

        // Hero outbox card actions
        binding.btnSyncNow.setOnClickListener {
            OutboxWorker.enqueue(this)
            showSnackbar("Outbox sync enqueued — messages will deliver when network is available.")
        }

        binding.btnCheckServer.setOnClickListener {
            checkServerHealth()
        }

        // Pull-to-refresh
        binding.swipeRefresh.setOnRefreshListener {
            checkServerHealth()
            binding.swipeRefresh.isRefreshing = false
        }

        // Permission tiles — tap to request/open settings
        binding.cardSmsPermission.setOnClickListener {
            val smsGranted = ContextCompat.checkSelfPermission(
                this, Manifest.permission.RECEIVE_SMS
            ) == PackageManager.PERMISSION_GRANTED
            if (!smsGranted) {
                requestSmsPermissionLauncher.launch(
                    arrayOf(
                        Manifest.permission.RECEIVE_SMS,
                        Manifest.permission.READ_SMS
                    )
                )
            }
        }

        binding.cardNotifPermission.setOnClickListener {
            startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        }

        binding.cardBatteryOpt.setOnClickListener {
            requestBatteryOptimizationExemption()
        }

        // Backfill tile
        binding.btnBackfillAction.setOnClickListener {
            val smsGranted = ContextCompat.checkSelfPermission(
                this, Manifest.permission.READ_SMS
            ) == PackageManager.PERMISSION_GRANTED

            if (!smsGranted) {
                showSnackbar("Grant SMS read permission first — tap the SMS tile above.", isError = true)
                return@setOnClickListener
            }
            binding.btnBackfillAction.isEnabled = false
            binding.btnBackfillAction.text = "Scanning..."
            lifecycleScope.launch {
                val count = SmsBackfillHelper(this@MainActivity).backfillRecentBankSms(90)
                binding.btnBackfillAction.isEnabled = true
                binding.btnBackfillAction.text = "Backfill"
                if (count > 0) {
                    showSnackbar("$count historical bank messages queued for server sync.")
                } else {
                    showSnackbar("No new bank messages found in last 90 days.")
                }
            }
        }
    }

    private fun observeOutbox() {
        val db = AppDatabase.getDatabase(this)
        lifecycleScope.launch {
            db.outboxDao().getPendingCountFlow().collect { count ->
                // Hero large number counter
                binding.tvOutboxLargeCount.text = count.toString()
            }
        }
    }

    private fun checkServerHealth() {
        val serverUrl = prefs.serverUrl
        binding.tvServerBadge.text = "Checking..."
        binding.tvServerBadge.setTextColor(ContextCompat.getColor(this, R.color.text_secondary))
        binding.tvServerBadge.background = null

        lifecycleScope.launch(Dispatchers.IO) {
            val request = Request.Builder()
                .url("$serverUrl/api/v1/health")
                .get()
                .build()

            try {
                httpClient.newCall(request).execute().use { response ->
                    withContext(Dispatchers.Main) {
                        if (response.isSuccessful) {
                            binding.tvServerBadge.text = "Connected"
                            binding.tvServerBadge.setTextColor(
                                ContextCompat.getColor(this@MainActivity, R.color.status_healthy)
                            )
                            binding.tvServerBadge.setBackgroundResource(R.drawable.badge_pill_healthy)
                        } else {
                            binding.tvServerBadge.text = "HTTP ${response.code}"
                            binding.tvServerBadge.setTextColor(
                                ContextCompat.getColor(this@MainActivity, R.color.status_error)
                            )
                            binding.tvServerBadge.setBackgroundResource(R.drawable.badge_pill_error)
                        }
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.tvServerBadge.text = "Unreachable"
                    binding.tvServerBadge.setTextColor(
                        ContextCompat.getColor(this@MainActivity, R.color.status_error)
                    )
                    binding.tvServerBadge.setBackgroundResource(R.drawable.badge_pill_error)
                }
            }
        }
    }

    private fun updatePermissionTiles() {
        // SMS tile
        val smsGranted = ContextCompat.checkSelfPermission(
            this, Manifest.permission.RECEIVE_SMS
        ) == PackageManager.PERMISSION_GRANTED
        binding.tvSmsStatusBadge.text = if (smsGranted) "Active" else "Grant"
        binding.tvSmsStatusBadge.setTextColor(
            ContextCompat.getColor(
                this,
                if (smsGranted) R.color.status_healthy else R.color.status_warning
            )
        )
        binding.tvSmsStatusBadge.setBackgroundResource(
            if (smsGranted) R.drawable.badge_pill_healthy else R.drawable.badge_pill_warning
        )
        binding.cardSmsPermission.isClickable = !smsGranted

        // Notification listener tile
        val notifGranted = isNotificationServiceEnabled()
        binding.tvNotifStatusBadge.text = if (notifGranted) "Active" else "Enable"
        binding.tvNotifStatusBadge.setTextColor(
            ContextCompat.getColor(
                this,
                if (notifGranted) R.color.status_healthy else R.color.status_warning
            )
        )
        binding.tvNotifStatusBadge.setBackgroundResource(
            if (notifGranted) R.drawable.badge_pill_healthy else R.drawable.badge_pill_warning
        )
        binding.cardNotifPermission.isClickable = !notifGranted

        // Battery tile
        val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
        val batteryExempt = pm.isIgnoringBatteryOptimizations(packageName)
        binding.tvBatteryStatusBadge.text = if (batteryExempt) "Exempt" else "Request"
        binding.tvBatteryStatusBadge.setTextColor(
            ContextCompat.getColor(
                this,
                if (batteryExempt) R.color.status_healthy else R.color.status_warning
            )
        )
        binding.tvBatteryStatusBadge.setBackgroundResource(
            if (batteryExempt) R.drawable.badge_pill_healthy else R.drawable.badge_pill_warning
        )
        binding.cardBatteryOpt.isClickable = !batteryExempt
    }

    private fun isNotificationServiceEnabled(): Boolean {
        val flat = Settings.Secure.getString(contentResolver, "enabled_notification_listeners")
        return flat != null && flat.contains(packageName)
    }

    private fun requestBatteryOptimizationExemption() {
        val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
        if (!pm.isIgnoringBatteryOptimizations(packageName)) {
            startActivity(
                Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                    data = Uri.parse("package:$packageName")
                }
            )
        }
    }

    /**
     * Anchored Snackbar replacing all Toast calls.
     * Supports an optional Retry action when [isError] is true.
     */
    private fun showSnackbar(message: String, isError: Boolean = false) {
        val snackbar = Snackbar.make(binding.root, message, Snackbar.LENGTH_LONG)
        if (isError) {
            snackbar.setActionTextColor(ContextCompat.getColor(this, R.color.status_warning))
        }
        snackbar.show()
    }
}
