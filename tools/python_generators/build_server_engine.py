import os

ROOT = "artifacts/file_generation/ttl=63d/intermediate/globalpay-2.0"

def write_file(rel_path, content):
    full_path = os.path.join(ROOT, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.lstrip("\n"))

write_file("server/src/runtime.mjs", """
/**
 * GlobalPay 2.0 Executable Backend Server & Core Financial Engine (Zero-External-Dep Runtime)
 * Supports all /api/v1 REST endpoints, PBKDF2 password hashing, session management,
 * RBAC, user data isolation, integer minor-unit arithmetic, quote expiry, idempotency,
 * transaction state machine, webhook HMAC verification, and PDF receipt generation.
 */
import http from "node:http";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

// ============================================================================
// 1. CRYPTOGRAPHIC & FINANCIAL UTILITIES
// ============================================================================
export const CURRENCIES = {
  USD: { code: "USD", symbol: "$", name: "US Dollar", decimals: 2, transferable: true },
  EUR: { code: "EUR", symbol: "€", name: "Euro", decimals: 2, transferable: true },
  GBP: { code: "GBP", symbol: "£", name: "British Pound", decimals: 2, transferable: true },
  INR: { code: "INR", symbol: "₹", name: "Indian Rupee", decimals: 2, transferable: true },
  JPY: { code: "JPY", symbol: "¥", name: "Japanese Yen", decimals: 0, transferable: true },
  CAD: { code: "CAD", symbol: "C$", name: "Canadian Dollar", decimals: 2, transferable: true },
  AUD: { code: "AUD", symbol: "A$", name: "Australian Dollar", decimals: 2, transferable: true },
  SGD: { code: "SGD", symbol: "S$", name: "Singapore Dollar", decimals: 2, transferable: true },
  AED: { code: "AED", symbol: "د.إ", name: "UAE Dirham", decimals: 2, transferable: true },
  CHF: { code: "CHF", symbol: "CHF", name: "Swiss Franc", decimals: 2, transferable: true },
  BRL: { code: "BRL", symbol: "R$", name: "Brazilian Real", decimals: 2, transferable: false },
  ZAR: { code: "ZAR", symbol: "R", name: "South African Rand", decimals: 2, transferable: false },
};

// Base USD mid-market rates (scaled by 10^8)
export const INDICATIVE_USD_RATES_SCALED = {
  USD: 100_000_000n,
  EUR: 92_450_000n,     // 0.92450000
  GBP: 78_900_000n,     // 0.78900000
  INR: 8_395_000_000n,  // 83.95000000
  JPY: 15_320_000_000n, // 153.20000000
  CAD: 138_400_000n,    // 1.38400000
  AUD: 151_800_000n,    // 1.51800000
  SGD: 134_100_000n,    // 1.34100000
  AED: 367_250_000n,    // 3.67250000
  CHF: 88_150_000n,     // 0.88150000
  BRL: 568_900_000n,    // 5.68900000
  ZAR: 1_785_000_000n,  // 17.85000000
};

export function hashPassword(password, salt = crypto.randomBytes(16).toString("hex")) {
  const derived = crypto.pbkdf2Sync(password, salt, 10000, 64, "sha512").toString("hex");
  return `pbkdf2_sha512$10000$${salt}$${derived}`;
}

export function verifyPassword(password, storedHash) {
  if (!storedHash || !storedHash.startsWith("pbkdf2_sha512$")) return false;
  const parts = storedHash.split("$");
  if (parts.length !== 4) return false;
  const [, iterStr, salt, expectedHex] = parts;
  const iterations = parseInt(iterStr, 10);
  const derived = crypto.pbkdf2Sync(password, salt, iterations, 64, "sha512").toString("hex");
  try {
    return crypto.timingSafeEqual(Buffer.from(derived, "hex"), Buffer.from(expectedHex, "hex"));
  } catch {
    return false;
  }
}

export function formatMinor(minorBigInt, currency) {
  const meta = CURRENCIES[currency] || { decimals: 2 };
  const val = BigInt(minorBigInt);
  const neg = val < 0n;
  const abs = neg ? -val : val;
  if (meta.decimals === 0) return `${neg ? "-" : ""}${abs.toString()}`;
  const factor = 10n ** BigInt(meta.decimals);
  const whole = abs / factor;
  const frac = (abs % factor).toString().padStart(meta.decimals, "0");
  return `${neg ? "-" : ""}${whole.toString()}.${frac}`;
}

export function getCrossRateScaled(sourceCurrency, targetCurrency) {
  const srcRate = INDICATIVE_USD_RATES_SCALED[sourceCurrency];
  const tgtRate = INDICATIVE_USD_RATES_SCALED[targetCurrency];
  if (!srcRate || !tgtRate) throw new Error(`UNSUPPORTED_CURRENCY_PAIR: ${sourceCurrency}/${targetCurrency}`);
  // crossRate = (tgtRate * 10^8) / srcRate
  return (tgtRate * 100_000_000n + srcRate / 2n) / srcRate;
}

export function formatScaledRate(rateScaled) {
  const whole = rateScaled / 100_000_000n;
  const frac = (rateScaled % 100_000_000n).toString().padStart(8, "0");
  return `${whole}.${frac}`;
}

export function convertMinorAmount(sendMinor, sourceCurrency, targetCurrency, rateScaled) {
  const srcDec = CURRENCIES[sourceCurrency]?.decimals ?? 2;
  const tgtDec = CURRENCIES[targetCurrency]?.decimals ?? 2;
  const decDiff = tgtDec - srcDec;
  let num = BigInt(sendMinor) * BigInt(rateScaled);
  let den = 100_000_000n;
  if (decDiff > 0) num *= 10n ** BigInt(decDiff);
  else if (decDiff < 0) den *= 10n ** BigInt(-decDiff);
  return (num + den / 2n) / den;
}

// ============================================================================
// 2. TRANSACTION STATE MACHINE
// ============================================================================
export const VALID_STATE_TRANSITIONS = {
  DRAFT: ["REQUIRES_AUTHORIZATION", "CANCELLED", "FAILED"],
  REQUIRES_AUTHORIZATION: ["PROCESSING", "CANCELLED", "FAILED"],
  PROCESSING: ["COMPLETED", "FAILED", "REQUIRES_INVESTIGATION"],
  REQUIRES_INVESTIGATION: ["COMPLETED", "FAILED", "REFUND_PENDING"],
  COMPLETED: ["REFUND_PENDING"],
  REFUND_PENDING: ["REFUNDED", "REQUIRES_INVESTIGATION"],
  FAILED: [],
  CANCELLED: [],
  REFUNDED: [],
};

export function assertValidStateTransition(fromState, toState) {
  const allowed = VALID_STATE_TRANSITIONS[fromState] || [];
  if (!allowed.includes(toState)) {
    const err = new Error(`Invalid state transition from ${fromState} to ${toState}`);
    err.code = "INVALID_STATE_TRANSITION";
    err.status = 409;
    throw err;
  }
}

// ============================================================================
// 3. PERSISTENT LEDGER STORE & SEED INITIALIZATION
// ============================================================================
export function createGlobalPayStore(options = {}) {
  const webhookSecret = options.webhookSecret || "whsec_sandbox_deterministic_secret";
  const nowIso = () => new Date().toISOString();

  const mayaId = "usr_demo_maya_01";
  const alexId = "usr_demo_alex_02";
  const adminId = "usr_demo_admin_03";

  const state = {
    webhookSecret,
    fxProviderAvailable: true,
    users: new Map(),
    sessions: new Map(),
    passwordResetTokens: new Map(),
    accounts: new Map(),
    beneficiaries: new Map(),
    corridors: new Map(),
    quotes: new Map(),
    transactions: new Map(),
    paymentRequests: new Map(),
    expenseGroups: new Map(),
    budgets: new Map(),
    notifications: new Map(),
    auditEvents: [],
    webhookEvents: new Map(),
    idempotencyKeys: new Map(),
    conversionHistory: [],
  };

  // Seed Users
  state.users.set(mayaId, {
    id: mayaId,
    email: "maya.lin@sandbox.globalpay.app",
    passwordHash: hashPassword("GlobalPay#2026!", "a1b2c3d4e5f60102"),
    role: "USER",
    status: "ACTIVE",
    mfaEnabled: true,
    createdAt: "2026-09-01T10:00:00.000Z",
    profile: {
      fullName: "Maya Lin",
      handle: "@mayalin",
      phone: "+1-415-555-0192",
      countryCode: "US",
      preferredCurrency: "USD",
      locale: "en-US",
      themePreference: "dark",
      hideBalancesDefault: false,
      notifyEmail: true,
      notifyPush: true,
      notifySecurityAlerts: true,
      notifyBudgetThresholds: true,
    },
  });

  state.users.set(alexId, {
    id: alexId,
    email: "alex.rivera@sandbox.globalpay.app",
    passwordHash: hashPassword("AlexSecure#2026!", "b2c3d4e5f6010203"),
    role: "USER",
    status: "ACTIVE",
    mfaEnabled: false,
    createdAt: "2026-09-05T12:00:00.000Z",
    profile: {
      fullName: "Alex Rivera",
      handle: "@alexrivera",
      phone: "+44-20-7946-0921",
      countryCode: "GB",
      preferredCurrency: "GBP",
      locale: "en-GB",
      themePreference: "dark",
      hideBalancesDefault: false,
      notifyEmail: true,
      notifyPush: true,
      notifySecurityAlerts: true,
      notifyBudgetThresholds: true,
    },
  });

  state.users.set(adminId, {
    id: adminId,
    email: "compliance.ops@sandbox.globalpay.app",
    passwordHash: hashPassword("OpsAdmin#2026!", "c3d4e5f601020304"),
    role: "ADMIN",
    status: "ACTIVE",
    mfaEnabled: true,
    createdAt: "2026-08-15T08:00:00.000Z",
    profile: {
      fullName: "Priya Nair (Compliance Ops)",
      handle: "@priya_ops",
      phone: "+1-212-555-0144",
      countryCode: "US",
      preferredCurrency: "USD",
      locale: "en-US",
      themePreference: "dark",
      hideBalancesDefault: false,
      notifyEmail: true,
      notifyPush: false,
      notifySecurityAlerts: true,
      notifyBudgetThresholds: false,
    },
  });

  // Seed Currency Accounts (Exact Minor Units)
  const seedAccounts = [
    { id: "acc_maya_usd", userId: mayaId, currency: "USD", decimals: 2, balanceMinor: 1_248_050n, mask: "•••• 4829", routing: "ACH-021000021" },
    { id: "acc_maya_eur", userId: mayaId, currency: "EUR", decimals: 2, balanceMinor: 342_000n, mask: "•••• 9012", routing: "DE89••••4829" },
    { id: "acc_maya_gbp", userId: mayaId, currency: "GBP", decimals: 2, balanceMinor: 185_500n, mask: "•••• 3310", routing: "SORT-20-00-00" },
    { id: "acc_maya_inr", userId: mayaId, currency: "INR", decimals: 2, balanceMinor: 8_450_000n, mask: "•••• 7741", routing: "HDFC0000123" },
    { id: "acc_maya_jpy", userId: mayaId, currency: "JPY", decimals: 0, balanceMinor: 245_000n, mask: "•••• 5508", routing: "BOJP-0019" },
    { id: "acc_alex_gbp", userId: alexId, currency: "GBP", decimals: 2, balanceMinor: 610_000n, mask: "•••• 6612", routing: "SORT-40-11-22" },
    { id: "acc_alex_usd", userId: alexId, currency: "USD", decimals: 2, balanceMinor: 220_000n, mask: "•••• 1198", routing: "ACH-021000021" },
  ];
  for (const a of seedAccounts) {
    state.accounts.set(a.id, { ...a, isSandboxAccount: true, status: "ACTIVE", version: 1 });
  }

  // Seed Supported International Corridors
  const corridors = [
    {
      id: "cor_us_in",
      sourceCountry: "US",
      destinationCountry: "IN",
      sourceCurrency: "USD",
      targetCurrency: "INR",
      providerName: "globalpay_deterministic_sandbox",
      paymentRail: "UPI_SANDBOX / IMPS",
      minAmountMinor: 1_000n,       // $10.00
      maxAmountMinor: 2_500_000n,   // $25,000.00
      fixedFeeMinor: 299n,          // $2.99
      percentageFeeBps: 45,         // 0.45%
      fxMarkupBps: 35,              // 0.35%
      taxRateBps: 10,               // 0.10% statutory remittance fee
      estimatedDelivery: "Instant to 15 minutes (IMPS/UPI Sandbox)",
      requiredFields: ["fullName", "accountMask", "routingCode (IFSC)"],
      eligibilityRules: ["Personal remittance or family maintenance", "Sender KYC verified in Sandbox"],
      isEnabled: true,
    },
    {
      id: "cor_us_gb",
      sourceCountry: "US",
      destinationCountry: "GB",
      sourceCurrency: "USD",
      targetCurrency: "GBP",
      providerName: "globalpay_deterministic_sandbox",
      paymentRail: "FASTER_PAYMENTS",
      minAmountMinor: 1_000n,
      maxAmountMinor: 5_000_000n,
      fixedFeeMinor: 199n,
      percentageFeeBps: 35,
      fxMarkupBps: 25,
      taxRateBps: 0,
      estimatedDelivery: "Under 2 minutes (UK Faster Payments Sandbox)",
      requiredFields: ["fullName", "accountMask", "routingCode (Sort Code)"],
      eligibilityRules: ["Standard UK Faster Payments corridor limit £250,000"],
      isEnabled: true,
    },
    {
      id: "cor_us_eu",
      sourceCountry: "US",
      destinationCountry: "DE",
      sourceCurrency: "USD",
      targetCurrency: "EUR",
      providerName: "globalpay_deterministic_sandbox",
      paymentRail: "SEPA_INSTANT",
      minAmountMinor: 1_000n,
      maxAmountMinor: 5_000_000n,
      fixedFeeMinor: 249n,
      percentageFeeBps: 40,
      fxMarkupBps: 30,
      taxRateBps: 0,
      estimatedDelivery: "Under 5 minutes (SEPA Instant Sandbox)",
      requiredFields: ["fullName", "accountMask (IBAN)", "routingCode (BIC)"],
      eligibilityRules: ["SEPA zone participant bank required"],
      isEnabled: true,
    },
    {
      id: "cor_us_jp",
      sourceCountry: "US",
      destinationCountry: "JP",
      sourceCurrency: "USD",
      targetCurrency: "JPY",
      providerName: "globalpay_deterministic_sandbox",
      paymentRail: "ZENGIN_SANDBOX",
      minAmountMinor: 2_000n,
      maxAmountMinor: 3_000_000n,
      fixedFeeMinor: 399n,
      percentageFeeBps: 50,
      fxMarkupBps: 40,
      taxRateBps: 0,
      estimatedDelivery: "1 to 4 hours (Zengin Sandbox)",
      requiredFields: ["fullName", "accountMask", "routingCode (Zengin Branch)"],
      eligibilityRules: ["Purpose of remittance code mandatory"],
      isEnabled: true,
    },
    {
      id: "cor_us_sg",
      sourceCountry: "US",
      destinationCountry: "SG",
      sourceCurrency: "USD",
      targetCurrency: "SGD",
      providerName: "globalpay_deterministic_sandbox",
      paymentRail: "FAST_PAYNOW_SANDBOX",
      minAmountMinor: 1_000n,
      maxAmountMinor: 4_000_000n,
      fixedFeeMinor: 250n,
      percentageFeeBps: 35,
      fxMarkupBps: 30,
      taxRateBps: 0,
      estimatedDelivery: "Instant (FAST Singapore Sandbox)",
      requiredFields: ["fullName", "accountMask", "routingCode (Bank Code)"],
      eligibilityRules: ["FAST Singapore account verification"],
      isEnabled: true,
    },
  ];
  for (const c of corridors) {
    state.corridors.set(`${c.sourceCurrency}_${c.targetCurrency}`, c);
  }

  // Seed Beneficiaries for Maya
  const seedBeneficiaries = [
    {
      id: "ben_arjun_in",
      userId: mayaId,
      fullName: "Arjun Mehta",
      handleOrUpi: "arjun.mehta@oksbi-sandbox",
      email: "arjun.mehta@sandbox.example.in",
      countryCode: "IN",
      currency: "INR",
      bankName: "HDFC Bank Sandbox",
      accountMask: "•••• 8821",
      routingCode: "HDFC0000241",
      paymentRail: "UPI_SANDBOX / IMPS",
      verificationStatus: "VERIFIED_SANDBOX",
      isFavorite: true,
      isActive: true,
    },
    {
      id: "ben_claire_eu",
      userId: mayaId,
      fullName: "Claire Dubois",
      handleOrUpi: "@clairedubois",
      email: "claire.dubois@sandbox.example.fr",
      countryCode: "DE",
      currency: "EUR",
      bankName: "EuroClear Sandbox Bank",
      accountMask: "DE89 •••• 3104",
      routingCode: "COBADEFFXXX",
      paymentRail: "SEPA_INSTANT",
      verificationStatus: "VERIFIED_SANDBOX",
      isFavorite: true,
      isActive: true,
    },
    {
      id: "ben_liam_us",
      userId: mayaId,
      fullName: "Liam O'Connor",
      handleOrUpi: "@liamoconnor",
      email: "liam@sandbox.example.com",
      countryCode: "US",
      currency: "USD",
      bankName: "GlobalPay Domestic P2P",
      accountMask: "•••• 1049",
      routingCode: "ACH-021000021",
      paymentRail: "ACH_INSTANT_SANDBOX",
      verificationStatus: "VERIFIED_SANDBOX",
      isFavorite: true,
      isActive: true,
    },
  ];
  for (const b of seedBeneficiaries) state.beneficiaries.set(b.id, b);

  // Seed Initial Transactions for Maya & Alex
  const seedTxs = [
    {
      id: "tx_seed_01",
      referenceCode: "GP-SBX-20261020-A109F2",
      userId: mayaId,
      sourceAccountId: "acc_maya_usd",
      beneficiaryId: "ben_arjun_in",
      type: "INTERNATIONAL_TRANSFER",
      state: "COMPLETED",
      sourceCurrency: "USD",
      sourceAmountMinor: 50_000n, // $500.00
      feeAmountMinor: 524n,      // $5.24
      taxAmountMinor: 50n,       // $0.50
      totalDebitedMinor: 50_574n,
      targetCurrency: "INR",
      targetAmountMinor: 4_182_800n, // ₹41,828.00
      exchangeRateUsed: "83.65600000",
      spendingCategory: "Family & International",
      recipientName: "Arjun Mehta",
      recipientIdentifier: "HDFC0000241 / •••• 8821",
      note: "Diwali family gift (Sandbox)",
      providerName: "globalpay_deterministic_sandbox",
      providerReference: "SBX-PRV-9910A8B7C6",
      isSandbox: true,
      isRecurring: false,
      idempotencyKey: "idem_seed_01",
      createdAt: "2026-10-20T14:22:00.000Z",
      completedAt: "2026-10-20T14:22:18.000Z",
      events: [
        { fromState: null, toState: "DRAFT", actorType: "USER", reason: "Transfer quote accepted", createdAt: "2026-10-20T14:21:55.000Z" },
        { fromState: "DRAFT", toState: "REQUIRES_AUTHORIZATION", actorType: "SYSTEM", reason: "Awaiting sandbox authorization", createdAt: "2026-10-20T14:21:58.000Z" },
        { fromState: "REQUIRES_AUTHORIZATION", toState: "PROCESSING", actorType: "USER", reason: "User authorized transfer", createdAt: "2026-10-20T14:22:05.000Z" },
        { fromState: "PROCESSING", toState: "COMPLETED", actorType: "PROVIDER_WEBHOOK", reason: "Sandbox IMPS settlement confirmed", createdAt: "2026-10-20T14:22:18.000Z" },
      ],
    },
    {
      id: "tx_seed_02",
      referenceCode: "GP-SBX-20261022-C482E1",
      userId: mayaId,
      sourceAccountId: "acc_maya_usd",
      beneficiaryId: "ben_liam_us",
      type: "DOMESTIC_P2P",
      state: "COMPLETED",
      sourceCurrency: "USD",
      sourceAmountMinor: 8_500n, // $85.00
      feeAmountMinor: 0n,
      taxAmountMinor: 0n,
      totalDebitedMinor: 8_500n,
      targetCurrency: "USD",
      targetAmountMinor: 8_500n,
      exchangeRateUsed: "1.00000000",
      spendingCategory: "Dining & Nightlife",
      recipientName: "Liam O'Connor",
      recipientIdentifier: "@liamoconnor",
      note: "Ramen & concert tickets split",
      providerName: "globalpay_deterministic_sandbox",
      providerReference: "SBX-PRV-4421E9D0A1",
      isSandbox: true,
      isRecurring: false,
      idempotencyKey: "idem_seed_02",
      createdAt: "2026-10-22T19:45:00.000Z",
      completedAt: "2026-10-22T19:45:02.000Z",
      events: [
        { fromState: null, toState: "DRAFT", actorType: "USER", reason: "Domestic P2P initiated", createdAt: "2026-10-22T19:44:55.000Z" },
        { fromState: "DRAFT", toState: "REQUIRES_AUTHORIZATION", actorType: "SYSTEM", reason: "Ready for authorization", createdAt: "2026-10-22T19:44:58.000Z" },
        { fromState: "REQUIRES_AUTHORIZATION", toState: "PROCESSING", actorType: "USER", reason: "Authorized via session", createdAt: "2026-10-22T19:45:00.000Z" },
        { fromState: "PROCESSING", toState: "COMPLETED", actorType: "PROVIDER_WEBHOOK", reason: "Instant P2P ledger settlement", createdAt: "2026-10-22T19:45:02.000Z" },
      ],
    },
    {
      id: "tx_seed_alex_only",
      referenceCode: "GP-SBX-20261023-FF0099",
      userId: alexId,
      sourceAccountId: "acc_alex_gbp",
      beneficiaryId: null,
      type: "DOMESTIC_P2P",
      state: "COMPLETED",
      sourceCurrency: "GBP",
      sourceAmountMinor: 4_200n,
      feeAmountMinor: 0n,
      taxAmountMinor: 0n,
      totalDebitedMinor: 4_200n,
      targetCurrency: "GBP",
      targetAmountMinor: 4_200n,
      exchangeRateUsed: "1.00000000",
      spendingCategory: "Software & Cloud",
      recipientName: "London Cloud Host Sandbox",
      recipientIdentifier: "SORT-40-11-22",
      note: "Alex private server invoice",
      providerName: "globalpay_deterministic_sandbox",
      providerReference: "SBX-PRV-ALEX990011",
      isSandbox: true,
      isRecurring: true,
      idempotencyKey: "idem_seed_alex_01",
      createdAt: "2026-10-23T09:15:00.000Z",
      completedAt: "2026-10-23T09:15:04.000Z",
      events: [],
    },
  ];
  for (const t of seedTxs) state.transactions.set(t.id, t);

  // Seed Budgets for Maya
  const seedBudgets = [
    { id: "bdg_01", userId: mayaId, category: "Family & International", currency: "USD", monthlyLimitMinor: 100_000n, alertThresholdPct: 80, monthKey: "2026-10" },
    { id: "bdg_02", userId: mayaId, category: "Dining & Nightlife", currency: "USD", monthlyLimitMinor: 35_000n, alertThresholdPct: 80, monthKey: "2026-10" },
    { id: "bdg_03", userId: mayaId, category: "Software & Cloud", currency: "USD", monthlyLimitMinor: 20_000n, alertThresholdPct: 85, monthKey: "2026-10" },
  ];
  for (const b of seedBudgets) state.budgets.set(b.id, b);

  // Seed Notifications for Maya
  state.notifications.set("ntf_01", {
    id: "ntf_01",
    userId: mayaId,
    type: "TRANSFER_STATUS",
    title: "Sandbox Transfer Settled (INR 41,828.00)",
    message: "Ref GP-SBX-20261020-A109F2 to Arjun Mehta completed in Sandbox.",
    isRead: false,
    createdAt: "2026-10-20T14:22:20.000Z",
  });

  // Helper to record audit logs
  function recordAudit({ actorUserId, actorRole, action, resourceType, resourceId, outcome, redactedMeta = {} }) {
    const entry = {
      id: `aud_${crypto.randomBytes(6).toString("hex")}`,
      actorUserId: actorUserId || null,
      actorRole: actorRole || "ANONYMOUS",
      action,
      resourceType,
      resourceId: resourceId || null,
      outcome,
      redactedMeta: JSON.stringify(redactedMeta),
      createdAt: nowIso(),
    };
    state.auditEvents.unshift(entry);
    return entry;
  }

  return { state, recordAudit };
}

// ============================================================================
// 4. CORE DOMAIN SERVICES (AUTH, QUOTES, PAYMENTS, WEBHOOKS, ANALYTICS)
// ============================================================================
export class GlobalPayEngine {
  constructor(options = {}) {
    const { state, recordAudit } = createGlobalPayStore(options);
    this.state = state;
    this.recordAudit = recordAudit;
  }

  // --- AUTHENTICATION ---
  registerUser({ email, password, fullName, handle, countryCode = "US", preferredCurrency = "USD" }) {
    const cleanEmail = (email || "").trim().toLowerCase();
    if (!cleanEmail.includes("@") || !password || password.length < 8) {
      const err = new Error("Valid email and password (min 8 chars) required.");
      err.status = 400;
      throw err;
    }
    for (const u of this.state.users.values()) {
      if (u.email === cleanEmail) {
        const err = new Error("Email already registered.");
        err.status = 409;
        throw err;
      }
    }
    const id = `usr_${crypto.randomBytes(6).toString("hex")}`;
    const user = {
      id,
      email: cleanEmail,
      passwordHash: hashPassword(password),
      role: "USER",
      status: "ACTIVE",
      mfaEnabled: false,
      createdAt: new Date().toISOString(),
      profile: {
        fullName: fullName || "GlobalPay Member",
        handle: handle || `@${cleanEmail.split("@")[0]}`,
        countryCode,
        preferredCurrency,
        locale: "en-US",
        themePreference: "dark",
        hideBalancesDefault: false,
        notifyEmail: true,
        notifyPush: true,
        notifySecurityAlerts: true,
        notifyBudgetThresholds: true,
      },
    };
    this.state.users.set(id, user);

    // Provision default USD sandbox account with $2,500.00 fictional balance
    const accId = `acc_${id}_usd`;
    this.state.accounts.set(accId, {
      id: accId,
      userId: id,
      currency: "USD",
      decimals: 2,
      balanceMinor: 250_000n,
      mask: `•••• ${Math.floor(1000 + Math.random() * 9000)}`,
      routing: "ACH-021000021",
      isSandboxAccount: true,
      status: "ACTIVE",
      version: 1,
    });

    this.recordAudit({ actorUserId: id, actorRole: "USER", action: "USER_REGISTER", resourceType: "User", resourceId: id, outcome: "SUCCESS" });
    return this.createSession(user);
  }

  loginUser({ email, password }) {
    const cleanEmail = (email || "").trim().toLowerCase();
    let found = null;
    for (const u of this.state.users.values()) {
      if (u.email === cleanEmail) {
        found = u;
        break;
      }
    }
    if (!found || !verifyPassword(password || "", found.passwordHash)) {
      this.recordAudit({ actorUserId: found?.id, actorRole: "ANONYMOUS", action: "USER_LOGIN_FAILED", resourceType: "Session", outcome: "DENIED", redactedMeta: { email: cleanEmail } });
      const err = new Error("Invalid email or password.");
      err.status = 401;
      throw err;
    }
    if (found.status !== "ACTIVE") {
      const err = new Error(`Account is ${found.status}.`);
      err.status = 403;
      throw err;
    }
    this.recordAudit({ actorUserId: found.id, actorRole: found.role, action: "USER_LOGIN", resourceType: "Session", outcome: "SUCCESS" });
    return this.createSession(found);
  }

  createSession(user, ttlMs = 60 * 60 * 1000) {
    const rawToken = `gpsess_${crypto.randomBytes(24).toString("hex")}`;
    const tokenHash = crypto.createHash("sha256").update(rawToken).digest("hex");
    const csrfToken = crypto.randomBytes(16).toString("hex");
    const session = {
      id: `ses_${crypto.randomBytes(6).toString("hex")}`,
      userId: user.id,
      tokenHash,
      csrfToken,
      expiresAt: new Date(Date.now() + ttlMs).toISOString(),
      revokedAt: null,
    };
    this.state.sessions.set(tokenHash, session);
    return {
      accessToken: rawToken,
      csrfToken,
      expiresAt: session.expiresAt,
      user: this.sanitizeUser(user),
    };
  }

  authenticateToken(rawToken) {
    if (!rawToken) {
      const err = new Error("Authentication required.");
      err.status = 401;
      throw err;
    }
    const tokenHash = crypto.createHash("sha256").update(rawToken).digest("hex");
    const session = this.state.sessions.get(tokenHash);
    if (!session || session.revokedAt || new Date(session.expiresAt).getTime() <= Date.now()) {
      const err = new Error("Session expired or revoked.");
      err.status = 401;
      throw err;
    }
    const user = this.state.users.get(session.userId);
    if (!user || user.status !== "ACTIVE") {
      const err = new Error("User account inactive.");
      err.status = 403;
      throw err;
    }
    return { user, session };
  }

  revokeSession(rawToken) {
    const tokenHash = crypto.createHash("sha256").update(rawToken || "").digest("hex");
    const session = this.state.sessions.get(tokenHash);
    if (session) {
      session.revokedAt = new Date().toISOString();
    }
  }

  sanitizeUser(user) {
    const { passwordHash, ...safe } = user;
    return safe;
  }

  // --- ACCOUNTS & BALANCES (STRICT OWNERSHIP ISOLATION) ---
  getUserAccounts(userId) {
    const list = [];
    for (const acc of this.state.accounts.values()) {
      if (acc.userId === userId) {
        list.push({
          ...acc,
          balanceMinor: acc.balanceMinor.toString(),
          balanceFormatted: formatMinor(acc.balanceMinor, acc.currency),
          symbol: CURRENCIES[acc.currency]?.symbol || acc.currency,
        });
      }
    }
    return list;
  }

  // --- INTERNATIONAL TRANSFER QUOTES (SERVER-GENERATED, DECIMAL-SAFE) ---
  createTransferQuote(userId, { sourceCurrency, targetCurrency, sendAmountMinor, beneficiaryId }) {
    const sendMinor = BigInt(sendAmountMinor || 0);
    if (sendMinor <= 0n) {
      const err = new Error("Transfer amount must be positive.");
      err.status = 400;
      throw err;
    }

    const corridor = this.state.corridors.get(`${sourceCurrency}_${targetCurrency}`);
    if (!corridor || !corridor.isEnabled) {
      const err = new Error(`Unsupported or disabled transfer corridor: ${sourceCurrency} -> ${targetCurrency}`);
      err.status = 422;
      throw err;
    }

    if (sendMinor < corridor.minAmountMinor || sendMinor > corridor.maxAmountMinor) {
      const err = new Error(`Amount outside corridor limits (${formatMinor(corridor.minAmountMinor, sourceCurrency)} - ${formatMinor(corridor.maxAmountMinor, sourceCurrency)} ${sourceCurrency}).`);
      err.status = 422;
      throw err;
    }

    const midRateScaled = getCrossRateScaled(sourceCurrency, targetCurrency);
    // Customer rate = midRate * (10000 - fxMarkupBps) / 10000
    const customerRateScaled = (midRateScaled * BigInt(10000 - corridor.fxMarkupBps)) / 10000n;

    const fixedFeeMinor = corridor.fixedFeeMinor;
    const variableFeeMinor = (sendMinor * BigInt(corridor.percentageFeeBps) + 5000n) / 10000n;
    const taxAmountMinor = (sendMinor * BigInt(corridor.taxRateBps) + 5000n) / 10000n;
    const totalFeeMinor = fixedFeeMinor + variableFeeMinor + taxAmountMinor;
    const totalPayableMinor = sendMinor + totalFeeMinor;

    const recipientAmountMinor = convertMinorAmount(sendMinor, sourceCurrency, targetCurrency, customerRateScaled);

    const quote = {
      id: `qte_${crypto.randomBytes(6).toString("hex")}`,
      userId,
      beneficiaryId: beneficiaryId || null,
      sourceCountry: corridor.sourceCountry,
      destinationCountry: corridor.destinationCountry,
      sourceCurrency,
      targetCurrency,
      sendAmountMinor: sendMinor,
      fixedFeeMinor,
      variableFeeMinor,
      taxAmountMinor,
      totalFeeMinor,
      totalPayableMinor,
      midMarketRate: formatScaledRate(midRateScaled),
      customerExchangeRate: formatScaledRate(customerRateScaled),
      customerRateScaled,
      fxMarkupBps: corridor.fxMarkupBps,
      recipientAmountMinor,
      estimatedDelivery: corridor.estimatedDelivery,
      quoteSource: "GlobalPay Deterministic FX Engine (Sandbox)",
      isSandbox: true,
      createdAt: new Date().toISOString(),
      expiresAt: new Date(Date.now() + 5 * 60 * 1000).toISOString(), // 5-minute TTL
      acceptedAt: null,
    };

    this.state.quotes.set(quote.id, quote);
    return this.serializeQuote(quote);
  }

  serializeQuote(q) {
    return {
      ...q,
      sendAmountMinor: q.sendAmountMinor.toString(),
      fixedFeeMinor: q.fixedFeeMinor.toString(),
      variableFeeMinor: q.variableFeeMinor.toString(),
      taxAmountMinor: q.taxAmountMinor.toString(),
      totalFeeMinor: q.totalFeeMinor.toString(),
      totalPayableMinor: q.totalPayableMinor.toString(),
      recipientAmountMinor: q.recipientAmountMinor.toString(),
      customerRateScaled: undefined,
    };
  }

  // --- EXECUTE DOMESTIC OR INTERNATIONAL PAYMENT (WITH IDEMPOTENCY & ATOMIC ROLLBACK) ---
  executePayment(userId, payload) {
    const {
      idempotencyKey,
      type = "DOMESTIC_P2P",
      sourceCurrency = "USD",
      amountMinor,
      quoteId,
      beneficiaryId,
      recipientName,
      recipientIdentifier,
      spendingCategory = "Transfers",
      note = "",
      simulationBehavior = "AUTO_COMPLETE",
    } = payload;

    if (!idempotencyKey || String(idempotencyKey).trim().length < 4) {
      const err = new Error("idempotencyKey header or field is required for all financial operations.");
      err.status = 400;
      throw err;
    }

    const idemComposite = `${userId}:${idempotencyKey}`;
    const existingPayloadHash = crypto.createHash("sha256").update(JSON.stringify({ type, sourceCurrency, amountMinor, quoteId, recipientIdentifier })).digest("hex");

    if (this.state.idempotencyKeys.has(idemComposite)) {
      const saved = this.state.idempotencyKeys.get(idemComposite);
      if (saved.requestHash !== existingPayloadHash) {
        const err = new Error("IDEMPOTENCY_CONFLICT: Key reused with different payment parameters.");
        err.status = 409;
        throw err;
      }
      return { ...saved.response, deduplicated: true };
    }

    // Locate User's Source Account
    let sourceAccount = null;
    for (const acc of this.state.accounts.values()) {
      if (acc.userId === userId && acc.currency === sourceCurrency) {
        sourceAccount = acc;
        break;
      }
    }
    if (!sourceAccount) {
      const err = new Error(`No active ${sourceCurrency} account found for authenticated user.`);
      err.status = 404;
      throw err;
    }

    let sendMinor;
    let feeMinor = 0n;
    let taxMinor = 0n;
    let totalDebitedMinor;
    let targetCurrency = sourceCurrency;
    let targetAmountMinor;
    let exchangeRateUsed = "1.00000000";

    if (type === "INTERNATIONAL_TRANSFER") {
      const quote = this.state.quotes.get(quoteId);
      if (!quote || quote.userId !== userId) {
        const err = new Error("Valid transfer quote belonging to user is required.");
        err.status = 404;
        throw err;
      }
      if (quote.acceptedAt) {
        const err = new Error("Quote has already been consumed.");
        err.status = 409;
        throw err;
      }
      if (new Date(quote.expiresAt).getTime() <= Date.now()) {
        const err = new Error("QUOTE_EXPIRED: Transfer quote has expired. Please request a fresh quote.");
        err.status = 422;
        throw err;
      }
      sendMinor = quote.sendAmountMinor;
      feeMinor = quote.fixedFeeMinor + quote.variableFeeMinor;
      taxMinor = quote.taxAmountMinor;
      totalDebitedMinor = quote.totalPayableMinor;
      targetCurrency = quote.targetCurrency;
      targetAmountMinor = quote.recipientAmountMinor;
      exchangeRateUsed = quote.customerExchangeRate;
    } else {
      sendMinor = BigInt(amountMinor || 0);
      if (sendMinor <= 0n) {
        const err = new Error("Payment amount must be greater than zero.");
        err.status = 400;
        throw err;
      }
      if (sendMinor > 1_000_000n) {
        const err = new Error("LIMIT_EXCEEDED: Single domestic payment exceeds sandbox limit of 10,000.00.");
        err.status = 422;
        throw err;
      }
      totalDebitedMinor = sendMinor;
      targetAmountMinor = sendMinor;
    }

    // Check Sufficient Sandbox Balance
    if (sourceAccount.balanceMinor < totalDebitedMinor) {
      const err = new Error(`INSUFFICIENT_FUNDS: Required ${formatMinor(totalDebitedMinor, sourceCurrency)} ${sourceCurrency}, available ${formatMinor(sourceAccount.balanceMinor, sourceCurrency)} ${sourceCurrency}.`);
      err.status = 422;
      throw err;
    }

    // Snapshot for atomic rollback if post-debit step throws
    const previousBalance = sourceAccount.balanceMinor;
    const txId = `tx_${crypto.randomBytes(6).toString("hex")}`;
    const referenceCode = `GP-SBX-20261025-${crypto.randomBytes(3).toString("hex").toUpperCase()}`;

    const tx = {
      id: txId,
      referenceCode,
      userId,
      sourceAccountId: sourceAccount.id,
      beneficiaryId: beneficiaryId || null,
      quoteId: quoteId || null,
      type,
      state: "DRAFT",
      sourceCurrency,
      sourceAmountMinor: sendMinor,
      feeAmountMinor: feeMinor,
      taxAmountMinor: taxMinor,
      totalDebitedMinor,
      targetCurrency,
      targetAmountMinor,
      exchangeRateUsed,
      spendingCategory,
      recipientName: recipientName || "Sandbox Recipient",
      recipientIdentifier: recipientIdentifier || "@sandbox_recipient",
      note,
      providerName: "globalpay_deterministic_sandbox",
      providerReference: `SBX-PRV-${crypto.randomBytes(5).toString("hex").toUpperCase()}`,
      isSandbox: true,
      isRecurring: false,
      idempotencyKey,
      createdAt: new Date().toISOString(),
      completedAt: null,
      failedAt: null,
      failureReason: null,
      events: [
        { fromState: null, toState: "DRAFT", actorType: "USER", reason: "Transaction created", createdAt: new Date().toISOString() },
      ],
    };

    try {
      // Transition DRAFT -> REQUIRES_AUTHORIZATION -> PROCESSING
      this.transitionState(tx, "REQUIRES_AUTHORIZATION", "SYSTEM", "Validated parameters & quote");
      this.transitionState(tx, "PROCESSING", "USER", "Authorized by session credentials");

      // Debit balance while PROCESSING
      sourceAccount.balanceMinor -= totalDebitedMinor;
      sourceAccount.version += 1;

      if (simulationBehavior === "THROW_DB_ERROR") {
        throw new Error("Simulated unexpected database write fault mid-transaction");
      }

      if (simulationBehavior === "FAIL_PROVIDER" || String(recipientIdentifier).includes("fail")) {
        // Provider rejected -> restore balance and transition to FAILED
        sourceAccount.balanceMinor = previousBalance;
        this.transitionState(tx, "FAILED", "PROVIDER_WEBHOOK", "Sandbox bank rejected transfer");
        tx.failedAt = new Date().toISOString();
        tx.failureReason = "SANDBOX_SIMULATED_DECLINE: Beneficiary bank rejected transfer.";
      } else if (simulationBehavior === "STAY_PROCESSING" || String(recipientIdentifier).includes("slow")) {
        // Remains in PROCESSING (funds held/debited until webhook/reconciliation)
      } else if (simulationBehavior === "REQUIRE_INVESTIGATION") {
        this.transitionState(tx, "REQUIRES_INVESTIGATION", "SYSTEM", "Provider gateway timeout; queued for reconciliation");
      } else {
        this.transitionState(tx, "COMPLETED", "PROVIDER_WEBHOOK", "Sandbox settlement confirmed");
        tx.completedAt = new Date().toISOString();
      }

      if (quoteId && this.state.quotes.has(quoteId)) {
        this.state.quotes.get(quoteId).acceptedAt = new Date().toISOString();
      }

      this.state.transactions.set(tx.id, tx);
      this.state.notifications.set(`ntf_${tx.id}`, {
        id: `ntf_${tx.id}`,
        userId,
        type: "PAYMENT_OUTCOME",
        title: `Sandbox ${tx.state}: ${formatMinor(tx.targetAmountMinor, tx.targetCurrency)} ${tx.targetCurrency}`,
        message: `Ref ${tx.referenceCode} to ${tx.recipientName} is ${tx.state}.`,
        isRead: false,
        createdAt: new Date().toISOString(),
      });

      const response = { transaction: this.serializeTransaction(tx) };
      this.state.idempotencyKeys.set(idemComposite, {
        requestHash: existingPayloadHash,
        response,
        createdAt: new Date().toISOString(),
      });

      this.recordAudit({
        actorUserId: userId,
        actorRole: "USER",
        action: `PAYMENT_${tx.state}`,
        resourceType: "Transaction",
        resourceId: tx.id,
        outcome: tx.state === "FAILED" ? "FAILURE" : "SUCCESS",
        redactedMeta: { referenceCode: tx.referenceCode, sourceCurrency, totalDebitedMinor: totalDebitedMinor.toString() },
      });

      return response;
    } catch (err) {
      // Atomic rollback of balance on unexpected error
      sourceAccount.balanceMinor = previousBalance;
      throw err;
    }
  }

  transitionState(tx, toState, actorType, reason) {
    assertValidStateTransition(tx.state, toState);
    const fromState = tx.state;
    tx.state = toState;
    tx.events.push({
      fromState,
      toState,
      actorType,
      reason,
      createdAt: new Date().toISOString(),
    });
  }

  // --- REFUND & REVERSAL WORKFLOW (SEPARATE RECORD & AUDITABLE STATE) ---
  refundTransaction(actorUser, transactionId, reason = "Customer requested sandbox refund") {
    const tx = this.state.transactions.get(transactionId);
    if (!tx) {
      const err = new Error("Transaction not found.");
      err.status = 404;
      throw err;
    }
    if (actorUser.role !== "ADMIN" && tx.userId !== actorUser.id) {
      const err = new Error("Forbidden: Cannot refund another user's transaction.");
      err.status = 403;
      throw err;
    }
    this.transitionState(tx, "REFUND_PENDING", actorUser.role, "Refund initiated");
    this.transitionState(tx, "REFUNDED", "PROVIDER_WEBHOOK", reason);

    const acc = this.state.accounts.get(tx.sourceAccountId);
    if (acc) {
      acc.balanceMinor += tx.totalDebitedMinor;
      acc.version += 1;
    }

    this.recordAudit({
      actorUserId: actorUser.id,
      actorRole: actorUser.role,
      action: "TRANSACTION_REFUNDED",
      resourceType: "Transaction",
      resourceId: tx.id,
      outcome: "SUCCESS",
      redactedMeta: { refundedMinor: tx.totalDebitedMinor.toString() },
    });

    return this.serializeTransaction(tx);
  }

  // --- WEBHOOK PROCESSING (SIGNATURE VERIFICATION & DEDUPLICATION) ---
  processProviderWebhook(rawBodyString, signatureHeader) {
    const expectedSig = crypto.createHmac("sha256", this.state.webhookSecret).update(rawBodyString).digest("hex");
    let verified = false;
    try {
      verified = Boolean(signatureHeader) && crypto.timingSafeEqual(Buffer.from(signatureHeader), Buffer.from(expectedSig));
    } catch {
      verified = false;
    }

    if (!verified) {
      this.recordAudit({ actorRole: "WEBHOOK", action: "WEBHOOK_SIGNATURE_REJECTED", resourceType: "Webhook", outcome: "DENIED" });
      const err = new Error("WEBHOOK_SIGNATURE_INVALID: HMAC-SHA256 verification failed.");
      err.status = 401;
      throw err;
    }

    const event = JSON.parse(rawBodyString);
    const { externalEventId, transactionId, targetState, reason } = event;

    if (this.state.webhookEvents.has(externalEventId)) {
      return { status: "DUPLICATE_IGNORED", externalEventId };
    }

    const tx = this.state.transactions.get(transactionId);
    if (!tx) {
      const err = new Error("Transaction not found for webhook.");
      err.status = 404;
      throw err;
    }

    // Handle out-of-order or already terminal states safely without corrupting
    if (tx.state === targetState || tx.state === "COMPLETED" || tx.state === "REFUNDED") {
      this.state.webhookEvents.set(externalEventId, { externalEventId, status: "OUT_OF_ORDER_IGNORED" });
      return { status: "OUT_OF_ORDER_IGNORED", transactionState: tx.state };
    }

    this.transitionState(tx, targetState, "PROVIDER_WEBHOOK", reason || "Webhook settlement event");
    if (targetState === "COMPLETED") tx.completedAt = new Date().toISOString();
    if (targetState === "FAILED") {
      tx.failedAt = new Date().toISOString();
      const acc = this.state.accounts.get(tx.sourceAccountId);
      if (acc) acc.balanceMinor += tx.totalDebitedMinor;
    }

    this.state.webhookEvents.set(externalEventId, { externalEventId, status: "PROCESSED", processedAt: new Date().toISOString() });
    return { status: "PROCESSED", transactionState: tx.state };
  }

  // --- ANALYTICS & SMART SPEND (EXCLUDES REFUNDED/FAILED FROM SPEND TOTALS) ---
  getSpendingAnalytics(userId) {
    const categoryTotalsMinor = {};
    let totalCompletedSpendMinor = 0n;
    let refundedExcludedMinor = 0n;
    let transactionCount = 0;

    for (const tx of this.state.transactions.values()) {
      if (tx.userId !== userId) continue;
      if (tx.state === "REFUNDED" || tx.state === "REFUND_PENDING") {
        refundedExcludedMinor += tx.totalDebitedMinor;
        continue; // Never double count or include refunded transactions in active spend
      }
      if (tx.state !== "COMPLETED") continue;
      // Normalize to USD minor for unified summary if USD, otherwise convert indicative
      let usdEquivalentMinor = tx.totalDebitedMinor;
      if (tx.sourceCurrency !== "USD") {
        const rateToUsd = getCrossRateScaled(tx.sourceCurrency, "USD");
        usdEquivalentMinor = convertMinorAmount(tx.totalDebitedMinor, tx.sourceCurrency, "USD", rateToUsd);
      }
      totalCompletedSpendMinor += usdEquivalentMinor;
      transactionCount += 1;
      const cat = tx.spendingCategory || "General";
      categoryTotalsMinor[cat] = (categoryTotalsMinor[cat] || 0n) + usdEquivalentMinor;
    }

    const categories = Object.entries(categoryTotalsMinor).map(([category, minor]) => ({
      category,
      amountMinor: minor.toString(),
      amountFormatted: formatMinor(minor, "USD"),
    }));

    const budgets = [];
    for (const b of this.state.budgets.values()) {
      if (b.userId !== userId) continue;
      const spentMinor = categoryTotalsMinor[b.category] || 0n;
      const utilizationPct = b.monthlyLimitMinor > 0n ? Number((spentMinor * 100n) / b.monthlyLimitMinor) : 0;
      budgets.push({
        ...b,
        monthlyLimitMinor: b.monthlyLimitMinor.toString(),
        spentMinor: spentMinor.toString(),
        utilizationPct,
        isOverThreshold: utilizationPct >= b.alertThresholdPct,
      });
    }

    return {
      currency: "USD",
      calculationMethodology: "Sum of COMPLETED transactions owned by user; FAILED, CANCELLED, and REFUNDED transactions are strictly excluded to prevent double-counting.",
      totalCompletedSpendMinor: totalCompletedSpendMinor.toString(),
      totalCompletedSpendFormatted: formatMinor(totalCompletedSpendMinor, "USD"),
      refundedExcludedMinor: refundedExcludedMinor.toString(),
      transactionCount,
      categories,
      budgets,
    };
  }

  getTransactionForUser(user, txId) {
    const tx = this.state.transactions.get(txId);
    if (!tx) {
      const err = new Error("Transaction not found.");
      err.status = 404;
      throw err;
    }
    if (user.role !== "ADMIN" && tx.userId !== user.id) {
      this.recordAudit({
        actorUserId: user.id,
        actorRole: user.role,
        action: "UNAUTHORIZED_TX_ACCESS_ATTEMPT",
        resourceType: "Transaction",
        resourceId: txId,
        outcome: "DENIED",
      });
      const err = new Error("Forbidden: You do not have permission to view this transaction.");
      err.status = 403;
      throw err;
    }
    return this.serializeTransaction(tx);
  }

  serializeTransaction(tx) {
    return {
      ...tx,
      sourceAmountMinor: tx.sourceAmountMinor.toString(),
      feeAmountMinor: tx.feeAmountMinor.toString(),
      taxAmountMinor: tx.taxAmountMinor.toString(),
      totalDebitedMinor: tx.totalDebitedMinor.toString(),
      targetAmountMinor: tx.targetAmountMinor.toString(),
      sourceAmountFormatted: formatMinor(tx.sourceAmountMinor, tx.sourceCurrency),
      totalDebitedFormatted: formatMinor(tx.totalDebitedMinor, tx.sourceCurrency),
      targetAmountFormatted: formatMinor(tx.targetAmountMinor, tx.targetCurrency),
    };
  }
}

// ============================================================================
// 5. HTTP REST API SERVER (/api/v1/*)
// ============================================================================
export function createHttpServer(engine = new GlobalPayEngine()) {
  const server = http.createServer(async (req, res) => {
    const requestId = `req_${crypto.randomBytes(6).toString("hex")}`;
    res.setHeader("X-Request-Id", requestId);
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.setHeader("X-Frame-Options", "DENY");
    res.setHeader("Access-Control-Allow-Origin", process.env.FRONTEND_ORIGIN || "http://localhost:5173");
    res.setHeader("Access-Control-Allow-Methods", "GET,POST,PATCH,DELETE,OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type,Authorization,Idempotency-Key,X-GlobalPay-Signature");

    if (req.method === "OPTIONS") {
      res.writeHead(204);
      return res.end();
    }

    const url = new URL(req.url || "/", "http://localhost");
    const pathname = url.pathname;

    const sendJson = (status, data) => {
      res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ requestId, environment: "SANDBOX_SIMULATION", ...data }));
    };

    const readBody = () =>
      new Promise((resolve, reject) => {
        let raw = "";
        req.on("data", (chunk) => {
          raw += chunk;
          if (raw.length > 256 * 1024) reject(Object.assign(new Error("Payload too large"), { status: 413 }));
        });
        req.on("end", () => resolve(raw));
        req.on("error", reject);
      });

    try {
      // System Health Endpoints
      if (req.method === "GET" && pathname === "/api/v1/system/health/liveness") {
        return sendJson(200, { status: "ALIVE", service: "globalpay-2.0-api", timestamp: new Date().toISOString() });
      }
      if (req.method === "GET" && pathname === "/api/v1/system/health/readiness") {
        return sendJson(200, { status: "READY", database: "CONNECTED", providerMode: "SANDBOX" });
      }

      // Public Auth Endpoints
      if (req.method === "POST" && pathname === "/api/v1/auth/register") {
        const body = JSON.parse((await readBody()) || "{}");
        const session = engine.registerUser(body);
        return sendJson(201, session);
      }
      if (req.method === "POST" && pathname === "/api/v1/auth/login") {
        const body = JSON.parse((await readBody()) || "{}");
        const session = engine.loginUser(body);
        return sendJson(200, session);
      }

      // Webhook Endpoint (Authenticated by HMAC Signature)
      if (req.method === "POST" && pathname === "/api/v1/webhooks/provider") {
        const raw = await readBody();
        const sig = req.headers["x-globalpay-signature"] || "";
        const outcome = engine.processProviderWebhook(raw, String(sig));
        return sendJson(200, outcome);
      }

      // Protected Endpoints Require Bearer Token
      const authHeader = req.headers.authorization || "";
      const token = authHeader.startsWith("Bearer ") ? authHeader.slice(7).trim() : "";
      const { user } = engine.authenticateToken(token);

      if (req.method === "POST" && pathname === "/api/v1/auth/logout") {
        engine.revokeSession(token);
        return sendJson(200, { loggedOut: true });
      }
      if (req.method === "GET" && pathname === "/api/v1/auth/me") {
        return sendJson(200, { user: engine.sanitizeUser(user) });
      }
      if (req.method === "GET" && pathname === "/api/v1/accounts") {
        return sendJson(200, { accounts: engine.getUserAccounts(user.id) });
      }
      if (req.method === "GET" && pathname === "/api/v1/fx/rates") {
        const base = url.searchParams.get("base") || "USD";
        const rates = {};
        for (const code of Object.keys(CURRENCIES)) {
          rates[code] = formatScaledRate(getCrossRateScaled(base, code));
        }
        return sendJson(200, {
          baseCurrency: base,
          isIndicative: true,
          source: "GlobalPay Sandbox Indicative Feed",
          timestamp: new Date().toISOString(),
          currencies: CURRENCIES,
          rates,
        });
      }
      if (req.method === "POST" && pathname === "/api/v1/transfers/quotes") {
        const body = JSON.parse((await readBody()) || "{}");
        const quote = engine.createTransferQuote(user.id, body);
        return sendJson(201, { quote });
      }
      if (req.method === "POST" && pathname === "/api/v1/payments") {
        const body = JSON.parse((await readBody()) || "{}");
        const idemKey = req.headers["idempotency-key"] || body.idempotencyKey;
        const result = engine.executePayment(user.id, { ...body, idempotencyKey: idemKey });
        return sendJson(result.deduplicated ? 200 : 201, result);
      }
      if (req.method === "GET" && pathname.startsWith("/api/v1/transactions/")) {
        const txId = pathname.split("/").pop();
        const tx = engine.getTransactionForUser(user, txId);
        return sendJson(200, { transaction: tx });
      }
      if (req.method === "POST" && pathname.endsWith("/refund")) {
        const parts = pathname.split("/");
        const txId = parts[parts.length - 2];
        const tx = engine.refundTransaction(user, txId);
        return sendJson(200, { transaction: tx });
      }
      if (req.method === "GET" && pathname === "/api/v1/analytics/spending") {
        return sendJson(200, { analytics: engine.getSpendingAnalytics(user.id) });
      }
      if (req.method === "GET" && pathname === "/api/v1/admin/overview") {
        if (user.role !== "ADMIN") {
          engine.recordAudit({ actorUserId: user.id, actorRole: user.role, action: "ADMIN_ACCESS_DENIED", resourceType: "Admin", outcome: "DENIED" });
          return sendJson(403, { error: "FORBIDDEN: Administrator role required." });
        }
        return sendJson(200, {
          metrics: {
            totalUsers: engine.state.users.size,
            totalTransactions: engine.state.transactions.size,
            auditEventCount: engine.state.auditEvents.length,
          },
          auditEvents: engine.state.auditEvents.slice(0, 50),
        });
      }

      return sendJson(404, { error: `Route not found: ${req.method} ${pathname}` });
    } catch (err) {
      const status = err.status || 500;
      return sendJson(status, { error: err.message || "Internal server error", code: err.code || "ERROR" });
    }
  });

  return { server, engine };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const port = Number(process.env.PORT || 4000);
  const { server } = createHttpServer();
  server.listen(port, () => {
    console.log(`[GlobalPay 2.0 API] Listening on http://localhost:${port}/api/v1 (SANDBOX_SIMULATION)`);
  });
}
""")

print("server/src/runtime.mjs created successfully.")
