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
