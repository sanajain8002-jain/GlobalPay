# GlobalPay 2.0 — Complete Setup, Operations & Deployment Guide

## 1. Local Setup & Development
1. **Install Dependencies**:
   ```bash
   npm install
   ```
2. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   ```
3. **Start Local PostgreSQL via Docker**:
   ```bash
   docker compose up -d postgres
   ```
4. **Apply Database Migrations**:
   ```bash
   npm run db:migrate
   ```
5. **Seed Clearly Labelled Sandbox Data**:
   ```bash
   npm run db:seed
   ```
6. **Start Backend & Frontend Development Servers**:
   ```bash
   npm run dev
   ```
7. **Run Automated Tests**:
   ```bash
   npm test
   ```
8. **Build Production Assets**:
   ```bash
   npm run build
   ```

## 2. Production Deployment, Health Checks & Rollback
- **Liveness Probe**: `GET /api/v1/system/health/liveness`
- **Readiness Probe**: `GET /api/v1/system/health/readiness`
- **Database Backups & Recovery**: Enable automated daily snapshots and Point-In-Time Recovery (PITR) on managed PostgreSQL (Supabase / AWS RDS / Cloud SQL). Never run `prisma migrate reset` in production.
