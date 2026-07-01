#!/usr/bin/env bash
set -euo pipefail

# Sync SMTP credentials between Mailcow and Infisical.
# This script updates a mailbox password in Mailcow and upserts matching SMTP
# secrets in Infisical so application auth/email settings stay consistent.
#
# Usage:
#   bash scripts/sync_smtp_mailcow_infisical.sh
#
# Optional overrides:
#   SMTP_MAILBOX=support@d31337m3.com
#   SMTP_HOST=smtp.d31337m3.com
#   SMTP_PORT=465
#   INFISICAL_ENV_FILE=/etc/d31337m3/client-index.infisical.env
#   MAILCOW_API_BASE=https://127.0.0.1:8444
#   MAILCOW_API_KEY=<rw-api-key>
#   NEW_SMTP_PASSWORD=<set specific password>

SMTP_MAILBOX="${SMTP_MAILBOX:-support@d31337m3.com}"
SMTP_HOST="${SMTP_HOST:-smtp.d31337m3.com}"
SMTP_PORT="${SMTP_PORT:-465}"
SMTP_ENABLED="${SMTP_ENABLED:-true}"
INFISICAL_ENV_FILE="${INFISICAL_ENV_FILE:-/etc/d31337m3/client-index.infisical.env}"
MAILCOW_API_BASE="${MAILCOW_API_BASE:-https://127.0.0.1:8444}"
MAILCOW_CONF="/opt/mailcow-dockerized/mailcow.conf"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

need_cmd curl
need_cmd sudo
need_cmd docker
need_cmd python3
need_cmd openssl

if ! sudo test -f "$INFISICAL_ENV_FILE"; then
  echo "Infisical env file not found: $INFISICAL_ENV_FILE" >&2
  exit 1
fi

if [[ "$SMTP_MAILBOX" != *"@"* ]]; then
  echo "SMTP_MAILBOX must be a full email address" >&2
  exit 1
fi

bootstrap_mailcow_api_key() {
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

mailcow_api_call() {
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

update_mailbox_password() {
  local mailbox="$1"
  local password="$2"
  local payload response

  payload="$(python3 - "$mailbox" "$password" <<'PY'
import json
import sys
mailbox, password = sys.argv[1:]
obj = {
    "attr": {
        "authsource": "mailcow",
        "password": password,
        "password2": password,
        "force_pw_update": "0",
        "active": "1",
    },
    "items": [mailbox],
}
print(json.dumps(obj))
PY
)"

  response="$(mailcow_api_call POST "/api/v1/edit/mailbox" "$payload")"

  MC_JSON="$response" python3 - <<'PY'
import json
import os
raw = os.environ.get("MC_JSON", "").strip()
ok = False
msg = raw
try:
    data = json.loads(raw)
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and str(item.get("type", "")).lower() == "success":
                ok = True
                msg = item.get("msg", "success")
                break
except Exception:
    pass
if ok:
    print("ok")
else:
    print("fail:" + str(msg))
PY
}

read_infisical_env_var() {
  local key="$1"
  sudo awk -F= -v k="$key" '$1==k {print substr($0, index($0, "=")+1)}' "$INFISICAL_ENV_FILE"
}

INFISICAL_SITE_URL="$(read_infisical_env_var INFISICAL_SITE_URL)"
INFISICAL_ENVIRONMENT="$(read_infisical_env_var INFISICAL_ENVIRONMENT)"
INFISICAL_PROJECT_ID="$(read_infisical_env_var INFISICAL_PROJECT_ID)"
INFISICAL_SERVICE_TOKEN="$(read_infisical_env_var INFISICAL_SERVICE_TOKEN)"
INFISICAL_SECRETS_PATH="$(read_infisical_env_var INFISICAL_SECRETS_PATH)"

if [[ -z "$INFISICAL_SITE_URL" || -z "$INFISICAL_ENVIRONMENT" || -z "$INFISICAL_PROJECT_ID" || -z "$INFISICAL_SERVICE_TOKEN" ]]; then
  echo "Infisical configuration is incomplete in $INFISICAL_ENV_FILE" >&2
  exit 1
fi

if [[ -z "${INFISICAL_SECRETS_PATH:-}" ]]; then
  INFISICAL_SECRETS_PATH="/"
fi

if [[ -z "${MAILCOW_API_KEY:-}" ]]; then
  MAILCOW_API_KEY="$(bootstrap_mailcow_api_key)"
fi

# Verify mailbox exists first.
mailboxes_json="$(mailcow_api_call GET "/api/v1/get/mailbox/all")"
if ! MC_JSON="$mailboxes_json" python3 - "$SMTP_MAILBOX" <<'PY'
import json
import os
import sys
email = sys.argv[1].lower()
raw = os.environ.get("MC_JSON", "")
try:
    rows = json.loads(raw)
except Exception:
    raise SystemExit(2)
if not isinstance(rows, list):
    raise SystemExit(3)
for row in rows:
    if isinstance(row, dict) and str(row.get("username", "")).lower() == email:
        raise SystemExit(0)
raise SystemExit(1)
PY
then
  echo "Mailbox not found in Mailcow: $SMTP_MAILBOX" >&2
  exit 1
fi

NEW_SMTP_PASSWORD="${NEW_SMTP_PASSWORD:-$(openssl rand -base64 36 | tr -d '=+/\n' | cut -c1-30)}"

echo "Updating Mailcow mailbox password for $SMTP_MAILBOX..."
mailcow_result="$(update_mailbox_password "$SMTP_MAILBOX" "$NEW_SMTP_PASSWORD")"
if [[ "$mailcow_result" != "ok" ]]; then
  echo "Mailcow password update failed: ${mailcow_result#fail:}" >&2
  exit 1
fi

echo "Upserting SMTP secrets in Infisical (project=$INFISICAL_PROJECT_ID env=$INFISICAL_ENVIRONMENT path=$INFISICAL_SECRETS_PATH)..."

sudo env \
  INFISICAL_SITE_URL="$INFISICAL_SITE_URL" \
  INFISICAL_SERVICE_TOKEN="$INFISICAL_SERVICE_TOKEN" \
  INFISICAL_PROJECT_ID="$INFISICAL_PROJECT_ID" \
  INFISICAL_ENVIRONMENT="$INFISICAL_ENVIRONMENT" \
  INFISICAL_SECRETS_PATH="$INFISICAL_SECRETS_PATH" \
  SMTP_MAILBOX="$SMTP_MAILBOX" \
  SMTP_HOST="$SMTP_HOST" \
  SMTP_PORT="$SMTP_PORT" \
  SMTP_ENABLED="$SMTP_ENABLED" \
  NEW_SMTP_PASSWORD="$NEW_SMTP_PASSWORD" \
  /home/D31337m3/Orm_d31337m3/microservices/.venv/bin/python - <<'PY'
import os
from infisical_sdk import InfisicalSDKClient

host = os.environ["INFISICAL_SITE_URL"]
token = os.environ["INFISICAL_SERVICE_TOKEN"]
project_id = os.environ["INFISICAL_PROJECT_ID"]
env_slug = os.environ["INFISICAL_ENVIRONMENT"]
secret_path = os.environ.get("INFISICAL_SECRETS_PATH", "/") or "/"
mailbox = os.environ["SMTP_MAILBOX"]
password = os.environ["NEW_SMTP_PASSWORD"]

updates = {
    "SMTP_ENABLED": os.environ.get("SMTP_ENABLED", "true"),
    "SMTP_HOST": os.environ["SMTP_HOST"],
    "SMTP_PORT": str(os.environ["SMTP_PORT"]),
    "SMTP_USERNAME": mailbox,
    "SMTP_PASSWORD": password,
    "SMTP_FROM": mailbox,
}

client = InfisicalSDKClient(host=host)
client.auth.token_auth.login(token=token)

for key, value in updates.items():
    try:
        client.secrets.update_secret_by_name(
            current_secret_name=key,
            project_id=project_id,
            environment_slug=env_slug,
            secret_path=secret_path,
            secret_value=value,
        )
        print(f"updated:{key}")
    except Exception:
        client.secrets.create_secret_by_name(
            secret_name=key,
            project_id=project_id,
            environment_slug=env_slug,
            secret_path=secret_path,
            secret_value=value,
        )
        print(f"created:{key}")
PY

echo "Restarting client-index to pick up updated SMTP secrets..."
sudo systemctl restart d31337m3-client-index

echo "Done. SMTP host set to $SMTP_HOST and password synchronized between Mailcow and Infisical."
echo "Mailbox: $SMTP_MAILBOX"
echo "New password length: ${#NEW_SMTP_PASSWORD}"
