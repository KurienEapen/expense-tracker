package com.expensetracker.companion.data.model

import com.google.gson.annotations.SerializedName

data class RawMessageItem(
    @SerializedName("id") val id: Int,
    @SerializedName("sender") val sender: String,
    @SerializedName("body") val body: String,
    @SerializedName("source") val source: String,
    @SerializedName("received_at_ms") val receivedAtMs: Long,
    @SerializedName("is_parsed") var isParsed: Boolean,
    @SerializedName("transaction_id") var transactionId: Int?
) {
    val displayDate: String
        get() {
            return try {
                val sdf = java.text.SimpleDateFormat("dd MMM, hh:mm a", java.util.Locale.getDefault())
                sdf.format(java.util.Date(receivedAtMs))
            } catch (e: Exception) {
                ""
            }
        }
}
