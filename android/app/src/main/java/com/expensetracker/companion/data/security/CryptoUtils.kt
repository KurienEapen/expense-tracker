package com.expensetracker.companion.data.security

import java.security.MessageDigest
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

object CryptoUtils {

    /**
     * Calculates HMAC_SHA256(secret, timestamp + "." + raw_body) and returns lowercase hex string.
     */
    fun calculateHmac(secret: String, timestamp: String, rawBody: String): String {
        val message = "$timestamp.$rawBody".toByteArray(Charsets.UTF_8)
        val keySpec = SecretKeySpec(secret.toByteArray(Charsets.UTF_8), "HmacSHA256")
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(keySpec)
        val hmacBytes = mac.doFinal(message)
        return hmacBytes.joinToString("") { "%02x".format(it) }
    }

    /**
     * Calculates sha256(sender + "|" + body + "|" + received_ts_ms) and returns lowercase hex string.
     */
    fun computeIdempotencyKey(sender: String, body: String, receivedAtMs: Long): String {
        val input = "$sender|$body|$receivedAtMs".toByteArray(Charsets.UTF_8)
        val md = MessageDigest.getInstance("SHA-256")
        val digest = md.digest(input)
        return digest.joinToString("") { "%02x".format(it) }
    }

    /**
     * Redacts full 16-digit card numbers, CVVs, and OTPs while preserving card last-4.
     */
    fun redactSensitiveInfo(text: String): String {
        var redacted = text

        // 1. Redact 16-digit card numbers (preserving last 4 digits)
        val cardRegex = Regex("""\b(?:\d[ -]?){12}(\d{4})\b""")
        redacted = cardRegex.replace(redacted) { matchResult ->
            val last4 = matchResult.groupValues[1]
            "XXXX-XXXX-XXXX-$last4"
        }

        // 2. Redact CVV if present
        val cvvRegex = Regex("""(?i)\b(cvv|cvv2|security code)\s*[:=]?\s*\d{3,4}\b""")
        redacted = cvvRegex.replace(redacted, "$1: [REDACTED]")

        // 3. Redact OTP if present
        val otpRegex = Regex("""(?i)\b(otp|one time password)\s*(?:is|:)?\s*\d{4,8}\b""")
        redacted = otpRegex.replace(redacted, "$1: [REDACTED]")

        return redacted
    }
}
