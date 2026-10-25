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
