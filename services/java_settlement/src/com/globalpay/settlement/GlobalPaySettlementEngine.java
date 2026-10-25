package com.globalpay.settlement;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.Map;
import java.util.Set;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/**
 * GlobalPay 2.0 — Java 17 Core Settlement, State Machine & Webhook Verification Engine
 *
 * Modify this class if you want to customize enterprise settlement rules,
 * state transitions, basis-point fee formulas, or HMAC-SHA256 webhook verification
 * in Java.
 */
public final class GlobalPaySettlementEngine {

    public enum TransactionState {
        DRAFT,
        REQUIRES_AUTHORIZATION,
        PROCESSING,
        COMPLETED,
        FAILED,
        CANCELLED,
        REFUND_PENDING,
        REFUNDED,
        REQUIRES_INVESTIGATION
    }

    private static final Map<TransactionState, Set<TransactionState>> VALID_TRANSITIONS =
            new EnumMap<>(TransactionState.class);

    static {
        VALID_TRANSITIONS.put(TransactionState.DRAFT, EnumSet.of(
                TransactionState.REQUIRES_AUTHORIZATION, TransactionState.CANCELLED, TransactionState.FAILED));
        VALID_TRANSITIONS.put(TransactionState.REQUIRES_AUTHORIZATION, EnumSet.of(
                TransactionState.PROCESSING, TransactionState.CANCELLED, TransactionState.FAILED));
        VALID_TRANSITIONS.put(TransactionState.PROCESSING, EnumSet.of(
                TransactionState.COMPLETED, TransactionState.FAILED, TransactionState.REQUIRES_INVESTIGATION));
        VALID_TRANSITIONS.put(TransactionState.REQUIRES_INVESTIGATION, EnumSet.of(
                TransactionState.COMPLETED, TransactionState.FAILED, TransactionState.REFUND_PENDING));
        VALID_TRANSITIONS.put(TransactionState.COMPLETED, EnumSet.of(
                TransactionState.REFUND_PENDING));
        VALID_TRANSITIONS.put(TransactionState.REFUND_PENDING, EnumSet.of(
                TransactionState.REFUNDED, TransactionState.REQUIRES_INVESTIGATION));
        VALID_TRANSITIONS.put(TransactionState.FAILED, EnumSet.noneOf(TransactionState.class));
        VALID_TRANSITIONS.put(TransactionState.CANCELLED, EnumSet.noneOf(TransactionState.class));
        VALID_TRANSITIONS.put(TransactionState.REFUNDED, EnumSet.noneOf(TransactionState.class));
    }

    public static boolean canTransition(TransactionState from, TransactionState to) {
        Set<TransactionState> allowed = VALID_TRANSITIONS.get(from);
        return allowed != null && allowed.contains(to);
    }

    public static void assertValidTransition(TransactionState from, TransactionState to) {
        if (!canTransition(from, to)) {
            throw new IllegalStateException(
                    "INVALID_STATE_TRANSITION: Cannot transition from " + from + " to " + to);
        }
    }

    /**
     * Exact integer minor-unit fee calculation using basis points (100 bps = 1.00%).
     */
    public static long computeBasisPointsMinor(long amountMinor, int basisPoints) {
        if (amountMinor <= 0 || basisPoints <= 0) {
            return 0L;
        }
        return (amountMinor * (long) basisPoints + 5000L) / 10000L;
    }

    /**
     * Decimal-safe currency conversion using BigDecimal and explicit decimal scale.
     */
    public static long convertMinorAmount(
            long sendAmountMinor,
            int sourceDecimals,
            int targetDecimals,
            BigDecimal customerExchangeRate) {
        BigDecimal sendMajor = BigDecimal.valueOf(sendAmountMinor)
                .movePointLeft(sourceDecimals);
        BigDecimal targetMajor = sendMajor.multiply(customerExchangeRate);
        return targetMajor
                .movePointRight(targetDecimals)
                .setScale(0, RoundingMode.HALF_UP)
                .longValueExact();
    }

    /**
     * Constant-time HMAC-SHA256 webhook signature verification.
     */
    public static boolean verifyWebhookHmacSha256(String rawPayload, String signatureHex, String secret) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            SecretKeySpec keySpec = new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
            mac.init(keySpec);
            byte[] digest = mac.doFinal(rawPayload.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder(digest.length * 2);
            for (byte b : digest) {
                sb.append(String.format("%02x", b));
            }
            byte[] expectedBytes = sb.toString().getBytes(StandardCharsets.UTF_8);
            byte[] providedBytes = signatureHex.getBytes(StandardCharsets.UTF_8);
            return MessageDigest.isEqual(expectedBytes, providedBytes);
        } catch (Exception e) {
            return false;
        }
    }

    public static void main(String[] args) {
        assertValidTransition(TransactionState.DRAFT, TransactionState.REQUIRES_AUTHORIZATION);
        assertValidTransition(TransactionState.REQUIRES_AUTHORIZATION, TransactionState.PROCESSING);
        assertValidTransition(TransactionState.PROCESSING, TransactionState.COMPLETED);

        long sendMinor = 100_000L; // $1,000.00 USD
        long varFeeMinor = computeBasisPointsMinor(sendMinor, 45); // 0.45% = 450 cents ($4.50)
        long inrRecipientMinor = convertMinorAmount(sendMinor, 2, 2, new BigDecimal("83.65620000"));

        System.out.println("[GlobalPay Java 17 Settlement Engine] Verified at " + Instant.now());
        System.out.println(" -> Send Minor (USD): " + sendMinor);
        System.out.println(" -> Variable Fee Minor (45 bps): " + varFeeMinor);
        System.out.println(" -> Recipient Minor (INR): " + inrRecipientMinor);
    }
}
