/**
 * GlobalPay 2.0 Automated Integration, Security, State Machine & HTTP API Test Suite
 * Executes directly via `node --test tests/run_tests.mjs`
 */
import test from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import {
  GlobalPayEngine,
  createHttpServer,
  formatMinor,
  getCrossRateScaled,
  convertMinorAmount,
  assertValidStateTransition,
} from "../server/src/runtime.mjs";

test("1. Authentication: Valid registration, login, invalid credentials, and session revocation", async () => {
  const engine = new GlobalPayEngine();

  // Valid login for seeded demo user Maya
  const mayaSession = engine.loginUser({
    email: "maya.lin@sandbox.globalpay.app",
    password: "GlobalPay#2026!",
  });
  assert.ok(mayaSession.accessToken.startsWith("gpsess_"));
  assert.equal(mayaSession.user.email, "maya.lin@sandbox.globalpay.app");
  assert.equal(mayaSession.user.passwordHash, undefined, "Password hash must never leak");

  // Invalid credentials rejected with 401
  assert.throws(
    () => engine.loginUser({ email: "maya.lin@sandbox.globalpay.app", password: "WrongPassword!" }),
    (err) => err.status === 401
  );

  // Registration of fresh user provisions default USD sandbox account
  const fresh = engine.registerUser({
    email: "zoe.chen@sandbox.globalpay.app",
    password: "ZoeStrongPassword#2026",
    fullName: "Zoe Chen",
    handle: "@zoechen",
  });
  assert.equal(fresh.user.profile.handle, "@zoechen");
  const zoeAccounts = engine.getUserAccounts(fresh.user.id);
  assert.equal(zoeAccounts.length, 1);
  assert.equal(zoeAccounts[0].balanceMinor, "250000");

  // Revoke session and verify subsequent access fails
  engine.revokeSession(fresh.accessToken);
  assert.throws(
    () => engine.authenticateToken(fresh.accessToken),
    (err) => err.status === 401
  );
});

test("2. Access Control & Data Isolation: User A cannot view or refund User B's transactions", async () => {
  const engine = new GlobalPayEngine();
  const maya = engine.loginUser({ email: "maya.lin@sandbox.globalpay.app", password: "GlobalPay#2026!" }).user;
  const alex = engine.loginUser({ email: "alex.rivera@sandbox.globalpay.app", password: "AlexSecure#2026!" }).user;

  // Maya tries to read Alex's private transaction
  assert.throws(
    () => engine.getTransactionForUser(maya, "tx_seed_alex_only"),
    (err) => err.status === 403
  );

  // Maya tries to refund Alex's transaction
  assert.throws(
    () => engine.refundTransaction(maya, "tx_seed_alex_only"),
    (err) => err.status === 403
  );

  // Alex can read his own transaction
  const alexTx = engine.getTransactionForUser(alex, "tx_seed_alex_only");
  assert.equal(alexTx.id, "tx_seed_alex_only");
});

test("3. Financial Arithmetic & International Transfer Quotes: Decimal-safe minor units & expiry enforcement", async () => {
  const engine = new GlobalPayEngine();
  const maya = engine.loginUser({ email: "maya.lin@sandbox.globalpay.app", password: "GlobalPay#2026!" }).user;

  // Generate USD -> INR quote for $1,000.00 (100,000 minor units)
  const quote = engine.createTransferQuote(maya.id, {
    sourceCurrency: "USD",
    targetCurrency: "INR",
    sendAmountMinor: "100000",
    beneficiaryId: "ben_arjun_in",
  });

  // Fixed fee: 299 ($2.99), Variable fee (45 bps of 100000): 450 ($4.50), Tax (10 bps): 100 ($1.00) -> Total fee = 849 ($8.49)
  assert.equal(quote.fixedFeeMinor, "299");
  assert.equal(quote.variableFeeMinor, "450");
  assert.equal(quote.taxAmountMinor, "100");
  assert.equal(quote.totalFeeMinor, "849");
  assert.equal(quote.totalPayableMinor, "100849");

  // Expire the quote manually and verify payment execution rejects it
  const rawQuote = engine.state.quotes.get(quote.id);
  rawQuote.expiresAt = new Date(Date.now() - 1000).toISOString();

  assert.throws(
    () =>
      engine.executePayment(maya.id, {
        idempotencyKey: "idem_expired_quote_test",
        type: "INTERNATIONAL_TRANSFER",
        sourceCurrency: "USD",
        quoteId: quote.id,
        recipientName: "Arjun Mehta",
        recipientIdentifier: "HDFC0000241",
      }),
    (err) => err.status === 422 && err.message.includes("QUOTE_EXPIRED")
  );
});

test("4. Idempotency, Insufficient Funds, Atomic Rollback & State Transitions", async () => {
  const engine = new GlobalPayEngine();
  const maya = engine.loginUser({ email: "maya.lin@sandbox.globalpay.app", password: "GlobalPay#2026!" }).user;

  const beforeUsd = BigInt(engine.getUserAccounts(maya.id).find((a) => a.currency === "USD").balanceMinor);

  // Execute domestic payment of $50.00 (5000 cents)
  const firstCall = engine.executePayment(maya.id, {
    idempotencyKey: "idem_unique_payment_001",
    type: "DOMESTIC_P2P",
    sourceCurrency: "USD",
    amountMinor: "5000",
    recipientName: "Liam O'Connor",
    recipientIdentifier: "@liamoconnor",
  });
  assert.equal(firstCall.transaction.state, "COMPLETED");

  // Retry with identical idempotency key -> returns deduplicated result without double-debiting
  const duplicateCall = engine.executePayment(maya.id, {
    idempotencyKey: "idem_unique_payment_001",
    type: "DOMESTIC_P2P",
    sourceCurrency: "USD",
    amountMinor: "5000",
    recipientName: "Liam O'Connor",
    recipientIdentifier: "@liamoconnor",
  });
  assert.equal(duplicateCall.deduplicated, true);
  assert.equal(duplicateCall.transaction.id, firstCall.transaction.id);

  const afterUsd = BigInt(engine.getUserAccounts(maya.id).find((a) => a.currency === "USD").balanceMinor);
  assert.equal(beforeUsd - afterUsd, 5000n, "Balance must only be debited once across duplicate requests");

  // Reusing same idempotency key with different amount must throw 409 IDEMPOTENCY_CONFLICT
  assert.throws(
    () =>
      engine.executePayment(maya.id, {
        idempotencyKey: "idem_unique_payment_001",
        type: "DOMESTIC_P2P",
        sourceCurrency: "USD",
        amountMinor: "9900",
        recipientName: "Liam O'Connor",
        recipientIdentifier: "@liamoconnor",
      }),
    (err) => err.status === 409
  );

  // Single domestic transaction limit check (limit is 1,000,000 minor = $10,000.00)
  assert.throws(
    () =>
      engine.executePayment(maya.id, {
        idempotencyKey: "idem_too_large_002",
        type: "DOMESTIC_P2P",
        sourceCurrency: "USD",
        amountMinor: "1100000", // $11,000.00 > $10,000.00 single-tx limit
        recipientName: "Liam",
        recipientIdentifier: "@liam",
      }),
    (err) => err.status === 422 && err.message.includes("LIMIT_EXCEEDED")
  );
  // Wait: let's test an amount > Maya's balance on EUR account (EUR balance is 342,000 minor = €3,420.00)
  assert.throws(
    () =>
      engine.executePayment(maya.id, {
        idempotencyKey: "idem_insufficient_eur",
        type: "DOMESTIC_P2P",
        sourceCurrency: "EUR",
        amountMinor: "500000", // €5,000.00 > €3,420.00 available
        recipientName: "Claire Dubois",
        recipientIdentifier: "@clairedubois",
      }),
    (err) => err.status === 422 && err.message.includes("INSUFFICIENT_FUNDS")
  );

  // Atomic rollback check when mid-transaction DB fault occurs
  const eurBeforeFault = BigInt(engine.getUserAccounts(maya.id).find((a) => a.currency === "EUR").balanceMinor);
  assert.throws(() =>
    engine.executePayment(maya.id, {
      idempotencyKey: "idem_db_fault_rollback",
      type: "DOMESTIC_P2P",
      sourceCurrency: "EUR",
      amountMinor: "10000",
      recipientName: "Claire Dubois",
      recipientIdentifier: "@clairedubois",
      simulationBehavior: "THROW_DB_ERROR",
    })
  );
  const eurAfterFault = BigInt(engine.getUserAccounts(maya.id).find((a) => a.currency === "EUR").balanceMinor);
  assert.equal(eurBeforeFault, eurAfterFault, "Balance must roll back cleanly on mid-transaction failure");

  // Validate illegal state transitions are rejected
  assert.throws(() => assertValidStateTransition("COMPLETED", "FAILED"), /Invalid state transition/);
  assert.throws(() => assertValidStateTransition("DRAFT", "COMPLETED"), /Invalid state transition/);
});

test("5. Webhook Signature Verification, Deduplication, Refunds & Analytics Double-Count Prevention", async () => {
  const engine = new GlobalPayEngine({ webhookSecret: "whsec_test_secret_key" });
  const maya = engine.loginUser({ email: "maya.lin@sandbox.globalpay.app", password: "GlobalPay#2026!" }).user;

  // Create a payment that stays in PROCESSING state
  const pendingRes = engine.executePayment(maya.id, {
    idempotencyKey: "idem_stay_processing_01",
    type: "DOMESTIC_P2P",
    sourceCurrency: "USD",
    amountMinor: "12000", // $120.00
    recipientName: "Slow Settlement Vendor",
    recipientIdentifier: "@slow_vendor",
    simulationBehavior: "STAY_PROCESSING",
  });
  assert.equal(pendingRes.transaction.state, "PROCESSING");

  const payloadStr = JSON.stringify({
    externalEventId: "evt_webhook_001",
    transactionId: pendingRes.transaction.id,
    targetState: "COMPLETED",
    reason: "Async clearing completed",
  });

  // Invalid webhook signature must fail with 401
  assert.throws(
    () => engine.processProviderWebhook(payloadStr, "invalid_signature_hex"),
    (err) => err.status === 401
  );

  // Valid HMAC signature processes transition PROCESSING -> COMPLETED
  const validSig = crypto.createHmac("sha256", "whsec_test_secret_key").update(payloadStr).digest("hex");
  const whResult1 = engine.processProviderWebhook(payloadStr, validSig);
  assert.equal(whResult1.status, "PROCESSED");
  assert.equal(whResult1.transactionState, "COMPLETED");

  // Duplicate webhook delivery is safely ignored
  const whResult2 = engine.processProviderWebhook(payloadStr, validSig);
  assert.equal(whResult2.status, "DUPLICATE_IGNORED");

  // Analytics includes the completed $120.00 transaction
  const analyticsBeforeRefund = engine.getSpendingAnalytics(maya.id);
  const spendBefore = BigInt(analyticsBeforeRefund.totalCompletedSpendMinor);

  // Refund the $120.00 transaction and verify analytics excludes refunded transaction
  const refundedTx = engine.refundTransaction(maya, pendingRes.transaction.id);
  assert.equal(refundedTx.state, "REFUNDED");

  const analyticsAfterRefund = engine.getSpendingAnalytics(maya.id);
  const spendAfter = BigInt(analyticsAfterRefund.totalCompletedSpendMinor);
  assert.equal(spendBefore - spendAfter, 12000n, "Refunded transaction must be excluded from active spending totals");
});

test("6. End-to-End HTTP REST API Acceptance Journey (/api/v1/*)", async () => {
  const { server } = createHttpServer();
  await new Promise((resolve) => server.listen(0, resolve));
  const address = server.address();
  const baseUrl = `http://127.0.0.1:${address.port}/api/v1`;

  try {
    // 1. Liveness health check
    const healthRes = await fetch(`${baseUrl}/system/health/liveness`);
    assert.equal(healthRes.status, 200);
    const healthJson = await healthRes.json();
    assert.equal(healthJson.status, "ALIVE");

    // 2. Login as Maya
    const loginRes = await fetch(`${baseUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "maya.lin@sandbox.globalpay.app", password: "GlobalPay#2026!" }),
    });
    assert.equal(loginRes.status, 200);
    const { accessToken } = await loginRes.json();
    const authHeaders = {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    };

    // 3. Fetch indicative FX rates
    const fxRes = await fetch(`${baseUrl}/fx/rates?base=USD`, { headers: authHeaders });
    assert.equal(fxRes.status, 200);
    const fxJson = await fxRes.json();
    assert.equal(fxJson.isIndicative, true);
    assert.ok(fxJson.rates.INR);

    // 4. Request a sandbox transfer quote (USD -> GBP)
    const quoteRes = await fetch(`${baseUrl}/transfers/quotes`, {
      method: "POST",
      headers: authHeaders,
      body: JSON.stringify({
        sourceCurrency: "USD",
        targetCurrency: "GBP",
        sendAmountMinor: "20000", // $200.00
      }),
    });
    assert.equal(quoteRes.status, 201);
    const { quote } = await quoteRes.json();

    // 5. Execute sandbox international transfer using the quote
    const payRes = await fetch(`${baseUrl}/payments`, {
      method: "POST",
      headers: { ...authHeaders, "Idempotency-Key": "e2e_http_quote_pay_01" },
      body: JSON.stringify({
        type: "INTERNATIONAL_TRANSFER",
        sourceCurrency: "USD",
        quoteId: quote.id,
        recipientName: "London Sandbox Beneficiary",
        recipientIdentifier: "SORT-20-00-00",
      }),
    });
    assert.equal(payRes.status, 201);
    const { transaction } = await payRes.json();
    assert.equal(transaction.state, "COMPLETED");

    // 6. Non-admin user cannot access /admin/overview
    const adminDenied = await fetch(`${baseUrl}/admin/overview`, { headers: authHeaders });
    assert.equal(adminDenied.status, 403);

    // 7. Logout revokes session
    const logoutRes = await fetch(`${baseUrl}/auth/logout`, { method: "POST", headers: authHeaders });
    assert.equal(logoutRes.status, 200);

    const afterLogoutRes = await fetch(`${baseUrl}/accounts`, { headers: authHeaders });
    assert.equal(afterLogoutRes.status, 401);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});
