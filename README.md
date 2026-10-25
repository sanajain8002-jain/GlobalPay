# GlobalPay 2.0 — Money moves. You move.

[![CI & Financial Integrity Tests](https://img.shields.io/badge/tests-6%2F6%20passing-10B981?style=flat-square)](#local-setup--automated-test-suite)
[![Deploy to Render](https://img.shields.io/badge/Render-Deploy%20Blueprint-46E3B7?style=flat-square)](https://dashboard.render.com/select-repo?type=blueprint)
[![API Version](https://img.shields.io/badge/API-%2Fapi%2Fv1%20(OpenAPI%203.1)-6D28D9?style=flat-square)](./docs/openapi.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-8B5CF6?style=flat-square)](./LICENSE)

**GlobalPay 2.0** is a full-stack global fintech platform for domestic instant payments, QR checkout, corridor-validated international transfers with server-guaranteed quotes, indicative currency conversion across 12 currencies, peer payment requests, group expense splitting, smart spend analytics, **GP Copilot**, and role-based compliance administration.

---

## Step-by-Step: Publish on GitHub & Deploy Live on Render.com

### Step 1 — Push Your Code to GitHub
Unzip `globalpay-2.0-fullstack.zip`, open a terminal in the extracted `globalpay-2.0` folder, and run:

```bash
git init
git branch -M main
git add .
git commit -m "feat: GlobalPay 2.0 full-stack fintech application"
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/globalpay-2.0.git
git push -u origin main
```
*(Or simply run `bash scripts/publish-github.sh` and paste your GitHub repository URL when prompted.)*

### Step 2 — Publish Your Live Full-Stack App & Website on Render.com
This repository includes a pre-configured `render.yaml` Blueprint at the root. To publish both your live website and backend on [Render](https://render.com):
1. Log in to [dashboard.render.com](https://dashboard.render.com).
2. Click **New +** in the top bar and select **Blueprint**.
3. Connect your **`globalpay-2.0`** GitHub repository and click **Apply**.
4. Render automatically reads `render.yaml` and deploys:
   - **`globalpay-2-web` (Live Website)**: Publishes your interactive 23-screen GlobalPay 2.0 web application at `https://globalpay-2-web.onrender.com` (with free automatic SSL/HTTPS).
   - **`globalpay-2-api` (Node.js `/api/v1` Backend)**: Runs `node server/src/runtime.mjs` with live health checks at `/api/v1/system/health/liveness` and auto-generated cryptographic secrets (`SESSION_SECRET`, `JWT_ACCESS_SECRET`, `CSRF_SECRET`, `PAYMENT_WEBHOOK_SECRET`).
   - **`globalpay-postgres` (Managed PostgreSQL 16 Database)**: Provisions your persistent PostgreSQL database.

### Step 3 — Alternative Free Static Website on GitHub Pages
If you also want a live website hosted directly on GitHub Pages:
1. Open your GitHub repository → **Settings → Pages**.
2. Under **Build and deployment → Source**, choose **GitHub Actions**.
3. The included `.github/workflows/deploy-pages.yml` workflow automatically publishes your live site at `https://<YOUR_GITHUB_USERNAME>.github.io/globalpay-2.0/`.

---

## Multi-Language Source Code Included (Edit Any Layer)

All source code used to build and operate GlobalPay 2.0 is included in this repository (see [`docs/CUSTOMIZATION_GUIDE.md`](./docs/CUSTOMIZATION_GUIDE.md) for full details):
- **Frontend Web & UI (`HTML5`, `Tailwind CSS`, `TypeScript`, `React 18`)**: `index.html`, `client/index.html`, `client/src/App.tsx`, `client/src/api/client.ts`
- **Backend REST API (`Node.js`, `TypeScript`, `Express`)**: `server/src/runtime.mjs`, `server/src/index.ts`, `server/src/utils/money.ts`, `server/src/services/stateMachine.ts`, `server/src/providers/paymentProvider.ts`
- **Python Analytics Engine & Project Generators (`Python 3`)**: `services/python_analytics/ledger_engine.py` and all 7 build scripts in `tools/python_generators/` (including `rebuild_project.py`)
- **Java 17 Enterprise Settlement Engine (`Java 17` + `Maven`)**: `services/java_settlement/src/com/globalpay/settlement/GlobalPaySettlementEngine.java` and `services/java_settlement/pom.xml`
- **Database Schema & Migrations (`PostgreSQL SQL` + `Prisma`)**: `prisma/schema.prisma`, `prisma/migrations/20261025000000_init_globalpay/migration.sql`, `prisma/seed.ts`

---

## Sandbox Demo Credentials (Local & Sandbox Testing Only)

| Persona | Email | Password | Role |
| :--- | :--- | :--- | :--- |
| **Maya Lin (Primary User)** | `maya.lin@sandbox.globalpay.app` | `GlobalPay#2026!` | `USER` |
| **Alex Rivera (Secondary User)** | `alex.rivera@sandbox.globalpay.app` | `AlexSecure#2026!` | `USER` |
| **Priya Nair (Compliance Ops)** | `compliance.ops@sandbox.globalpay.app` | `OpsAdmin#2026!` | `ADMIN` |

---

## Local Setup & Automated Test Suite

```bash
# 1. Run the automated Node.js API & Financial State-Machine Test Suite (6/6 tests)
node --test tests/run_tests.mjs

# 2. Run the Python Financial Quote & Analytics Engine
python3 services/python_analytics/ledger_engine.py

# 3. Start the standalone /api/v1 Sandbox HTTP Server on port 4000
node server/src/runtime.mjs
```
