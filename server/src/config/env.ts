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
