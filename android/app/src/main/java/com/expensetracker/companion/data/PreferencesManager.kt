package com.expensetracker.companion.data

import android.content.Context
import android.content.SharedPreferences

class PreferencesManager(context: Context) {

    private val prefs: SharedPreferences = context.getSharedPreferences(
        "expense_companion_prefs",
        Context.MODE_PRIVATE
    )

    var serverUrl: String
        get() = prefs.getString(KEY_SERVER_URL, "http://10.0.2.2:8000") ?: "http://10.0.2.2:8000"
        set(value) = prefs.edit().putString(KEY_SERVER_URL, value.trimEnd('/')).apply()

    var deviceId: String
        get() = prefs.getString(KEY_DEVICE_ID, "pixel-companion-01") ?: "pixel-companion-01"
        set(value) = prefs.edit().putString(KEY_DEVICE_ID, value.trim()).apply()

    var deviceSecret: String
        get() = prefs.getString(KEY_DEVICE_SECRET, "dev_secret_change_in_production_32bytes") ?: "dev_secret_change_in_production_32bytes"
        set(value) = prefs.edit().putString(KEY_DEVICE_SECRET, value.trim()).apply()

    var senderWhitelist: String
        get() = prefs.getString(
            KEY_SENDER_WHITELIST,
            "HDFCBK,ICICIB,SBICRD,AXISBK,JUPITR,SCAPIA,HSBCIN,FEDBNK,INDUSB,KOTAKB,PLUXEE,SODEXO,ONECRD,FIMONEY,CRED,PAYTM,AMZPAY,IDFCFB,RBLBNK,YESBNK,CITIBK,SCBL,TATAPAY,AIRTEL,POSTPE,SLICEC,UNI"
        ) ?: ""
        set(value) = prefs.edit().putString(KEY_SENDER_WHITELIST, value).apply()

    var appWhitelist: String
        get() = prefs.getString(
            KEY_APP_WHITELIST,
            "com.google.android.apps.nbu.paisa.user,com.phonepe.app,in.org.npci.upiapp"
        ) ?: ""
        set(value) = prefs.edit().putString(KEY_APP_WHITELIST, value).apply()

    fun getSenderWhitelistSet(): Set<String> {
        val userSet = senderWhitelist.split(",")
            .map { it.trim().uppercase() }
            .filter { it.isNotEmpty() }
            .toSet()
        val defaultCore = setOf(
            "HDFCBK", "ICICIB", "SBICRD", "AXISBK", "JUPITR", "SCAPIA", "HSBCIN",
            "FEDBNK", "INDUSB", "KOTAKB", "PLUXEE", "SODEXO", "ONECRD", "FIMONEY",
            "CRED", "PAYTM", "AMZPAY", "IDFCFB", "RBLBNK", "YESBNK", "CITIBK",
            "SCBL", "TATAPAY", "AIRTEL", "POSTPE", "SLICEC", "UNI"
        )
        return userSet + defaultCore
    }

    fun getAppWhitelistSet(): Set<String> {
        return appWhitelist.split(",")
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .toSet()
    }

    companion object {
        private const val KEY_SERVER_URL = "server_url"
        private const val KEY_DEVICE_ID = "device_id"
        private const val KEY_DEVICE_SECRET = "device_secret"
        private const val KEY_SENDER_WHITELIST = "sender_whitelist"
        private const val KEY_APP_WHITELIST = "app_whitelist"
    }
}
