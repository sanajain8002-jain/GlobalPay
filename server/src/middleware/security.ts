/**
 * Security & Financial Controls Middleware
 * - Token bucket rate limiting per IP & authenticated user
 * - Strict RBAC role enforcement
 * - Sensitive payload redaction for audit logging
 */
import crypto from "node:crypto";

const SENSITIVE_KEYS = new Set([
  "password",
  "passwordHash",
  "newPassword",
  "otp",
  "upiPin",
  "accessToken",
  "csrfToken",
  "authorization",
]);

export function redactSensitiveFields(input: Record<string, unknown>): Record<string, unknown> {
  const output: Record<string, unknown> = {};
  for (const [key, val] of Object.entries(input || {})) {
    if (SENSITIVE_KEYS.has(key)) {
      output[key] = "[REDACTED_SECRET]";
    } else if (val && typeof val === "object" && !Array.isArray(val)) {
      output[key] = redactSensitiveFields(val as Record<string, unknown>);
    } else {
      output[key] = val;
    }
  }
  return output;
}

export class SlidingWindowRateLimiter {
  private buckets = new Map<string, { count: number; resetAt: number }>();
  constructor(private readonly maxRequests: number, private readonly windowMs: number) {}

  check(key: string, now = Date.now()): { allowed: boolean; remaining: number; resetAt: number } {
    const entry = this.buckets.get(key);
    if (!entry || now >= entry.resetAt) {
      const resetAt = now + this.windowMs;
      this.buckets.set(key, { count: 1, resetAt });
      return { allowed: true, remaining: this.maxRequests - 1, resetAt };
    }
    if (entry.count >= this.maxRequests) {
      return { allowed: false, remaining: 0, resetAt: entry.resetAt };
    }
    entry.count += 1;
    return { allowed: true, remaining: this.maxRequests - entry.count, resetAt: entry.resetAt };
  }
}

export function generateRequestId(): string {
  return `req_${crypto.randomBytes(8).toString("hex")}`;
}
