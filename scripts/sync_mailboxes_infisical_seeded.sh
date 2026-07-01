#!/usr/bin/env bash
set -euo pipefail

# Seed and sync mailbox passwords to both Mailcow and Infisical.
# Accounts: admin, support, payments, security
#
# Usage:
#   bash scripts/sync_mailboxes_infisical_seeded.sh
#
# Optional overrides:
#   INFISICAL_ENV_FILE=/etc/d31337m3/client-index.infisical.env
#   MAILCOW_API_BASE=https://127.0.0.1:8444
#   MAILBOX_DOMAIN=d31337m3.com
#   MAILBOX_PASSWORD_SEED=<custom-seed>
#   MAILCOW_API_KEY=<rw-api-key>

INFISICAL_ENV_FILE="${INFISICAL_ENV_FILE:-/etc/d31337m3/client-index.infisical.env}"
MAILCOW_API_BASE="${MAILCOW_API_BASE:-https://127.0.0.1:8444}"
MAILCOW_CONF="/opt/mailcow-dockerized/mailcow.conf"
MAILBOX_DOMAIN="${MAILBOX_DOMAIN:-d31337m3.com}"
MAILBOX_PASSWORD_SEED="${MAILBOX_PASSWORD_SEED:-d31337m3-launch-seed-2026-06-30}"
ACCOUNTS=(admin support payments security)

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

if ! sudo test -f "$INFISICAL_ENV_FILE"; then
  echo "Infisical env file not found: $INFISICAL_ENV_FILE" >&2
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

  api_key="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(24))
PY
)"

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

mailbox_exists() {
  local mailbox="$1"
  local all_json
  all_json="$(mailcow_api_call GET "/api/v1/get/mailbox/all")"

  MC_JSON="$all_json" python3 - "$mailbox" <<'PY'
import json
import os
import sys
mb = sys.argv[1].lower()
raw = os.environ.get('MC_JSON', '')
try:
    rows = json.loads(raw)
except Exception:
    print('no')
    raise SystemExit(0)
for row in rows if isinstance(rows, list) else []:
    if isinstance(row, dict) and str(row.get('username', '')).lower() == mb:
        print('yes')
        raise SystemExit(0)
print('no')
PY
}

update_mailbox_password() {
  local mailbox="$1"
  local password="$2"
  local payload response

  payload="$(python3 - "$mailbox" "$password" <<'PY'
import json
import sys
mailbox, password = sys.argv[1:]
print(json.dumps({
    'attr': {
        'authsource': 'mailcow',
        'password': password,
        'password2': password,
        'force_pw_update': '0',
        'active': '1'
    },
    'items': [mailbox]
}))
PY
)"

  response="$(mailcow_api_call POST "/api/v1/edit/mailbox" "$payload")"

  MC_JSON="$response" python3 - <<'PY'
import json
import os
raw = os.environ.get('MC_JSON', '')
ok = False
try:
    data = json.loads(raw)
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and str(item.get('type', '')).lower() == 'success':
                ok = True
                break
except Exception:
    pass
print('ok' if ok else 'fail')
PY
}

read_infisical_env_var() {
  local key="$1"
  sudo awk -F= -v k="$key" '$1==k {print substr($0, index($0, "=")+1)}' "$INFISICAL_ENV_FILE"
}

if [[ -z "${MAILCOW_API_KEY:-}" ]]; then
  MAILCOW_API_KEY="$(bootstrap_mailcow_api_key)"
fi

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

mailcow_api_call GET "/api/v1/get/mailbox/all" >/dev/null

echo "Syncing seeded mailbox passwords to Mailcow and Infisical..."

sudo env \
  INFISICAL_SITE_URL="$INFISICAL_SITE_URL" \
  INFISICAL_SERVICE_TOKEN="$INFISICAL_SERVICE_TOKEN" \
  INFISICAL_PROJECT_ID="$INFISICAL_PROJECT_ID" \
  INFISICAL_ENVIRONMENT="$INFISICAL_ENVIRONMENT" \
  INFISICAL_SECRETS_PATH="$INFISICAL_SECRETS_PATH" \
  MAILBOX_DOMAIN="$MAILBOX_DOMAIN" \
  MAILBOX_PASSWORD_SEED="$MAILBOX_PASSWORD_SEED" \
  /home/D31337m3/Orm_d31337m3/microservices/.venv/bin/python - <<'PY' > /tmp/d31337m3_seeded_mailboxes.json
import hashlib
import json
import os

accounts = ['admin', 'support', 'payments', 'security']
domain = os.environ['MAILBOX_DOMAIN']
seed = os.environ['MAILBOX_PASSWORD_SEED']

rows = []
for account in accounts:
    email = f"{account}@{domain}"
    digest = hashlib.sha256(f"{seed}:{email}".encode()).hexdigest()
    password = f"D3!{digest[:27]}"
    rows.append({'account': account, 'email': email, 'password': password})

print(json.dumps(rows))
PY

created=0
for account in "${ACCOUNTS[@]}"; do
  email="${account}@${MAILBOX_DOMAIN}"

  if [[ "$(mailbox_exists "$email")" != "yes" ]]; then
    echo "Mailbox missing, cannot sync: $email" >&2
    exit 1
  fi

  password="$(python3 - "$account" <<'PY'
import json
import sys
acc = sys.argv[1]
rows = json.load(open('/tmp/d31337m3_seeded_mailboxes.json'))
for r in rows:
    if r['account'] == acc:
        print(r['password'])
        break
PY
)"

  status="$(update_mailbox_password "$email" "$password")"
  if [[ "$status" != "ok" ]]; then
    echo "Failed to update mailbox password for $email" >&2
    exit 1
  fi

  created=$((created + 1))
done

sudo env \
  INFISICAL_SITE_URL="$INFISICAL_SITE_URL" \
  INFISICAL_SERVICE_TOKEN="$INFISICAL_SERVICE_TOKEN" \
  INFISICAL_PROJECT_ID="$INFISICAL_PROJECT_ID" \
  INFISICAL_ENVIRONMENT="$INFISICAL_ENVIRONMENT" \
  INFISICAL_SECRETS_PATH="$INFISICAL_SECRETS_PATH" \
  /home/D31337m3/Orm_d31337m3/microservices/.venv/bin/python - <<'PY'
import json
import os
from infisical_sdk import InfisicalSDKClient

rows = json.load(open('/tmp/d31337m3_seeded_mailboxes.json'))

host = os.environ['INFISICAL_SITE_URL']
token = os.environ['INFISICAL_SERVICE_TOKEN']
project_id = os.environ['INFISICAL_PROJECT_ID']
env_slug = os.environ['INFISICAL_ENVIRONMENT']
secret_path = os.environ.get('INFISICAL_SECRETS_PATH', '/') or '/'

client = InfisicalSDKClient(host=host)
client.auth.token_auth.login(token=token)

for row in rows:
    account = row['account'].upper()
    email = row['email']
    password = row['password']

    pairs = {
        f'MAILBOX_{account}_EMAIL': email,
        f'MAILBOX_{account}_PASSWORD': password,
    }

    for key, value in pairs.items():
        try:
            client.secrets.update_secret_by_name(
                current_secret_name=key,
                project_id=project_id,
                environment_slug=env_slug,
                secret_path=secret_path,
                secret_value=value,
            )
            print(f'updated:{key}')
        except Exception:
            client.secrets.create_secret_by_name(
                secret_name=key,
                project_id=project_id,
                environment_slug=env_slug,
                secret_path=secret_path,
                secret_value=value,
            )
            print(f'created:{key}')
PY

echo "Synchronized $created mailbox accounts."

# keep local seeded file root-only for audit/debug
sudo chown root:root /tmp/d31337m3_seeded_mailboxes.json
sudo chmod 600 /tmp/d31337m3_seeded_mailboxes.json
