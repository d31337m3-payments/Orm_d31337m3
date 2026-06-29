#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Stopping microservices managed by scripts..."
"${ROOT_DIR}/microservices/stop_all.sh" || true

echo "Stopping systemd microservices if installed..."
for unit in d31337m3-orchestrator.service d31337m3-watchdog.service d31337m3-payments.service d31337m3-data-handling.service d31337m3-client-index.service d31337m3-auditor.service; do
  sudo systemctl stop "$unit" 2>/dev/null || true
done

echo "Ensuring Nginx API upstream targets orchestrator (8006)..."
for site in /etc/nginx/sites-available/d31337m3.com /etc/nginx/sites-available/d31337m3; do
  if [[ -f "$site" ]]; then
    sudo sed -E -i 's|proxy_pass http://127.0.0.1:[0-9]+/api/;|proxy_pass http://127.0.0.1:8006/api/;|g' "$site"
  fi
done
sudo nginx -t
sudo systemctl reload nginx

echo "Restarting microservices stack..."
"${ROOT_DIR}/microservices/start_all.sh" || true
"${ROOT_DIR}/microservices/health_check.sh" || true

echo "Rollback commands completed for microservices-only topology. Validate with:"
echo "curl -I -H 'Host: d31337m3.com' http://127.0.0.1/"
