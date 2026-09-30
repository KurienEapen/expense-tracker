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
import com.expensetracker.companion.data.model.UnreviewedTransaction
import com.google.android.material.snackbar.Snackbar
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
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
        fetchUnreviewedCount()
    }

    override fun onResume() {
        super.onResume()
        updatePermissionTiles()
        fetchUnreviewedCount()
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

        binding.btnOpenIgnoredRules.setOnClickListener {
            IgnoredRulesBottomSheetFragment.newInstance()
                .show(supportFragmentManager, IgnoredRulesBottomSheetFragment.TAG)
        }

        // Hero outbox card actions
        binding.btnSyncNow.setOnClickListener {
            binding.btnSyncNow.isEnabled = false
            lifecycleScope.launch {
                val db = AppDatabase.getDatabase(this@MainActivity)
                val count = withContext(Dispatchers.IO) { db.outboxDao().getPendingCount() }
                if (count == 0) {
                    showSnackbar("Outbox is empty — tap 'Backfill' below to scan recent bank SMS.")
                    binding.btnSyncNow.isEnabled = true
                    return@launch
                }
                showSnackbar("Syncing $count message${if (count > 1) "s" else ""} to server...")
                val synced = withContext(Dispatchers.IO) {
                    OutboxWorker.syncOutboxDirect(this@MainActivity)
                }
                binding.btnSyncNow.isEnabled = true
                if (synced > 0) {
                    showSnackbar("Successfully synced $synced message${if (synced > 1) "s" else ""} to server!")
                    fetchUnreviewedCount()
                } else {
                    showSnackbar("Sync failed — please check if server is reachable.", isError = true)
                }
            }
        }

        binding.btnCheckServer.setOnClickListener {
            checkServerHealth()
        }

        // In-App Ambiguity Review card actions
        binding.cardUnreviewedReview.setOnClickListener {
            openReviewBottomSheet()
        }
        binding.btnOpenReview.setOnClickListener {
            openReviewBottomSheet()
        }

        // Pull-to-refresh
        binding.swipeRefresh.setOnRefreshListener {
            checkServerHealth()
            fetchUnreviewedCount()
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
                            fetchUnreviewedCount()
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

    private fun openReviewBottomSheet() {
        val sheet = UnreviewedBottomSheetFragment.newInstance()
        sheet.onDismissCallback = {
            fetchUnreviewedCount()
        }
        sheet.show(supportFragmentManager, UnreviewedBottomSheetFragment.TAG)
    }

    private fun fetchUnreviewedCount() {
        val serverUrl = prefs.serverUrl.trim().trimEnd('/')
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val request = Request.Builder()
                    .url("$serverUrl/api/v1/categories/unreviewed?limit=100")
                    .get()
                    .build()

                httpClient.newCall(request).execute().use { response ->
                    val body = response.body?.string()
                    if (response.isSuccessful && body != null) {
                        val type = object : TypeToken<List<UnreviewedTransaction>>() {}.type
                        val list: List<UnreviewedTransaction> = Gson().fromJson(body, type)
                        val count = list.size

                        withContext(Dispatchers.Main) {
                            binding.tvUnreviewedLargeCount.text = count.toString()
                            if (count > 0) {
                                binding.tvUnreviewedBadge.text = "$count Pending"
                                binding.tvUnreviewedBadge.setTextColor(
                                    ContextCompat.getColor(this@MainActivity, R.color.status_warning)
                                )
                                binding.tvUnreviewedBadge.setBackgroundResource(R.drawable.badge_pill_warning)
                                binding.tvUnreviewedSubtitle.text = "$count ambiguous expense${if (count > 1) "s" else ""} need quick 1-tap review"
                                binding.btnOpenReview.text = "Review Now ($count)"
                            } else {
                                binding.tvUnreviewedBadge.text = "All Caught Up"
                                binding.tvUnreviewedBadge.setTextColor(
                                    ContextCompat.getColor(this@MainActivity, R.color.status_healthy)
                                )
                                binding.tvUnreviewedBadge.setBackgroundResource(R.drawable.badge_pill_healthy)
                                binding.tvUnreviewedSubtitle.text = "All transactions automatically categorized"
                                binding.btnOpenReview.text = "View Review Tray"
                            }
                        }
                    }
                }
            } catch (e: Exception) {
                // Silently skip if network unreachable
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
