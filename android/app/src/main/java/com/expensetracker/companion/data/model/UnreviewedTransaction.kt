package com.expensetracker.companion.data.model

import com.google.gson.annotations.SerializedName

data class UnreviewedTransaction(
    @SerializedName("id") val id: Int,
    @SerializedName("amount_inr") val amountInr: Double,
    @SerializedName("merchant_clean") val merchantClean: String?,
    @SerializedName("merchant_raw") val merchantRaw: String?,
    @SerializedName("issuer") val issuer: String?,
    @SerializedName("card_type") val cardType: String?,
    @SerializedName("card_last4") val cardLast4: String?,
    @SerializedName("transacted_at_utc") val transactedAtUtc: String?
) {
    val displayMerchant: String
        get() = merchantClean?.ifBlank { null } ?: merchantRaw?.ifBlank { null } ?: "Unknown Merchant"

    val displayMeta: String
        get() {
            val parts = mutableListOf<String>()
            if (!transactedAtUtc.isNullOrEmpty()) {
                val cleanDate = transactedAtUtc.take(10)
                parts.add(cleanDate)
            }
            issuer?.let { if (it.isNotBlank()) parts.add(it) }
            if (!cardLast4.isNullOrEmpty()) {
                val type = cardType?.replaceFirstChar { it.uppercase() } ?: "Card"
                parts.add("$type xx$cardLast4")
            }
            return if (parts.isEmpty()) "Pending categorization" else parts.joinToString(" • ")
        }
}
