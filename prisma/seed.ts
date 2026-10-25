/**
 * GlobalPay 2.0 Safe Sandbox Database Seeder
 * WARNING: For local development and sandbox testing ONLY.
 * Refuses to execute if NODE_ENV === 'production'.
 */
import crypto from "node:crypto";

export function hashPasswordPBKDF2(password: string, salt?: string): string {
  const actualSalt = salt || crypto.randomBytes(16).toString("hex");
  const derived = crypto.pbkdf2Sync(password, actualSalt, 100000, 64, "sha512").toString("hex");
  return `pbkdf2_sha512$100000$${actualSalt}$${derived}`;
}

export const SEED_DATA = {
  warning: "SANDBOX DEMO ACCOUNTS ONLY - DO NOT USE IN PRODUCTION",
  users: [
    {
      id: "usr_demo_maya_01",
      email: "maya.lin@sandbox.globalpay.app",
      passwordPlainForDocsOnly: "GlobalPay#2026!",
      role: "USER",
      fullName: "Maya Lin",
      handle: "@mayalin",
      countryCode: "US",
      preferredCurrency: "USD",
    },
    {
      id: "usr_demo_alex_02",
      email: "alex.rivera@sandbox.globalpay.app",
      passwordPlainForDocsOnly: "AlexSecure#2026!",
      role: "USER",
      fullName: "Alex Rivera",
      handle: "@alexrivera",
      countryCode: "GB",
      preferredCurrency: "GBP",
    },
    {
      id: "usr_demo_admin_03",
      email: "compliance.ops@sandbox.globalpay.app",
      passwordPlainForDocsOnly: "OpsAdmin#2026!",
      role: "ADMIN",
      fullName: "Priya Nair (Compliance Ops)",
      handle: "@priya_ops",
      countryCode: "US",
      preferredCurrency: "USD",
    }
  ]
};

if (process.env.NODE_ENV === "production") {
  console.error("FATAL: Refusing to seed demo credentials in production environment.");
  process.exit(1);
}

console.log("[GlobalPay Seed] Prepared deterministic sandbox dataset:", SEED_DATA.users.map(u => u.email));
