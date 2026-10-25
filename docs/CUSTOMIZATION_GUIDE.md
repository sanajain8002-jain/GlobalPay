# GlobalPay 2.0 — Multi-Language Source Code & Customization Guide

All source files across **HTML/CSS/JS**, **TypeScript/React**, **Node.js**, **Python**, **Java 17**, and **PostgreSQL/Prisma** are included in this archive so you can modify any layer and re-deploy at any time.

## 1. Where to Edit Each Language

| Language / Stack | File Path(s) in ZIP | What You Can Change Here |
| :--- | :--- | :--- |
| **Interactive Web App (HTML5 + Tailwind CSS + JS)** | `index.html` and `client/index.html` | Edit colors, brand copy, seeded demo accounts, currencies, fees, or any of the 23 interactive screens. Opens directly in any browser or deploys to Render/GitHub Pages/Vercel. |
| **React 18 + TypeScript Frontend** | `client/src/App.tsx`, `client/src/api/client.ts`, `client/tailwind.config.js` | Component hierarchy, React Router / TanStack Query integration, and Tailwind theme tokens (`gp.electric`, `gp.violet`, `gp.lavender`). |
| **Node.js + Express / HTTP Backend (`/api/v1`)** | `server/src/runtime.mjs`, `server/src/index.ts`, `server/src/config/env.ts`, `server/src/utils/money.ts`, `server/src/services/stateMachine.ts`, `server/src/providers/paymentProvider.ts` | REST API routes, PBKDF2 authentication, session TTL, rate limits, corridor fee formulas, and payment provider webhook handling. |
| **Python 3 Analytics & Project Generators** | `services/python_analytics/ledger_engine.py`, `tools/python_generators/*.py` | Run `python3 services/python_analytics/ledger_engine.py` for standalone Python decimal-safe quote/analytics calculation, or edit `tools/python_generators/*.py` and run `python3 tools/python_generators/rebuild_project.py` to regenerate the project scaffold. |
| **Java 17 Settlement & State Machine Engine** | `services/java_settlement/src/com/globalpay/settlement/GlobalPaySettlementEngine.java` and `services/java_settlement/pom.xml` | Enterprise Java implementation of the validated transaction state machine, basis-point fee calculator, `BigDecimal` currency conversion, and HMAC-SHA256 webhook verification. |
| **PostgreSQL & Prisma ORM** | `prisma/schema.prisma`, `prisma/migrations/20261025000000_init_globalpay/migration.sql`, `prisma/seed.ts` | Database tables, indexes, `BIGINT` minor-unit balance constraints, and demo seed records. |
| **Deployment & CI/CD (YAML / Docker / Shell)** | `render.yaml`, `docker-compose.yml`, `.github/workflows/ci.yml`, `.github/workflows/deploy-pages.yml`, `scripts/publish-github.sh` | One-click Render.com Blueprint, Docker PostgreSQL setup, and GitHub Actions pipelines. |

---

## 2. How to Test Your Changes Locally

```bash
# 1. Test the Node.js /api/v1 Backend & Financial State Machine (6 automated tests)
node --test tests/run_tests.mjs

# 2. Test the Python Financial Analytics & Quote Engine
python3 services/python_analytics/ledger_engine.py

# 3. Compile & Run the Java 17 Settlement Engine (if JDK javac is installed)
javac services/java_settlement/src/com/globalpay/settlement/GlobalPaySettlementEngine.java
java -cp services/java_settlement/src com.globalpay.settlement.GlobalPaySettlementEngine
```
