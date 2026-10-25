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
