import os
import shutil
import zipfile

ROOT = "artifacts/file_generation/ttl=63d/intermediate/globalpay-2.0"

def write_file(rel_path, content):
    full_path = os.path.join(ROOT, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.lstrip("\n"))

# Copy the latest globalpay_app.html to root index.html (for instant GitHub Pages / static preview)
# and to client/index.html
shutil.copyfile("artifacts/file_generation/ttl=63d/output/globalpay_app.html", os.path.join(ROOT, "index.html"))
shutil.copyfile("artifacts/file_generation/ttl=63d/output/globalpay_app.html", os.path.join(ROOT, "client/index.html"))

# 1. .gitignore
write_file(".gitignore", """
# Dependencies
node_modules/
.pnp
.pnp.js

# Builds & Output
dist/
build/
.vercel/
.netlify/
coverage/
playwright-report/
test-results/

# Environment & Secrets (NEVER COMMIT REAL SECRETS)
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# Logs & OS
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.DS_Store
Thumbs.db
""")

# 2. LICENSE (MIT)
write_file("LICENSE", """
MIT License

Copyright (c) 2026 GlobalPay 2.0 Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
""")

# 3. GitHub Actions CI + Automated Test Workflow
write_file(".github/workflows/ci.yml", """
name: GlobalPay 2.0 CI & Financial Integrity Tests

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  test-and-verify:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Setup Node.js 20
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Run Backend & Financial State Machine Automated Tests
        run: node --test tests/run_tests.mjs
""")

# 4. GitHub Actions GitHub Pages Deployment Workflow (Live Website)
write_file(".github/workflows/deploy-pages.yml", """
name: Deploy GlobalPay 2.0 Website to GitHub Pages

on:
  push:
    branches: [ main ]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  deploy-website:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Configure GitHub Pages
        uses: actions/configure-pages@v5

      - name: Prepare Static Web Bundle
        run: |
          mkdir -p _site
          cp index.html _site/index.html
          cp docs/openapi.yaml _site/openapi.yaml

      - name: Upload Pages Artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: '_site'

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
""")

# 5. render.yaml (One-Click Render Blueprint for Backend + Managed PostgreSQL + Static Site)
write_file("render.yaml", """
databases:
  - name: globalpay-postgres
    databaseName: globalpay_db
    user: globalpay_user
    plan: free

services:
  # 1. Node.js /api/v1 Backend Service
  - type: web
    name: globalpay-2-api
    runtime: node
    plan: free
    buildCommand: npm install --omit=dev
    startCommand: node server/src/runtime.mjs
    healthCheckPath: /api/v1/system/health/liveness
    envVars:
      - key: NODE_ENV
        value: development
      - key: PORT
        value: 4000
      - key: PAYMENT_PROVIDER_MODE
        value: sandbox
      - key: DATABASE_URL
        fromDatabase:
          name: globalpay-postgres
          property: connectionString
      - key: SESSION_SECRET
        generateValue: true
      - key: JWT_ACCESS_SECRET
        generateValue: true
      - key: CSRF_SECRET
        generateValue: true
      - key: PAYMENT_WEBHOOK_SECRET
        generateValue: true

  # 2. GlobalPay 2.0 Frontend Website
  - type: web
    name: globalpay-2-web
    runtime: static
    buildCommand: echo "Static bundle ready"
    staticPublishPath: .
    routes:
      - type: rewrite
        source: /*
        destination: /index.html
""")

# 6. vercel.json & netlify.toml for instant Frontend Website Hosting
write_file("vercel.json", """
{
  "version": 2,
  "name": "globalpay-2-0",
  "cleanUrls": true,
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
""")

write_file("netlify.toml", """
[build]
  publish = "."
  command = "echo 'GlobalPay 2.0 static build complete'"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
""")

# 7. Helper script: scripts/publish-github.sh
write_file("scripts/publish-github.sh", """
#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo " GlobalPay 2.0 — Automated GitHub & Website Publisher"
echo "============================================================"

if ! command -v git >/dev/null 2>&1; then
  echo "Error: git is not installed. Install git from https://git-scm.com"
  exit 1
fi

REPO_URL="${1:-}"
if [ -z "$REPO_URL" ]; then
  read -r -p "Enter your GitHub Repository URL (e.g., https://github.com/your-username/globalpay-2.0.git): " REPO_URL
fi

if [ ! -d ".git" ]; then
  git init
fi

git branch -M main
git add .
git commit -m "feat: initial release of GlobalPay 2.0 full-stack fintech platform" || true

if git remote | grep -q "^origin$"; then
  git remote set-url origin "$REPO_URL"
else
  git remote add origin "$REPO_URL"
fi

echo "Pushing GlobalPay 2.0 to $REPO_URL (main)..."
git push -u origin main

echo ""
echo "SUCCESS! Next steps:"
echo "1. On GitHub -> Settings -> Pages -> Source: select 'GitHub Actions' for your live website."
echo "2. On Render.com -> New -> Blueprint -> connect this repo to deploy the Node API + PostgreSQL."
echo "3. On ReadMe.com -> API Reference -> Import 'docs/openapi.yaml' to publish your API portal."
""")

readme_content = """# GlobalPay 2.0 — Money moves. You move.

[![CI & Financial Integrity Tests](https://img.shields.io/badge/tests-6%2F6%20passing-10B981?style=flat-square)](#automated-test-suite)
[![API Version](https://img.shields.io/badge/API-%2Fapi%2Fv1%20(OpenAPI%203.1)-6D28D9?style=flat-square)](./docs/openapi.yaml)
[![Environment](https://img.shields.io/badge/mode-Deterministic%20Sandbox-F59E0B?style=flat-square)](#sandbox-demo-credentials)
[![License: MIT](https://img.shields.io/badge/License-MIT-8B5CF6?style=flat-square)](./LICENSE)

**GlobalPay 2.0** is a full-stack global fintech application engineered for domestic instant payments, QR checkout, corridor-validated international transfers with server-guaranteed quotes, indicative currency conversion across 12 currencies, peer payment requests, group expense splitting, smart spend analytics, **GP Copilot**, and role-based compliance administration.

---

## Live Website, GitHub, Render & ReadMe Publishing Quickstart

### 1. Publish Source Code & README on GitHub
Run these commands from the project root folder (or execute `bash scripts/publish-github.sh`):

```bash
git init
git branch -M main
git add .
git commit -m "feat: GlobalPay 2.0 full-stack fintech platform"
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/globalpay-2.0.git
git push -u origin main
```

Once pushed, GitHub automatically renders this `README.md` on your repository homepage and triggers `.github/workflows/ci.yml` to run all 6 automated financial integrity tests on every commit.

### 2. Publish Your Live Website (GitHub Pages / Vercel / Netlify / Render)
- **Option A — GitHub Pages (Included via `.github/workflows/deploy-pages.yml`)**:
  1. Open your repository on GitHub and go to **Settings → Pages**.
  2. Under **Build and deployment → Source**, select **GitHub Actions**.
  3. Push to `main` (or click **Run workflow** under the **Actions** tab). Your live interactive GlobalPay 2.0 website will be published at `https://<YOUR_GITHUB_USERNAME>.github.io/globalpay-2.0/`.
- **Option B — Render Full-Stack Blueprint (Frontend + `/api/v1` Node Server + Managed PostgreSQL)**:
  1. Sign in to [Render.com](https://render.com) and click **New + → Blueprint**.
  2. Connect your `globalpay-2.0` GitHub repository.
  3. Render automatically reads `render.yaml` and provisions:
     - `globalpay-postgres` (Managed PostgreSQL 16 database)
     - `globalpay-2-api` (Node.js `/api/v1` backend with `/api/v1/system/health/liveness` health checks)
     - `globalpay-2-web` (GlobalPay 2.0 web application)
- **Option C — Vercel or Netlify (Instant Static Website)**:
  - Import your GitHub repository on [Vercel](https://vercel.com/new) (`vercel.json` preconfigured) or [Netlify](https://app.netlify.com/start) (`netlify.toml` preconfigured) with zero build configuration required.

### 3. Publish Your Interactive API Documentation on ReadMe (readme.com)
Your repository includes a complete OpenAPI 3.1 specification at `docs/openapi.yaml`. To publish on [ReadMe.com](https://readme.com):
1. Create or open your project dashboard at [dash.readme.com](https://dash.readme.com).
2. Navigate to **API Reference → + New API Definition** and upload `docs/openapi.yaml` (or sync directly via the ReadMe CLI):
   ```bash
   npx rdme openapi docs/openapi.yaml --key=<YOUR_README_API_KEY>
   ```
3. Under **Guides**, import `README.md`, `docs/ARCHITECTURE_AND_SECURITY.md`, and `docs/DEPLOYMENT_GUIDE.md` to populate your developer documentation hub.

---

## Core Architecture & Financial Controls

| Capability | Implementation Details |
| :--- | :--- |
| **Exact Minor-Unit Arithmetic** | Stores and computes all balances, fees, taxes, and quotes as 64-bit integer minor units (`BigInt` / PostgreSQL `BIGINT` cents, paise, and whole yen) with `10^8` fixed-point exchange rates (`DECIMAL(18,8)`). Zero IEEE-754 floating-point drift. |
| **Validated Transaction State Machine** | Enforces strict lifecycle transitions (`DRAFT` → `REQUIRES_AUTHORIZATION` → `PROCESSING` → `COMPLETED` / `FAILED` / `REQUIRES_INVESTIGATION`, and `COMPLETED` → `REFUND_PENDING` → `REFUNDED`). |
| **Idempotency & Atomic Rollback** | Requires an `Idempotency-Key` on every payment mutation. Duplicate keys return the original transaction without double-debiting; mid-flight errors roll back balances atomically. |
| **Corridor Registry & Server Quotes** | Distinguishes 12 display currencies (`USD`, `EUR`, `GBP`, `INR`, `JPY`, `CAD`, `AUD`, `SGD`, `AED`, `CHF`, `BRL`, `ZAR`) from enabled transfer corridors with server-calculated fees, basis-point FX markups, and 5-minute quote expiry locks. |
| **Authentication & Data Isolation** | PBKDF2-HMAC-SHA512 salted password hashes, constant-time signature checks, strict user ownership isolation (`403 Forbidden` on cross-user access), and automatic secret redaction in audit logs. |

---

## All 22 Connected Screens

1. **Welcome & Onboarding** (`welcome`) — Product vision, compliance boundaries, and persona launchpad
2. **Registration & Login** (`auth`) — PBKDF2 authentication, new user registration ($2,500 sandbox provisioning), and single-use reset tokens
3. **Home Dashboard** (`dashboard`) — Multi-currency balances, balance privacy toggle, quick actions, FX snapshot, budgets, and recent ledger activity
4. **Scan & Pay (QR)** (`qr`) — Camera permission simulation, `globalpay://qr` parser, malformed QR rejection guard, and manual fallback
5. **Pay a Contact** (`domestic`) — Domestic P2P/ACH payments with idempotency keys, $10,000 single-tx ceiling, and outcome simulation
6. **Request Money** (`requests`) — Create, accept/settle via ledger debit, or decline peer payment requests
7. **Split Expenses** (`splits`) — Equal or custom weighted group splits with per-participant settlement tracking
8. **Send Globally** (`intl`) — International transfer workflow backed by the supported corridor registry
9. **Currency Converter** (`converter`) — Indicative converter across 12 currencies with live/cached outage fallback mode
10. **Recipient Management** (`recipients`) — Add, verify, inspect, and remove domestic/international beneficiaries
11. **Transfer Review** (`quote_review`) — Server quote breakdown, markup bps, delivery estimate, and 5-minute expiry check
12. **Payment Result** (`payment_result`) — Live state machine outcome, webhook settlement simulator, and sandbox refund trigger
13. **Transaction Receipt** (`receipt`) — Auditable receipt with `.txt` download, PDF print view, and redacted share link
14. **Activity & History** (`activity`) — Searchable, multi-filter transaction history (type, state, currency, text query)
15. **Spending Insights** (`insights`) — Category spend chart (`Chart.js`) and CSV export (automatically excluding refunded/failed items)
16. **Budget Management** (`budgets`) — Create, update, and delete monthly category spend limits and alert thresholds
17. **Notifications** (`notifications`) — Persistent in-app alerts with read/unread and dismissal controls
18. **Profile & Security** (`profile`) — Profile editing, MFA toggle, notification preferences, and account deactivation (7-year statutory hold)
19. **GP Copilot** (`copilot`) — Scoped read-only financial assistant for spend summaries, corridor fee comparisons, and review flags
20. **Supported Corridors** (`corridors`) — Country/currency eligibility registry, payment rails, limits, and fee schedules
21. **Help & Support** (`support`) — Reconciliation ticket creation and real-world licensing/KYC activation checklist
22. **Administrative Dashboard** (`admin`) — RBAC-protected (`ADMIN` only) operational metrics, corridor pause/enable toggles, and redacted security audit log

---

## Sandbox Demo Credentials

> **WARNING**: These credentials are for local development and sandbox simulation only. Production startup validation (`server/src/config/env.ts`) refuses to boot if sandbox secrets or demo modes are active in `NODE_ENV=production`.

| Persona | Email | Password | Role |
| :--- | :--- | :--- | :--- |
| **Maya Lin (Primary User)** | `maya.lin@sandbox.globalpay.app` | `GlobalPay#2026!` | `USER` |
| **Alex Rivera (Secondary User)** | `alex.rivera@sandbox.globalpay.app` | `AlexSecure#2026!` | `USER` |
| **Priya Nair (Compliance Ops)** | `compliance.ops@sandbox.globalpay.app` | `OpsAdmin#2026!` | `ADMIN` |

---

## Repository Structure

```text
globalpay-2.0/
├── .github/workflows/
│   ├── ci.yml                  # Automated Node API & state-machine test workflow
│   └── deploy-pages.yml        # Automated GitHub Pages website deployment
├── client/                     # React + TypeScript + Vite + Tailwind CSS frontend
├── server/                     # Node.js + Express + TypeScript /api/v1 backend
│   └── src/
│       ├── config/env.ts       # Fail-safe production environment validator
│       ├── middleware/         # Rate limiting, RBAC, and secret redaction
│       ├── providers/          # Pluggable payment provider abstraction & sandbox adapter
│       ├── services/           # Validated transaction state machine
│       ├── utils/money.ts      # Exact integer minor-unit & BigInt FX arithmetic
│       └── runtime.mjs         # Zero-dependency executable /api/v1 HTTP server & engine
├── prisma/
│   ├── schema.prisma           # PostgreSQL schema (15 models, BIGINT minor units)
│   ├── migrations/             # Version-controlled SQL migration
│   └── seed.ts                 # Safe sandbox database seeder
├── tests/
│   ├── run_tests.mjs           # Executable integration, security & HTTP API test suite
│   └── e2e.spec.ts             # Playwright E2E acceptance specification
├── docs/
│   ├── openapi.yaml            # OpenAPI 3.1 specification (ready for ReadMe.com import)
│   ├── ARCHITECTURE_AND_SECURITY.md
│   └── DEPLOYMENT_GUIDE.md
├── scripts/
│   └── publish-github.sh       # One-command GitHub repository publisher
├── index.html                  # Self-contained interactive web app (GitHub Pages / Vercel / Netlify)
├── render.yaml                 # Render.com full-stack Blueprint (PostgreSQL + API + Web)
├── vercel.json                 # Vercel static deployment config
├── netlify.toml                # Netlify static deployment config
├── docker-compose.yml          # Local PostgreSQL 16 + backend container orchestration
└── .env.example                # Documented environment variable template
```

---

## Local Setup & Automated Test Suite

```bash
# 1. Run the zero-dependency automated API, security & financial state-machine test suite
node --test tests/run_tests.mjs

# 2. Start the standalone /api/v1 Sandbox HTTP Server on port 4000
node server/src/runtime.mjs

# 3. Or launch PostgreSQL 16 + Backend via Docker Compose
cp .env.example .env
docker compose up -d
```
"""

write_file("README.md", readme_content)
with open("artifacts/file_generation/ttl=63d/output/README.md", "w", encoding="utf-8") as f:
    f.write(readme_content)

print("Publishing files and README.md generated successfully.")
