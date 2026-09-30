package com.expensetracker.companion.data.model

import com.google.gson.annotations.SerializedName

data class IgnoredRule(
    @SerializedName("id") val id: Int,
    @SerializedName("pattern") val pattern: String,
    @SerializedName("pattern_type") val patternType: String,
    @SerializedName("sender_filter") val senderFilter: String?,
    @SerializedName("description") val description: String?,
    @SerializedName("sample_text") val sampleText: String?,
    @SerializedName("match_count") val matchCount: Int,
    @SerializedName("is_active") val isActive: Boolean,
    @SerializedName("created_at_utc") val createdAtUtc: String?
) {
    val displayTitle: String
        get() = description?.ifBlank { null } ?: "Non-Transactional Filter"

    val displayMeta: String
        get() {
            val bank = senderFilter?.ifBlank { null } ?: "All Banks"
            val countStr = if (matchCount == 1) "1 time" else "$matchCount times"
            return "Bank: $bank • Blocked $countStr"
        }
}
