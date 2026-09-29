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
import android.widget.Toast
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
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var prefs: PreferencesManager
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .build()

    private val requestSmsPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val smsGranted = permissions[Manifest.permission.RECEIVE_SMS] == true
        val readGranted = permissions[Manifest.permission.READ_SMS] == true
        if (smsGranted && readGranted) {
            Toast.makeText(this, "SMS permissions granted!", Toast.LENGTH_SHORT).show()
        } else {
            Toast.makeText(this, "SMS permissions are needed to capture transactions", Toast.LENGTH_LONG).show()
        }
        updatePermissionButtons()
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
        updatePermissionButtons()
    }

    private fun initViews() {
        binding.etServerUrl.setText(prefs.serverUrl)
        binding.etDeviceId.setText(prefs.deviceId)
        binding.etDeviceSecret.setText(prefs.deviceSecret)

        binding.btnSaveSettings.setOnClickListener {
            prefs.serverUrl = binding.etServerUrl.text.toString()
            prefs.deviceId = binding.etDeviceId.text.toString()
            prefs.deviceSecret = binding.etDeviceSecret.text.toString()
            Toast.makeText(this, "Settings saved!", Toast.LENGTH_SHORT).show()
            checkServerHealth()
        }

        binding.btnSyncNow.setOnClickListener {
            OutboxWorker.enqueue(this)
            Toast.makeText(this, "Outbox sync enqueued", Toast.LENGTH_SHORT).show()
        }

        binding.btnTestPing.setOnClickListener {
            checkServerHealth()
        }

        binding.btnRequestSmsPermission.setOnClickListener {
            requestSmsPermissionLauncher.launch(
                arrayOf(
                    Manifest.permission.RECEIVE_SMS,
                    Manifest.permission.READ_SMS
                )
            )
        }

        binding.btnNotifPermission.setOnClickListener {
            val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
            startActivity(intent)
        }

        binding.btnBatteryOpt.setOnClickListener {
            requestBatteryOptimizationExemption()
        }

        binding.btnBackfillSms.setOnClickListener {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_SMS) != PackageManager.PERMISSION_GRANTED) {
                Toast.makeText(this, "Please grant SMS read permission first", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            binding.btnBackfillSms.isEnabled = false
            lifecycleScope.launch {
                val count = SmsBackfillHelper(this@MainActivity).backfillRecentBankSms(90)
                Toast.makeText(this@MainActivity, "Backfilled $count bank messages to outbox!", Toast.LENGTH_LONG).show()
                binding.btnBackfillSms.isEnabled = true
            }
        }
    }

    private fun observeOutbox() {
        val db = AppDatabase.getDatabase(this)
        lifecycleScope.launch {
            db.outboxDao().getPendingCountFlow().collect { count ->
                binding.tvOutboxCount.text = getString(R.string.outbox_pending_count, count)
            }
        }
    }

    private fun checkServerHealth() {
        val serverUrl = prefs.serverUrl
        binding.tvServerStatus.text = "Server Status: Checking..."

        lifecycleScope.launch(Dispatchers.IO) {
            val request = Request.Builder()
                .url("$serverUrl/api/v1/health")
                .get()
                .build()

            try {
                httpClient.newCall(request).execute().use { response ->
                    withContext(Dispatchers.Main) {
                        if (response.isSuccessful) {
                            binding.tvServerStatus.text = "Server Status: Connected (HTTP 200)"
                            binding.tvServerStatus.setTextColor(ContextCompat.getColor(this@MainActivity, R.color.secondary))
                        } else {
                            binding.tvServerStatus.text = "Server Status: Error (HTTP ${response.code})"
                            binding.tvServerStatus.setTextColor(ContextCompat.getColor(this@MainActivity, R.color.error))
                        }
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.tvServerStatus.text = "Server Status: Unreachable (${e.javaClass.simpleName})"
                    binding.tvServerStatus.setTextColor(ContextCompat.getColor(this@MainActivity, R.color.error))
                }
            }
        }
    }

    private fun updatePermissionButtons() {
        val smsGranted = ContextCompat.checkSelfPermission(this, Manifest.permission.RECEIVE_SMS) == PackageManager.PERMISSION_GRANTED
        binding.btnRequestSmsPermission.text = if (smsGranted) "SMS Permission: Granted ✓" else "SMS Permission: Grant"
        binding.btnRequestSmsPermission.isEnabled = !smsGranted

        val notifGranted = isNotificationServiceEnabled()
        binding.btnNotifPermission.text = if (notifGranted) "Notification Listener: Enabled ✓" else "Notification Listener: Enable"
        binding.btnNotifPermission.isEnabled = !notifGranted

        val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
        val isIgnoringBattery = pm.isIgnoringBatteryOptimizations(packageName)
        binding.btnBatteryOpt.text = if (isIgnoringBattery) "Battery Exemption: Active ✓" else "Battery Optimization: Request Exemption"
        binding.btnBatteryOpt.isEnabled = !isIgnoringBattery
    }

    private fun isNotificationServiceEnabled(): Boolean {
        val flat = Settings.Secure.getString(contentResolver, "enabled_notification_listeners")
        return flat != null && flat.contains(packageName)
    }

    private fun requestBatteryOptimizationExemption() {
        val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
        if (!pm.isIgnoringBatteryOptimizations(packageName)) {
            val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                data = Uri.parse("package:$packageName")
            }
            startActivity(intent)
        }
    }
}
