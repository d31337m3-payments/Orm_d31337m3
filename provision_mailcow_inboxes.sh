#!/usr/bin/env bash
set -euo pipefail

# Idempotent Mailcow mailbox provisioning for d31337m3.com
# Creates: admin, support, payments, security
#
# Usage:
#   bash provision_mailcow_inboxes.sh
#
# Optional env overrides:
#   MAILCOW_API_BASE=https://127.0.0.1:8444
#   MAILCOW_DOMAIN=d31337m3.com
#   MAILCOW_API_KEY=<existing-rw-api-key>
#   MAILCOW_QUOTA_MB=4096

MAILCOW_API_BASE="${MAILCOW_API_BASE:-https://127.0.0.1:8444}"
MAILCOW_DOMAIN="${MAILCOW_DOMAIN:-d31337m3.com}"
MAILCOW_QUOTA_MB="${MAILCOW_QUOTA_MB:-4096}"
RESULTS_FILE="${RESULTS_FILE:-/home/D31337m3/Orm_d31337m3/.mailboxes_${MAILCOW_DOMAIN}_credentials.csv}"
MAILCOW_CONF="/opt/mailcow-dockerized/mailcow.conf"

MAILBOXES=(admin support payments security)

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

need_cmd curl
need_cmd python3
need_cmd openssl
need_cmd sudo
need_cmd docker

# Bootstrap an API key in Mailcow DB if MAILCOW_API_KEY is not provided.
bootstrap_api_key() {
  local dbroot api_key

  if [[ ! -f "$MAILCOW_CONF" ]]; then
    echo "Mailcow config not found: $MAILCOW_CONF" >&2
    exit 1
  fi

  dbroot="$(sudo grep '^DBROOT=' "$MAILCOW_CONF" | cut -d= -f2-)"
  if [[ -z "$dbroot" ]]; then
    echo "Could not read DBROOT from $MAILCOW_CONF" >&2
    exit 1
  fi

  # Reuse an existing localhost RW key if one exists.
  api_key="$(sudo docker exec mailcowdockerized-mysql-mailcow-1 \
    mysql -N -B -uroot -p"$dbroot" -D mailcow \
    -e "SELECT api_key FROM api WHERE access='rw' AND active=1 AND (allow_from='127.0.0.1' OR allow_from='127.0.0.1/32') LIMIT 1;" 2>/dev/null || true)"

  if [[ -n "$api_key" ]]; then
    echo "$api_key"
    return
  fi

  api_key="$(openssl rand -hex 24)"
  sudo docker exec mailcowdockerized-mysql-mailcow-1 \
    mysql -uroot -p"$dbroot" -D mailcow \
    -e "INSERT INTO api (api_key, allow_from, skip_ip_check, access, active, created) VALUES ('$api_key', '127.0.0.1/32', 1, 'rw', 1, NOW());" >/dev/null

  echo "$api_key"
}

api_call() {
  local method="$1"
  local endpoint="$2"
  local body="${3:-}"

  if [[ -n "$body" ]]; then
    curl -ksS -X "$method" \
      -H "X-API-Key: $MAILCOW_API_KEY" \
      -H "Content-Type: application/json" \
      --data "$body" \
      "$MAILCOW_API_BASE$endpoint"
  else
    curl -ksS -X "$method" \
      -H "X-API-Key: $MAILCOW_API_KEY" \
      "$MAILCOW_API_BASE$endpoint"
  fi
}

mailbox_exists() {
  local email="$1"
  local all_json

  all_json="$(api_call GET "/api/v1/get/mailbox/all")"

  MC_JSON="$all_json" python3 - "$email" <<'PY'
import json
import os
import sys
email = sys.argv[1].lower()
raw = os.environ.get("MC_JSON", "").strip()
if not raw:
    print("no")
    raise SystemExit(0)
try:
    data = json.loads(raw)
except Exception:
    print("no")
    raise SystemExit(0)
found = False
if isinstance(data, list):
    for row in data:
        if isinstance(row, dict):
            u = str(row.get("username", "")).lower()
            if u == email:
                found = True
                break
print("yes" if found else "no")
PY
}

create_mailbox() {
  local local_part="$1"
  local email="$2"
  local password="$3"
  local display_name="$4"

  local payload response
  payload="$(python3 - "$local_part" "$display_name" "$password" "$MAILCOW_DOMAIN" "$MAILCOW_QUOTA_MB" <<'PY'
import json
import sys
local_part, display_name, password, domain, quota = sys.argv[1:]
obj = {
    "active": "1",
    "domain": domain,
    "local_part": local_part,
    "name": display_name,
    "authsource": "mailcow",
    "password": password,
    "password2": password,
    "quota": str(quota),
    "force_pw_update": "0",
    "tls_enforce_in": "0",
    "tls_enforce_out": "0",
}
print(json.dumps(obj))
PY
)"

  response="$(api_call POST "/api/v1/add/mailbox" "$payload")"

  MC_JSON="$response" python3 - "$email" <<'PY'
import json
import os
import sys
email = sys.argv[1].lower()
raw = os.environ.get("MC_JSON", "").strip()
ok = False
msg = raw
try:
    data = json.loads(raw)
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            t = str(item.get("type", "")).lower()
            m = item.get("msg", "")
            if t == "success":
                ok = True
                msg = m
                break
except Exception:
    pass
if ok:
    print("ok")
else:
    print("fail:" + str(msg))
PY
}

label_for_mailbox() {
  local lp="$1"
  case "$lp" in
    admin) echo "Admin" ;;
    support) echo "Support" ;;
    payments) echo "Payments" ;;
    security) echo "Security" ;;
    *) echo "$lp" ;;
  esac
}

if [[ -z "${MAILCOW_API_KEY:-}" ]]; then
  echo "No MAILCOW_API_KEY provided; bootstrapping localhost RW API key..."
  MAILCOW_API_KEY="$(bootstrap_api_key)"
fi

# Basic API auth check
if ! api_call GET "/api/v1/get/mailbox/all" >/dev/null 2>&1; then
  echo "Mailcow API auth check failed. Verify API key and Mailcow endpoint." >&2
  exit 1
fi

umask 077
: > "$RESULTS_FILE"
echo "email,password,status" >> "$RESULTS_FILE"

created=0
existing=0
failed=0

for lp in "${MAILBOXES[@]}"; do
  email="${lp}@${MAILCOW_DOMAIN}"
  exists="$(mailbox_exists "$email")"

  if [[ "$exists" == "yes" ]]; then
    echo "[skip] $email already exists"
    echo "$email,,existing" >> "$RESULTS_FILE"
    existing=$((existing + 1))
    continue
  fi

  pw="$(openssl rand -base64 33 | tr -d '=+/\n' | cut -c1-28)"
  display_name="$(label_for_mailbox "$lp")"

  result="$(create_mailbox "$lp" "$email" "$pw" "$display_name")"
  if [[ "$result" == "ok" ]]; then
    echo "[created] $email"
    echo "$email,$pw,created" >> "$RESULTS_FILE"
    created=$((created + 1))
  else
    echo "[failed] $email -> ${result#fail:}"
    echo "$email,,failed" >> "$RESULTS_FILE"
    failed=$((failed + 1))
  fi
done

echo
echo "Done. created=$created existing=$existing failed=$failed"
echo "Credentials file: $RESULTS_FILE"
chmod 600 "$RESULTS_FILE"

if [[ "$failed" -gt 0 ]]; then
  exit 2
fi
