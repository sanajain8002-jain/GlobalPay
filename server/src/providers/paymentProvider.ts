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
