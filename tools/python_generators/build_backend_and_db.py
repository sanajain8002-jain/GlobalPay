import os

ROOT = "artifacts/file_generation/ttl=63d/intermediate/globalpay-2.0"

dirs = [
    f"{ROOT}/prisma/migrations/20261025000000_init_globalpay",
    f"{ROOT}/server/src/config",
    f"{ROOT}/server/src/middleware",
    f"{ROOT}/server/src/providers",
    f"{ROOT}/server/src/services",
    f"{ROOT}/server/src/routes",
    f"{ROOT}/server/src/utils",
    f"{ROOT}/client/src/api",
    f"{ROOT}/client/src/context",
    f"{ROOT}/client/src/components",
    f"{ROOT}/client/src/pages",
    f"{ROOT}/tests",
    f"{ROOT}/docs",
]

for d in dirs:
    os.makedirs(d, exist_ok=True)

def write_file(rel_path, content):
    full_path = os.path.join(ROOT, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.lstrip("\n"))

# 1. Root package.json
write_file("package.json", """
{
  "name": "globalpay-2.0",
  "version": "2.0.0",
  "private": true,
  "description": "GlobalPay 2.0 - Full-Stack Global Fintech Application (Money moves. You move.)",
  "workspaces": [
    "client",
    "server"
  ],
  "scripts": {
    "dev": "concurrently \\"npm run dev --workspace=server\\" \\"npm run dev --workspace=client\\"",
    "build": "npm run build --workspace=server && npm run build --workspace=client",
    "db:migrate": "npx prisma migrate deploy",
    "db:seed": "npx tsx prisma/seed.ts",
    "test": "node --test tests/run_tests.mjs",
    "test:unit": "vitest run",
    "test:e2e": "playwright test",
    "lint": "npm run lint --workspaces --if-present"
  },
  "devDependencies": {
    "@playwright/test": "^1.48.0",
    "concurrently": "^9.0.1",
    "prisma": "^5.22.0",
    "supertest": "^7.0.0",
    "tsx": "^4.19.1",
    "typescript": "^5.6.3",
    "vitest": "^2.1.3"
  },
  "engines": {
    "node": ">=18.18.0"
  }
}
""")

# 2. .env.example
write_file(".env.example", """
# ============================================================================
# GLOBALPAY 2.0 - ENVIRONMENT CONFIGURATION TEMPLATE
# WARNING: Never commit real secrets or production credentials to git.
# In production (NODE_ENV=production), missing critical secrets cause immediate
# fail-safe startup abort rather than silent fallback to sandbox mode.
# ============================================================================

# Application & Runtime
NODE_ENV=development
PORT=4000
FRONTEND_ORIGIN=http://localhost:5173
API_PREFIX=/api/v1

# PostgreSQL Database (Prisma / Supabase / Managed PostgreSQL)
DATABASE_URL="postgresql://globalpay_user:CHANGE_ME_LOCAL_ONLY@localhost:5432/globalpay_db?schema=public"
DIRECT_URL="postgresql://globalpay_user:CHANGE_ME_LOCAL_ONLY@localhost:5432/globalpay_db?schema=public"

# Session & Cryptographic Security
SESSION_SECRET="REPLACE_WITH_64_BYTE_HEX_CRYPTOGRAPHIC_SECRET"
JWT_ACCESS_SECRET="REPLACE_WITH_64_BYTE_HEX_ACCESS_SECRET"
CSRF_SECRET="REPLACE_WITH_32_BYTE_HEX_CSRF_SECRET"
COOKIE_DOMAIN="localhost"
COOKIE_SECURE="false"
SESSION_TTL_MINUTES="60"
PASSWORD_RESET_TTL_MINUTES="15"

# Payment Provider Configuration (Sandbox by default in development)
PAYMENT_PROVIDER_MODE="sandbox" # Allowed: "sandbox" | "live"
PAYMENT_PROVIDER_NAME="globalpay_deterministic_sandbox"
STRIPE_OR_WISE_API_KEY="sbx_key_placeholder_do_not_use_in_prod"
PAYMENT_WEBHOOK_SECRET="whsec_placeholder_replace_in_production"

# Transaction & Velocity Limits (Minor Units)
MAX_SINGLE_DOMESTIC_TX_MINOR="1000000"   # e.g., $10,000.00
MAX_DAILY_DOMESTIC_TX_MINOR="2500000"    # e.g., $25,000.00
MAX_SINGLE_INTL_TX_MINOR="5000000"       # e.g., $50,000.00

# Indicative Exchange-Rate Provider
FX_PROVIDER_MODE="sandbox" # Allowed: "sandbox" | "live"
FX_API_BASE_URL="https://openexchangerates.org/api"
FX_API_KEY="fx_placeholder_key"
FX_CACHE_TTL_SECONDS="300"

# GP Copilot AI Assistant
AI_PROVIDER_MODE="rule_based_fallback" # Allowed: "rule_based_fallback" | "live_llm"
AI_API_KEY="ai_placeholder_key"
AI_MODEL_NAME="gemini-2.5-flash"

# Email / Push Notification Provider
NOTIFICATION_PROVIDER_MODE="sandbox_log" # Allowed: "sandbox_log" | "smtp_live"
SMTP_HOST="smtp.example.com"
SMTP_PORT="587"
SMTP_USER="notifications@globalpay.example.com"
SMTP_PASS="smtp_placeholder_secret"

# Observability & Audit Logging
LOG_LEVEL="info"
AUDIT_RETENTION_DAYS="2555" # 7 years statutory financial record retention
""")

# 3. docker-compose.yml
write_file("docker-compose.yml", """
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    container_name: globalpay_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: globalpay_user
      POSTGRES_PASSWORD: globalpay_dev_password
      POSTGRES_DB: globalpay_db
    ports:
      - "5432:5432"
    volumes:
      - globalpay_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U globalpay_user -d globalpay_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: .
      dockerfile: server/Dockerfile
    container_name: globalpay_backend
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      NODE_ENV: development
      PORT: 4000
      FRONTEND_ORIGIN: http://localhost:5173
      DATABASE_URL: postgresql://globalpay_user:globalpay_dev_password@postgres:5432/globalpay_db?schema=public
      SESSION_SECRET: dev_only_session_secret_32_bytes_minimum_length_ok
      JWT_ACCESS_SECRET: dev_only_jwt_secret_32_bytes_minimum_length_ok
      CSRF_SECRET: dev_only_csrf_secret_32_bytes_minimum_length_ok
      PAYMENT_PROVIDER_MODE: sandbox
      PAYMENT_WEBHOOK_SECRET: whsec_dev_sandbox_secret_key
    ports:
      - "4000:4000"

volumes:
  globalpay_pgdata:
""")

# 4. Prisma Schema
write_file("prisma/schema.prisma", """
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider  = "postgresql"
  url       = env("DATABASE_URL")
  directUrl = env("DIRECT_URL")
}

enum UserRole {
  USER
  SUPPORT_ANALYST
  COMPLIANCE_OFFICER
  ADMIN
}

enum AccountStatus {
  ACTIVE
  SUSPENDED
  DEACTIVATED
}

enum TransactionState {
  DRAFT
  REQUIRES_AUTHORIZATION
  PROCESSING
  COMPLETED
  FAILED
  CANCELLED
  REFUND_PENDING
  REFUNDED
  REQUIRES_INVESTIGATION
}

enum TransactionType {
  DOMESTIC_P2P
  QR_PAY
  INTERNATIONAL_TRANSFER
  CURRENCY_CONVERSION
  REQUEST_SETTLEMENT
  EXPENSE_SPLIT_SETTLEMENT
  SANDBOX_TOPUP
}

enum PaymentRequestStatus {
  PENDING
  ACCEPTED_SETTLED
  DECLINED
  CANCELLED
  EXPIRED
}

model User {
  id                   String                 @id @default(uuid())
  email                String                 @unique
  emailVerifiedAt      DateTime?
  passwordHash         String
  role                 UserRole               @default(USER)
  status               AccountStatus          @default(ACTIVE)
  mfaEnabled           Boolean                @default(false)
  mfaSecretHash        String?
  deactivatedAt        DateTime?
  retentionHoldUntil   DateTime?
  createdAt            DateTime               @default(now())
  updatedAt            DateTime               @updatedAt

  profile              UserProfile?
  sessions             Session[]
  passwordResetTokens  PasswordResetToken[]
  accounts             CurrencyAccount[]
  beneficiaries        Beneficiary[]
  quotes               TransferQuote[]
  transactions         Transaction[]          @relation("UserTransactions")
  sentRequests         PaymentRequest[]       @relation("RequesterRelation")
  receivedRequests     PaymentRequest[]       @relation("PayerRelation")
  createdGroups        ExpenseGroup[]
  expenseParticipations ExpenseParticipant[]
  budgets              Budget[]
  notifications        Notification[]
  auditEvents          AuditEvent[]           @relation("ActorAuditEvents")
  idempotencyKeys      IdempotencyKey[]

  @@index([email])
  @@index([status, role])
}

model UserProfile {
  id                      String   @id @default(uuid())
  userId                  String   @unique
  user                    User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  fullName                String
  handle                  String   @unique
  phone                   String?
  countryCode             String   @default("US")
  preferredCurrency       String   @default("USD")
  locale                  String   @default("en-US")
  themePreference         String   @default("dark")
  hideBalancesDefault     Boolean  @default(false)
  notifyEmail             Boolean  @default(true)
  notifyPush              Boolean  @default(true)
  notifySecurityAlerts    Boolean  @default(true)
  notifyBudgetThresholds  Boolean  @default(true)
  notifyMarketing         Boolean  @default(false)
  dashboardConfigJson     String   @default("{}")
  createdAt               DateTime @default(now())
  updatedAt               DateTime @updatedAt
}

model Session {
  id           String    @id @default(uuid())
  userId       String
  user         User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  tokenHash    String    @unique
  csrfToken    String
  ipAddress    String?
  userAgent    String?
  expiresAt    DateTime
  revokedAt    DateTime?
  createdAt    DateTime  @default(now())

  @@index([userId, expiresAt])
}

model PasswordResetToken {
  id          String    @id @default(uuid())
  userId      String
  user        User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  tokenHash   String    @unique
  expiresAt   DateTime
  usedAt      DateTime?
  createdAt   DateTime  @default(now())

  @@index([userId, expiresAt])
}

model CurrencyAccount {
  id                 String        @id @default(uuid())
  userId             String
  user               User          @relation(fields: [userId], references: [id], onDelete: Restrict)
  currency           String        // ISO 4217: USD, EUR, GBP, INR, JPY, SGD, CAD, AUD, AED, CHF, BRL, ZAR
  decimalDigits      Int           @default(2) // e.g., 2 for USD/EUR/INR, 0 for JPY
  balanceMinor       BigInt        @default(0) // Exact integer minor units (never floating point)
  heldBalanceMinor   BigInt        @default(0)
  accountNumberMask  String
  routingOrIbanMask  String
  isSandboxAccount   Boolean       @default(true)
  status             AccountStatus @default(ACTIVE)
  version            Int           @default(1) // Optimistic concurrency lock
  createdAt          DateTime      @default(now())
  updatedAt          DateTime      @updatedAt

  sourceTransactions Transaction[] @relation("SourceAccountTransactions")

  @@unique([userId, currency])
  @@index([userId, status])
}

model Beneficiary {
  id                    String   @id @default(uuid())
  userId                String
  user                  User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  fullName              String
  handleOrUpi           String?
  email                 String?
  countryCode           String
  currency              String
  bankName              String
  accountMask           String
  routingCode           String   // ACH / IBAN / IFSC / SWIFT / Sort Code
  paymentRail           String   // ACH, SEPA, FASTER_PAYMENTS, UPI_SANDBOX, SWIFT, PIX
  verificationStatus    String   @default("VERIFIED_SANDBOX")
  isFavorite            Boolean  @default(false)
  isActive              Boolean  @default(true)
  createdAt             DateTime @default(now())
  updatedAt             DateTime @updatedAt

  quotes                TransferQuote[]
  transactions          Transaction[]

  @@index([userId, isActive])
}

model SupportedCorridor {
  id                    String   @id @default(uuid())
  sourceCountry         String
  destinationCountry    String
  sourceCurrency        String
  targetCurrency        String
  providerName          String
  paymentRail           String
  minAmountMinor        BigInt
  maxAmountMinor        BigInt
  fixedFeeMinor         BigInt
  percentageFeeBps      Int      // Basis points: 45 = 0.45%
  fxMarkupBps           Int      // Basis points: 35 = 0.35%
  taxRateBps            Int      @default(0)
  estimatedDelivery     String
  requiredFieldsJson    String   // JSON array of required beneficiary fields
  eligibilityRulesJson  String   // JSON array of compliance rules
  isEnabled             Boolean  @default(true)
  isSandboxOnly         Boolean  @default(true)
  updatedAt             DateTime @updatedAt

  @@unique([sourceCountry, destinationCountry, sourceCurrency, targetCurrency])
}

model ExchangeRateSnapshot {
  id             String   @id @default(uuid())
  baseCurrency   String
  targetCurrency String
  midMarketRate  Decimal  @db.Decimal(18, 8)
  inverseRate    Decimal  @db.Decimal(18, 8)
  providerSource String
  isIndicative   Boolean  @default(true)
  isCachedFallback Boolean @default(false)
  fetchedAt      DateTime @default(now())
  expiresAt      DateTime

  @@index([baseCurrency, targetCurrency, fetchedAt])
}

model TransferQuote {
  id                    String    @id @default(uuid())
  userId                String
  user                  User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  beneficiaryId         String?
  beneficiary           Beneficiary? @relation(fields: [beneficiaryId], references: [id])
  sourceCountry         String
  destinationCountry    String
  sourceCurrency        String
  targetCurrency        String
  sendAmountMinor       BigInt
  fixedFeeMinor         BigInt
  variableFeeMinor      BigInt
  taxAmountMinor        BigInt
  totalFeeMinor         BigInt
  totalPayableMinor     BigInt
  midMarketRate         Decimal   @db.Decimal(18, 8)
  customerExchangeRate  Decimal   @db.Decimal(18, 8)
  fxMarkupBps           Int
  recipientAmountMinor  BigInt
  estimatedDelivery     String
  quoteSource           String
  isSandbox             Boolean   @default(true)
  expiresAt             DateTime
  acceptedAt            DateTime?
  createdAt             DateTime  @default(now())

  transaction           Transaction?

  @@index([userId, expiresAt])
}

model Transaction {
  id                    String           @id @default(uuid())
  referenceCode         String           @unique // e.g., GP-SBX-20261025-8F92A1
  userId                String
  user                  User             @relation("UserTransactions", fields: [userId], references: [id], onDelete: Restrict)
  sourceAccountId       String
  sourceAccount         CurrencyAccount  @relation("SourceAccountTransactions", fields: [sourceAccountId], references: [id], onDelete: Restrict)
  beneficiaryId         String?
  beneficiary           Beneficiary?     @relation(fields: [beneficiaryId], references: [id])
  quoteId               String?          @unique
  quote                 TransferQuote?   @relation(fields: [quoteId], references: [id])
  type                  TransactionType
  state                 TransactionState @default(DRAFT)
  sourceCurrency        String
  sourceAmountMinor     BigInt
  feeAmountMinor        BigInt           @default(0)
  taxAmountMinor        BigInt           @default(0)
  totalDebitedMinor     BigInt
  targetCurrency        String
  targetAmountMinor     BigInt
  exchangeRateUsed      Decimal          @default(1.00000000) @db.Decimal(18, 8)
  spendingCategory      String           @default("Transfers")
  recipientName         String
  recipientIdentifier   String
  note                  String?
  providerName          String           @default("globalpay_deterministic_sandbox")
  providerReference     String?          @unique
  isSandbox             Boolean          @default(true)
  isRecurring           Boolean          @default(false)
  idempotencyKey        String           @unique
  reversalOfTxId        String?          @unique
  AuthorizedAt          DateTime?
  completedAt           DateTime?
  failedAt              DateTime?
  failureReason         String?
  createdAt             DateTime         @default(now())
  updatedAt             DateTime         @updatedAt

  events                TransactionEvent[]
  webhookEvents         ProviderWebhookEvent[]

  @@index([userId, createdAt])
  @@index([userId, state, type])
  @@index([userId, spendingCategory])
}

model TransactionEvent {
  id            String            @id @default(uuid())
  transactionId String
  transaction   Transaction       @relation(fields: [transactionId], references: [id], onDelete: Cascade)
  fromState     TransactionState?
  toState       TransactionState
  actorType     String            // USER, SYSTEM, PROVIDER_WEBHOOK, ADMIN_RECONCILIATION
  actorId       String?
  reason        String
  metadataJson  String            @default("{}")
  createdAt     DateTime          @default(now())

  @@index([transactionId, createdAt])
}

model PaymentRequest {
  id                  String               @id @default(uuid())
  referenceCode       String               @unique
  requesterId         String
  requester           User                 @relation("RequesterRelation", fields: [requesterId], references: [id])
  payerId             String?
  payer               User?                @relation("PayerRelation", fields: [payerId], references: [id])
  payerHandleOrEmail  String
  currency            String
  amountMinor         BigInt
  note                String?
  category            String               @default("Shared")
  status              PaymentRequestStatus @default(PENDING)
  settledTransactionId String?             @unique
  sharePrivacyToken   String               @unique
  expiresAt           DateTime
  remindedAt          DateTime?
  respondedAt         DateTime?
  createdAt           DateTime             @default(now())
  updatedAt           DateTime             @updatedAt

  @@index([requesterId, status])
  @@index([payerId, status])
}

model ExpenseGroup {
  id              String               @id @default(uuid())
  creatorId       String
  creator         User                 @relation(fields: [creatorId], references: [id])
  name            String
  description     String?
  currency        String               @default("USD")
  totalAmountMinor BigInt              @default(0)
  splitMode       String               @default("EQUAL") // EQUAL | CUSTOM
  category        String               @default("Dining & Group")
  note            String?
  shareReceiptId  String               @unique
  createdAt       DateTime             @default(now())
  updatedAt       DateTime             @updatedAt

  participants    ExpenseParticipant[]

  @@index([creatorId, createdAt])
}

model ExpenseParticipant {
  id                   String       @id @default(uuid())
  groupId              String
  group                ExpenseGroup @relation(fields: [groupId], references: [id], onDelete: Cascade)
  userId               String?
  user                 User?        @relation(fields: [userId], references: [id])
  participantName      String
  participantHandle    String
  shareAmountMinor     BigInt
  status               String       @default("OWED") // OWED | SETTLED
  settledTransactionId String?
  settledAt            DateTime?
  remindedAt           DateTime?

  @@index([groupId, status])
}

model Budget {
  id                String   @id @default(uuid())
  userId            String
  user              User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  category          String
  currency          String   @default("USD")
  monthlyLimitMinor BigInt
  alertThresholdPct Int      @default(80)
  monthKey          String   // e.g., "2026-10"
  createdAt         DateTime @default(now())
  updatedAt         DateTime @updatedAt

  @@unique([userId, category, monthKey])
}

model Notification {
  id          String    @id @default(uuid())
  userId      String
  user        User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  type        String    // PAYMENT_OUTCOME, REQUEST_INCOMING, TRANSFER_STATUS, BUDGET_ALERT, SECURITY_EVENT
  title       String
  message     String
  actionRoute String?
  isRead      Boolean   @default(false)
  dismissedAt DateTime?
  createdAt   DateTime  @default(now())

  @@index([userId, isRead, createdAt])
}

model AuditEvent {
  id            String   @id @default(uuid())
  actorUserId   String?
  actorUser     User?    @relation("ActorAuditEvents", fields: [actorUserId], references: [id])
  actorRole     String
  action        String
  resourceType  String
  resourceId    String?
  ipAddress     String?
  requestId     String
  outcome       String   // SUCCESS, DENIED, FAILURE
  redactedMeta  String   @default("{}") // Never stores raw passwords, OTPs, PINs, or tokens
  createdAt     DateTime @default(now())

  @@index([actorUserId, createdAt])
  @@index([action, createdAt])
}

model ProviderWebhookEvent {
  id                String       @id @default(uuid())
  providerName      String
  externalEventId   String       @unique
  transactionId     String?
  transaction       Transaction? @relation(fields: [transactionId], references: [id])
  eventType         String
  signatureVerified Boolean
  processingStatus  String       // PROCESSED, DUPLICATE_IGNORED, REJECTED_SIGNATURE, OUT_OF_ORDER_QUEUED
  payloadHash       String
  processedAt       DateTime     @default(now())

  @@index([providerName, externalEventId])
}

model IdempotencyKey {
  id             String   @id @default(uuid())
  userId         String
  user           User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  key            String
  endpoint       String
  requestHash    String
  responseStatus Int
  responseBody   String
  expiresAt      DateTime
  createdAt      DateTime @default(now())

  @@unique([userId, key, endpoint])
}
""")

# 5. Prisma SQL Migration
write_file("prisma/migrations/20261025000000_init_globalpay/migration.sql", """
-- GlobalPay 2.0 Initial PostgreSQL Schema Migration
-- Strictly uses BIGINT minor units and DECIMAL(18,8) for exchange rates.

CREATE TYPE "UserRole" AS ENUM ('USER', 'SUPPORT_ANALYST', 'COMPLIANCE_OFFICER', 'ADMIN');
CREATE TYPE "AccountStatus" AS ENUM ('ACTIVE', 'SUSPENDED', 'DEACTIVATED');
CREATE TYPE "TransactionState" AS ENUM (
  'DRAFT',
  'REQUIRES_AUTHORIZATION',
  'PROCESSING',
  'COMPLETED',
  'FAILED',
  'CANCELLED',
  'REFUND_PENDING',
  'REFUNDED',
  'REQUIRES_INVESTIGATION'
);
CREATE TYPE "TransactionType" AS ENUM (
  'DOMESTIC_P2P',
  'QR_PAY',
  'INTERNATIONAL_TRANSFER',
  'CURRENCY_CONVERSION',
  'REQUEST_SETTLEMENT',
  'EXPENSE_SPLIT_SETTLEMENT',
  'SANDBOX_TOPUP'
);
CREATE TYPE "PaymentRequestStatus" AS ENUM (
  'PENDING',
  'ACCEPTED_SETTLED',
  'DECLINED',
  'CANCELLED',
  'EXPIRED'
);

CREATE TABLE "User" (
  "id" TEXT NOT NULL PRIMARY KEY,
  "email" TEXT NOT NULL UNIQUE,
  "emailVerifiedAt" TIMESTAMP(3),
  "passwordHash" TEXT NOT NULL,
  "role" "UserRole" NOT NULL DEFAULT 'USER',
  "status" "AccountStatus" NOT NULL DEFAULT 'ACTIVE',
  "mfaEnabled" BOOLEAN NOT NULL DEFAULT false,
  "mfaSecretHash" TEXT,
  "deactivatedAt" TIMESTAMP(3),
  "retentionHoldUntil" TIMESTAMP(3),
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL
);

CREATE TABLE "UserProfile" (
  "id" TEXT NOT NULL PRIMARY KEY,
  "userId" TEXT NOT NULL UNIQUE REFERENCES "User"("id") ON DELETE CASCADE,
  "fullName" TEXT NOT NULL,
  "handle" TEXT NOT NULL UNIQUE,
  "phone" TEXT,
  "countryCode" TEXT NOT NULL DEFAULT 'US',
  "preferredCurrency" TEXT NOT NULL DEFAULT 'USD',
  "locale" TEXT NOT NULL DEFAULT 'en-US',
  "themePreference" TEXT NOT NULL DEFAULT 'dark',
  "hideBalancesDefault" BOOLEAN NOT NULL DEFAULT false,
  "notifyEmail" BOOLEAN NOT NULL DEFAULT true,
  "notifyPush" BOOLEAN NOT NULL DEFAULT true,
  "notifySecurityAlerts" BOOLEAN NOT NULL DEFAULT true,
  "notifyBudgetThresholds" BOOLEAN NOT NULL DEFAULT true,
  "notifyMarketing" BOOLEAN NOT NULL DEFAULT false,
  "dashboardConfigJson" TEXT NOT NULL DEFAULT '{}',
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL
);

CREATE TABLE "CurrencyAccount" (
  "id" TEXT NOT NULL PRIMARY KEY,
  "userId" TEXT NOT NULL REFERENCES "User"("id") ON DELETE RESTRICT,
  "currency" TEXT NOT NULL,
  "decimalDigits" INTEGER NOT NULL DEFAULT 2,
  "balanceMinor" BIGINT NOT NULL DEFAULT 0 CHECK ("balanceMinor" >= 0),
  "heldBalanceMinor" BIGINT NOT NULL DEFAULT 0 CHECK ("heldBalanceMinor" >= 0),
  "accountNumberMask" TEXT NOT NULL,
  "routingOrIbanMask" TEXT NOT NULL,
  "isSandboxAccount" BOOLEAN NOT NULL DEFAULT true,
  "status" "AccountStatus" NOT NULL DEFAULT 'ACTIVE',
  "version" INTEGER NOT NULL DEFAULT 1,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL,
  UNIQUE("userId", "currency")
);

CREATE TABLE "Transaction" (
  "id" TEXT NOT NULL PRIMARY KEY,
  "referenceCode" TEXT NOT NULL UNIQUE,
  "userId" TEXT NOT NULL REFERENCES "User"("id") ON DELETE RESTRICT,
  "sourceAccountId" TEXT NOT NULL REFERENCES "CurrencyAccount"("id") ON DELETE RESTRICT,
  "beneficiaryId" TEXT,
  "quoteId" TEXT UNIQUE,
  "type" "TransactionType" NOT NULL,
  "state" "TransactionState" NOT NULL DEFAULT 'DRAFT',
  "sourceCurrency" TEXT NOT NULL,
  "sourceAmountMinor" BIGINT NOT NULL CHECK ("sourceAmountMinor" > 0),
  "feeAmountMinor" BIGINT NOT NULL DEFAULT 0,
  "taxAmountMinor" BIGINT NOT NULL DEFAULT 0,
  "totalDebitedMinor" BIGINT NOT NULL CHECK ("totalDebitedMinor" > 0),
  "targetCurrency" TEXT NOT NULL,
  "targetAmountMinor" BIGINT NOT NULL CHECK ("targetAmountMinor" > 0),
  "exchangeRateUsed" DECIMAL(18,8) NOT NULL DEFAULT 1.00000000,
  "spendingCategory" TEXT NOT NULL DEFAULT 'Transfers',
  "recipientName" TEXT NOT NULL,
  "recipientIdentifier" TEXT NOT NULL,
  "note" TEXT,
  "providerName" TEXT NOT NULL DEFAULT 'globalpay_deterministic_sandbox',
  "providerReference" TEXT UNIQUE,
  "isSandbox" BOOLEAN NOT NULL DEFAULT true,
  "isRecurring" BOOLEAN NOT NULL DEFAULT false,
  "idempotencyKey" TEXT NOT NULL UNIQUE,
  "reversalOfTxId" TEXT UNIQUE,
  "AuthorizedAt" TIMESTAMP(3),
  "completedAt" TIMESTAMP(3),
  "failedAt" TIMESTAMP(3),
  "failureReason" TEXT,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL
);

CREATE INDEX "idx_tx_user_created" ON "Transaction"("userId", "createdAt" DESC);
CREATE INDEX "idx_tx_user_state" ON "Transaction"("userId", "state", "type");
""")

# 6. Prisma Seed Script
write_file("prisma/seed.ts", """
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
""")

print("Database and root files generated successfully.")
