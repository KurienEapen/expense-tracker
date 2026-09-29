package com.expensetracker.companion.data.local

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "outbox",
    indices = [Index(value = ["idempotencyKey"], unique = true)]
)
data class OutboxEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val idempotencyKey: String,
    val source: String, // "sms" | "notification" | "screenshot_ocr" | "share_text"
    val sender: String,
    val appPackage: String? = null,
    val body: String,
    val receivedAtMs: Long,
    val deviceTz: String = "Asia/Kolkata",
    val locationJson: String? = null,
    val ocrConfidence: Float? = null,
    val appVersion: String = "0.1.0",
    val createdAtMs: Long = System.currentTimeMillis()
)
