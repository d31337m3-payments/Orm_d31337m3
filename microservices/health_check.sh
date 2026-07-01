#!/usr/bin/env bash
set -euo pipefail

checks=(
  "auditor:8005"
  "client_index:8002"
  "data_handling:8004"
  "payments:8003"
  "support_hub:8008"
  "workforce_ops:8009"
  "watchdog:8007"
  "orchestrator:8006"
)

failed=0
for item in "${checks[@]}"; do
  name="${item%%:*}"
  port="${item##*:}"
  if curl -fsS "http://127.0.0.1:${port}/health" >/dev/null; then
    echo "OK   ${name} :${port}"
  else
    echo "FAIL ${name} :${port}"
    failed=1
  fi
done

exit "${failed}"
