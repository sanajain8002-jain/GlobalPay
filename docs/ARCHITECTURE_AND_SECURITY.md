# GlobalPay 2.0 — Architecture, Security & Financial Controls

## 1. Financial Data Integrity
- **Exact Minor-Unit Storage**: Every monetary balance, fee, tax, quote, and transaction amount is stored and computed as a 64-bit integer (`BIGINT` / `BigInt`) in currency minor units (e.g., cents for `USD`/`EUR`/`GBP`, paise for `INR`, and 0-decimal whole yen for `JPY`).
- **Fixed-Point FX Arithmetic**: Exchange rates use `DECIMAL(18,8)` in PostgreSQL and `10^8`-scaled `BigInt` arithmetic in Node.js so floating-point precision drift (`0.1 + 0.2 !== 0.3`) is impossible.
- **Explicit Transaction State Machine**: All transactions transition strictly through validated states (`DRAFT` -> `REQUIRES_AUTHORIZATION` -> `PROCESSING` -> `COMPLETED` / `FAILED` / `REQUIRES_INVESTIGATION`, and `COMPLETED` -> `REFUND_PENDING` -> `REFUNDED`).
- **Idempotency Guarantees**: Every payment or transfer mutation requires a unique `Idempotency-Key` scoped to `(userId, key, endpoint)`. Retrying with the same key returns the original outcome without double-debiting; reusing a key with altered parameters throws `409 IDEMPOTENCY_CONFLICT`.

## 2. Authentication, Authorization & Redaction
- **Password Security**: Uses PBKDF2-HMAC-SHA512 with per-user cryptographic salts (`crypto.pbkdf2Sync`) and constant-time comparison (`crypto.timingSafeEqual`).
- **Strict Ownership Isolation**: Every query and service method filters by the authenticated `session.userId` derived from the verified session token—never from client-supplied user IDs.
- **Zero Secret Leakage**: Audit logs automatically redact `password`, `passwordHash`, `accessToken`, `csrfToken`, `otp`, and `upiPin`.
- **Data Retention & Account Deactivation**: When a user deactivates their account, login and payment capabilities are immediately revoked (`status = DEACTIVATED`), while statutory ledger records are retained under a 7-year compliance hold (`retentionHoldUntil`) before anonymization.

## 3. Real-World Compliance Boundaries & Live Activation Checklist
GlobalPay 2.0 operates in **Deterministic Sandbox Mode** by default. To activate live real-money movement in production:
1. Partner with a licensed banking-as-a-service (BaaS) or remittance sponsor (e.g., Wise Platform, Stripe Treasury/Payouts, Adyen, or licensed local clearing sponsor).
2. Configure live KYC/AML identity verification (e.g., Persona, Alloy, or Stripe Identity) and OFAC/sanctions screening prior to enabling `PAYMENT_PROVIDER_MODE=live`.
3. Provision production secrets in your secret manager (`SESSION_SECRET`, `JWT_ACCESS_SECRET`, `CSRF_SECRET`, `PAYMENT_WEBHOOK_SECRET`, `DATABASE_URL`).
