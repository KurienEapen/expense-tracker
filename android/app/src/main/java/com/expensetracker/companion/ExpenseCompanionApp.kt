package com.expensetracker.companion

import android.app.Application
import android.util.Log
import com.expensetracker.companion.worker.HeartbeatWorker
import com.expensetracker.companion.worker.OutboxWorker

class ExpenseCompanionApp : Application() {

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "Starting Expense Companion Application...")

        // Schedule periodic heartbeat telemetry worker
        HeartbeatWorker.schedulePeriodic(this)

        // Trigger immediate check on app startup for any pending outbox rows
        OutboxWorker.enqueue(this)
    }

    companion object {
        private const val TAG = "ExpenseCompanionApp"
    }
}
