#!/usr/bin/env bash
set -euo pipefail

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

git push -u origin main
