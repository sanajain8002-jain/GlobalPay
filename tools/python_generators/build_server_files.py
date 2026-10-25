import os

ROOT = "artifacts/file_generation/ttl=63d/intermediate/globalpay-2.0"

def write_file(rel_path, content):
    full_path = os.path.join(ROOT, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.lstrip("\n"))

# server/package.json
write_file("server/package.json", """
{
  "name": "@globalpay/server",
  "version": "2.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc -p tsconfig.json",
    "start": "node dist/index.js"
  },
  "dependencies": {
    "@prisma/client": "^5.22.0",
    "cookie-parser": "^1.4.7",
    "cors": "^2.8.5",
    "express": "^4.21.1",
    "helmet": "^8.0.0",
    "zod": "^3.23.8"
  },
  "devDependencies": {
    "@types/cookie-parser": "^1.4.7",
    "@types/cors": "^2.8.17",
    "@types/express": "^5.0.0",
    "@types/node": "^22.7.5",
    "typescript": "^5.6.3"
  }
}
""")

# server/tsconfig.json
write_file("server/tsconfig.json", """
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*"]
}
""")

# server/Dockerfile
write_file("server/Dockerfile", """
FROM node:20-alpine
WORKDIR /app
COPY package.json ./
COPY server/package.json ./server/
COPY prisma ./prisma/
RUN npm install --omit=dev
COPY server/src ./server/src
EXPOSE 4000
HEALTHCHECK --interval=15s --timeout=5s --retries=3 CMD wget -qO- http://localhost:4000/api/v1/system/health/liveness || exit 1
CMD ["node", "server/src/runtime.mjs"]
""")

# server/src/config/env.ts
write_file("server/src/config/env.ts", """
/**
 * Environment Configuration & Production Fail-Safe Validation
 * Refuses to boot in production if secrets are missing or set to sandbox defaults.
 */
export interface AppConfig {
  nodeEnv: "development" | "test" | "production";
  port: number;
  frontendOrigin: string;
  apiPrefix: string;
  sessionSecret: string;
  jwtAccessSecret: string;
  csrfSecret: string;
  paymentProviderMode: "sandbox" | "live";
  paymentWebhookSecret: string;
  maxSingleDomesticMinor: bigint;
  maxSingleIntlMinor: bigint;
  fxProviderMode: "sandbox" | "live";
  aiProviderMode: "rule_based_fallback" | "live_llm";
}

export function loadAndValidateConfig(env: NodeJS.ProcessEnv = process.env): AppConfig {
  const nodeEnv = (env.NODE_ENV || "development") as AppConfig["nodeEnv"];
  const isProd = nodeEnv === "production";

  const sessionSecret = env.SESSION_SECRET || (isProd ? "" : "dev_sandbox_session_secret_do_not_use_in_prod_64b");
  const jwtAccessSecret = env.JWT_ACCESS_SECRET || (isProd ? "" : "dev_sandbox_jwt_secret_do_not_use_in_prod_64bytes");
  const csrfSecret = env.CSRF_SECRET || (isProd ? "" : "dev_sandbox_csrf_secret_32bytes");
  const paymentWebhookSecret = env.PAYMENT_WEBHOOK_SECRET || (isProd ? "" : "whsec_sandbox_deterministic_secret");
  const paymentProviderMode = (env.PAYMENT_PROVIDER_MODE || "sandbox") as "sandbox" | "live";

  if (isProd) {
    const missing: string[] = [];
    if (!sessionSecret || sessionSecret.includes("sandbox") || sessionSecret.length < 32) missing.push("SESSION_SECRET");
    if (!jwtAccessSecret || jwtAccessSecret.includes("sandbox") || jwtAccessSecret.length < 32) missing.push("JWT_ACCESS_SECRET");
    if (!csrfSecret || csrfSecret.length < 16) missing.push("CSRF_SECRET");
    if (!env.DATABASE_URL) missing.push("DATABASE_URL");
    if (!paymentWebhookSecret || paymentWebhookSecret.includes("sandbox")) missing.push("PAYMENT_WEBHOOK_SECRET");
    if (paymentProviderMode === "sandbox") {
      throw new Error("CRITICAL SECURITY VIOLATION: Cannot start production server with PAYMENT_PROVIDER_MODE=sandbox.");
    }
    if (missing.length > 0) {
      throw new Error(`CRITICAL STARTUP FAILURE: Missing or insecure production environment variables: ${missing.join(", ")}`);
    }
  }

  return {
    nodeEnv,
    port: Number(env.PORT || 4000),
    frontendOrigin: env.FRONTEND_ORIGIN || "http://localhost:5173",
    apiPrefix: env.API_PREFIX || "/api/v1",
    sessionSecret,
    jwtAccessSecret,
    csrfSecret,
    paymentProviderMode,
    paymentWebhookSecret,
    maxSingleDomesticMinor: BigInt(env.MAX_SINGLE_DOMESTIC_TX_MINOR || "1000000"),
    maxSingleIntlMinor: BigInt(env.MAX_SINGLE_INTL_TX_MINOR || "5000000"),
    fxProviderMode: (env.FX_PROVIDER_MODE || "sandbox") as "sandbox" | "live",
    aiProviderMode: (env.AI_PROVIDER_MODE || "rule_based_fallback") as "rule_based_fallback" | "live_llm",
  };
}
""")

# server/src/utils/money.ts
write_file("server/src/utils/money.ts", """
/**
 * Exact Integer Minor-Unit & Decimal-Safe Financial Arithmetic
 * Never uses IEEE 754 floating-point math for balance mutations or fee computation.
 */
export const CURRENCY_METADATA: Record<string, { code: string; symbol: string; name: string; decimals: number; canHoldAndTransfer: boolean }> = {
  USD: { code: "USD", symbol: "$", name: "US Dollar", decimals: 2, canHoldAndTransfer: true },
  EUR: { code: "EUR", symbol: "€", name: "Euro", decimals: 2, canHoldAndTransfer: true },
  GBP: { code: "GBP", symbol: "£", name: "British Pound", decimals: 2, canHoldAndTransfer: true },
  INR: { code: "INR", symbol: "₹", name: "Indian Rupee", decimals: 2, canHoldAndTransfer: true },
  JPY: { code: "JPY", symbol: "¥", name: "Japanese Yen", decimals: 0, canHoldAndTransfer: true },
  CAD: { code: "CAD", symbol: "C$", name: "Canadian Dollar", decimals: 2, canHoldAndTransfer: true },
  AUD: { code: "AUD", symbol: "A$", name: "Australian Dollar", decimals: 2, canHoldAndTransfer: true },
  SGD: { code: "SGD", symbol: "S$", name: "Singapore Dollar", decimals: 2, canHoldAndTransfer: true },
  AED: { code: "AED", symbol: "د.إ", name: "UAE Dirham", decimals: 2, canHoldAndTransfer: true },
  CHF: { code: "CHF", symbol: "CHF", name: "Swiss Franc", decimals: 2, canHoldAndTransfer: true },
  BRL: { code: "BRL", symbol: "R$", name: "Brazilian Real", decimals: 2, canHoldAndTransfer: false }, // Indicative display & receive-only corridor
  ZAR: { code: "ZAR", symbol: "R", name: "South African Rand", decimals: 2, canHoldAndTransfer: false }, // Indicative display only
};

const RATE_SCALE = 100_000_000n; // 10^8 fixed-point scale for exchange rates

export function parseRateToScaledBigInt(rateStr: string): bigint {
  const [intPart, fracPart = ""] = rateStr.trim().split(".");
  const paddedFrac = (fracPart + "00000000").slice(0, 8);
  return BigInt(intPart) * RATE_SCALE + BigInt(paddedFrac);
}

export function formatMinorToMajor(minor: bigint | number, currency: string): string {
  const meta = CURRENCY_METADATA[currency] || { decimals: 2, symbol: currency + " " };
  const val = typeof minor === "number" ? BigInt(Math.trunc(minor)) : minor;
  const isNeg = val < 0n;
  const absVal = isNeg ? -val : val;
  if (meta.decimals === 0) {
    return `${isNeg ? "-" : ""}${absVal.toString()}`;
  }
  const factor = 10n ** BigInt(meta.decimals);
  const whole = absVal / factor;
  const frac = (absVal % factor).toString().padStart(meta.decimals, "0");
  return `${isNeg ? "-" : ""}${whole.toString()}.${frac}`;
}

export function computeBasisPointsMinor(amountMinor: bigint, bps: number): bigint {
  if (amountMinor <= 0n || bps <= 0) return 0n;
  // Half-up integer rounding: (amount * bps + 5000) / 10000
  return (amountMinor * BigInt(bps) + 5000n) / 10000n;
}

export function convertMinorUsingScaledRate(
  sendAmountMinor: bigint,
  sourceDecimals: number,
  targetDecimals: number,
  rateScaled: bigint
): bigint {
  // Adjust for decimal difference between source (e.g. USD=2) and target (e.g. JPY=0)
  const decDiff = targetDecimals - sourceDecimals;
  let numerator = sendAmountMinor * rateScaled;
  let denominator = RATE_SCALE;
  if (decDiff > 0) {
    numerator *= 10n ** BigInt(decDiff);
  } else if (decDiff < 0) {
    denominator *= 10n ** BigInt(-decDiff);
  }
  return (numerator + denominator / 2n) / denominator;
}
""")

# server/src/services/stateMachine.ts
write_file("server/src/services/stateMachine.ts", """
/**
 * Explicit Validated Transaction Lifecycle State Machine
 * Prevents illegal jumps (e.g., COMPLETED -> FAILED or DRAFT -> COMPLETED).
 */
export type TransactionState =
  | "DRAFT"
  | "REQUIRES_AUTHORIZATION"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED"
  | "REFUND_PENDING"
  | "REFUNDED"
  | "REQUIRES_INVESTIGATION";

const ALLOWED_TRANSITIONS: Record<TransactionState, readonly TransactionState[]> = {
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

export function canTransitionTransaction(fromState: TransactionState, toState: TransactionState): boolean {
  return ALLOWED_TRANSITIONS[fromState]?.includes(toState) ?? false;
}

export function assertValidTransition(fromState: TransactionState, toState: TransactionState): void {
  if (!canTransitionTransaction(fromState, toState)) {
    throw new Error(`INVALID_STATE_TRANSITION: Cannot transition transaction from ${fromState} to ${toState}`);
  }
}
""")

# server/src/providers/paymentProvider.ts
write_file("server/src/providers/paymentProvider.ts", """
/**
 * Payment Provider Integration Abstraction Layer
 * Supports pluggable live providers or the deterministic local sandbox provider.
 */
import crypto from "node:crypto";

export interface ProviderPaymentRequest {
  transactionId: string;
  referenceCode: string;
  amountMinor: bigint;
  currency: string;
  recipientIdentifier: string;
  simulationBehavior?: "AUTO_COMPLETE" | "STAY_PROCESSING" | "FAIL_PROVIDER" | "REQUIRE_INVESTIGATION";
}

export interface ProviderPaymentResult {
  providerName: string;
  providerReference: string;
  resultingState: "PROCESSING" | "COMPLETED" | "FAILED" | "REQUIRES_INVESTIGATION";
  isSandbox: boolean;
  failureReason?: string;
}

export interface PaymentProviderAdapter {
  readonly providerName: string;
  readonly isSandbox: boolean;
  authorizeAndSubmit(req: ProviderPaymentRequest): Promise<ProviderPaymentResult>;
  verifyWebhookSignature(rawBody: string, signatureHeader: string, secret: string): boolean;
  initiateRefund(providerReference: string, amountMinor: bigint): Promise<{ refundReference: string; status: "REFUND_PENDING" | "REFUNDED" }>;
  reconcileTransaction(providerReference: string): Promise<{ resolvedState: "COMPLETED" | "FAILED"; reason: string }>;
}

export class DeterministicSandboxPaymentProvider implements PaymentProviderAdapter {
  public readonly providerName = "globalpay_deterministic_sandbox";
  public readonly isSandbox = true;

  async authorizeAndSubmit(req: ProviderPaymentRequest): Promise<ProviderPaymentResult> {
    const hash = crypto.createHash("sha256").update(`${req.transactionId}:${req.referenceCode}`).digest("hex").slice(0, 12).toUpperCase();
    const providerReference = `SBX-PRV-${hash}`;

    if (req.simulationBehavior === "FAIL_PROVIDER" || req.recipientIdentifier.includes("fail")) {
      return {
        providerName: this.providerName,
        providerReference,
        resultingState: "FAILED",
        isSandbox: true,
        failureReason: "SANDBOX_SIMULATED_DECLINE: Beneficiary bank rejected transfer in sandbox test.",
      };
    }

    if (req.simulationBehavior === "STAY_PROCESSING" || req.recipientIdentifier.includes("slow")) {
      return {
        providerName: this.providerName,
        providerReference,
        resultingState: "PROCESSING",
        isSandbox: true,
      };
    }

    if (req.simulationBehavior === "REQUIRE_INVESTIGATION" || req.recipientIdentifier.includes("timeout")) {
      return {
        providerName: this.providerName,
        providerReference,
        resultingState: "REQUIRES_INVESTIGATION",
        isSandbox: true,
        failureReason: "SANDBOX_GATEWAY_TIMEOUT: Settlement outcome uncertain; queued for reconciliation.",
      };
    }

    return {
      providerName: this.providerName,
      providerReference,
      resultingState: "COMPLETED",
      isSandbox: true,
    };
  }

  verifyWebhookSignature(rawBody: string, signatureHeader: string, secret: string): boolean {
    if (!signatureHeader || !secret) return false;
    const expected = crypto.createHmac("sha256", secret).update(rawBody).digest("hex");
    try {
      return crypto.timingSafeEqual(Buffer.from(signatureHeader), Buffer.from(expected));
    } catch {
      return false;
    }
  }

  async initiateRefund(providerReference: string, _amountMinor: bigint): Promise<{ refundReference: string; status: "REFUND_PENDING" | "REFUNDED" }> {
    const refHash = crypto.createHash("sha256").update(`refund:${providerReference}`).digest("hex").slice(0, 10).toUpperCase();
    return {
      refundReference: `SBX-RFD-${refHash}`,
      status: "REFUNDED",
    };
  }

  async reconcileTransaction(_providerReference: string): Promise<{ resolvedState: "COMPLETED" | "FAILED"; reason: string }> {
    return {
      resolvedState: "COMPLETED",
      reason: "Reconciled against sandbox settlement ledger; clearing confirmed.",
    };
  }
}
""")

print("Server TypeScript modules created.")
