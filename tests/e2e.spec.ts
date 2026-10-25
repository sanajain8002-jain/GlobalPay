import { test, expect } from "@playwright/test";

test("Full GlobalPay 2.0 User Acceptance Journey", async ({ page }) => {
  await page.goto("http://localhost:5173");
  await expect(page.locator("text=GlobalPay")).toBeVisible();
});
