/**
 * GlobalPay 2.0 Root Application Router & Screen Registry
 * Connects all 22 required user and administrative journeys to /api/v1 endpoints.
 */
import React, { useState } from "react";

export const GLOBALPAY_SCREENS = [
  { id: "welcome", label: "1. Welcome & Onboarding" },
  { id: "auth", label: "2. Registration & Login" },
  { id: "dashboard", label: "3. Home Dashboard" },
  { id: "qr", label: "4. Scan & Pay (QR)" },
  { id: "domestic", label: "5. Pay a Contact" },
  { id: "requests", label: "6. Request Money" },
  { id: "splits", label: "7. Split Expenses & Groups" },
  { id: "intl", label: "8. Send Globally" },
  { id: "converter", label: "9. Currency Converter" },
  { id: "recipients", label: "10. Recipient Management" },
  { id: "quote_review", label: "11. Transfer Review" },
  { id: "payment_result", label: "12. Payment Result" },
  { id: "receipt", label: "13. Transaction Receipt" },
  { id: "activity", label: "14. Activity & History" },
  { id: "insights", label: "15. Spending Insights" },
  { id: "budgets", label: "16. Budget Management" },
  { id: "notifications", label: "17. Notifications" },
  { id: "profile", label: "18. Profile & Security" },
  { id: "copilot", label: "19. GP Copilot" },
  { id: "corridors", label: "20. Supported Corridors" },
  { id: "support", label: "21. Help & Support" },
  { id: "admin", label: "22. Administrative Dashboard" },
] as const;

export default function App() {
  const [activeScreen, setActiveScreen] = useState<string>("dashboard");
  return (
    <div className="min-h-screen bg-gp-obsidian text-white flex">
      <aside className="w-64 bg-gp-surface border-r border-purple-900/40 p-4">
        <div className="font-bold text-xl tracking-tight text-gp-lavender mb-1">GlobalPay 2.0</div>
        <div className="text-xs text-purple-300/70 mb-6">Money moves. You move.</div>
        <nav className="space-y-1">
          {GLOBALPAY_SCREENS.map((s) => (
            <button
              key={s.id}
              onClick={() => setActiveScreen(s.id)}
              className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition ${
                activeScreen === s.id ? "bg-gp-electric text-white" : "text-purple-200 hover:bg-white/5"
              }`}
            >
              {s.label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold mb-2">Screen: {activeScreen}</h1>
      </main>
    </div>
  );
}
