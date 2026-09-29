package com.expensetracker.companion

import com.expensetracker.companion.data.security.CryptoUtils
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CryptoUtilsTest {

    @Test
    fun testHmacCalculationMatchesBackendContract() {
        val secret = "dev_secret_change_in_production_32bytes"
        val timestamp = "1790000000"
        val rawBody = "{\"test\":\"payload\"}"

        // Expected HMAC computed with standard HMAC-SHA256 in Python backend
        val expectedHmac = "f76ee951d024102def2899f1f9e6954ae595f6633696d5fb0ea517a0876d507a"
        val hmac = CryptoUtils.calculateHmac(secret, timestamp, rawBody)
        assertEquals("HMAC signature must match backend byte-for-byte", expectedHmac, hmac)
    }

    @Test
    fun testIdempotencyKeyComputationMatchesBackend() {
        val sender = "HDFCBK"
        val body = "Rs 1,250.00 spent on HDFC Bank Card x1234"
        val receivedMs = 1790000000000L

        // Expected Idempotency key from backend Python implementation
        val expectedKey = "e7be5bf15d9f6eff87b053ee7d091aab398b4efc461b84416c377a9b27015209"
        val key = CryptoUtils.computeIdempotencyKey(sender, body, receivedMs)
        assertEquals("Idempotency key must match backend formula sha256(sender|body|ts)", expectedKey, key)
    }

    @Test
    fun testRedactionPreservesLast4Digits() {
        val rawSms = "Rs 2,500 spent on Card 4111 2222 3333 4444 at Swiggy. CVV: 123. OTP: 987654"
        val redacted = CryptoUtils.redactSensitiveInfo(rawSms)

        assertFalse("Full card number must not exist in output", redacted.contains("4111 2222 3333 4444"))
        assertTrue("Last 4 digits must be preserved", redacted.contains("XXXX-XXXX-XXXX-4444"))
        assertFalse("CVV must be redacted", redacted.contains("123"))
        assertFalse("OTP must be redacted", redacted.contains("987654"))
    }
}
