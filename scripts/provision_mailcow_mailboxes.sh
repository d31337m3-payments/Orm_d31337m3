#!/usr/bin/env bash
set -euo pipefail

MAILCOW_DIR="${MAILCOW_DIR:-/opt/mailcow-dockerized}"
MAILCOW_CONF="${MAILCOW_CONF:-${MAILCOW_DIR}/mailcow.conf}"
MYSQL_CONTAINER="${MYSQL_CONTAINER:-mailcowdockerized-mysql-mailcow-1}"
MAILCOW_API_BASE="${MAILCOW_API_BASE:-https://127.0.0.1:8444}"
DOMAIN="${DOMAIN:-d31337m3.com}"
MAILBOXES_CSV="${MAILBOXES:-admin,support,payments,security}"
DEFAULT_QUOTA_MB="${DEFAULT_QUOTA_MB:-3072}"
CREDS_FILE="${CREDS_FILE:-/home/D31337m3/Orm_d31337m3/.mailboxes_created.env}"
DRY_RUN="${DRY_RUN:-0}"

log() { printf "[%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
fail() { printf "ERROR: %s\n" "$*" >&2; exit 1; }

[[ -f "$MAILCOW_CONF" ]] || fail "Missing mailcow config at $MAILCOW_CONF"
command -v curl >/dev/null 2>&1 || fail "curl is required"
command -v python3 >/dev/null 2>&1 || fail "python3 is required"
command -v openssl >/dev/null 2>&1 || fail "openssl is required"

DBROOT="$(sudo grep '^DBROOT=' "$MAILCOW_CONF" | cut -d= -f2-)"
[[ -n "$DBROOT" ]] || fail "Could not read DBROOT from $MAILCOW_CONF"

sql() {
  local query="$1"
  sudo docker exec "$MYSQL_CONTAINER" mysql -N -B -uroot -p"$DBROOT" -D mailcow -e "$query"
}

json_success() {
  python3 - "$1" <<'PY'
import json, sys
raw = sys.argv[1]
try:
    data = json.loads(raw)
except Exception:
    print("invalid-json")
    sys.exit(1)

obj = data[0] if isinstance(data, list) and data else data
msg = ""
if isinstance(obj, dict):
    t = obj.get("type", "")
    m = obj.get("msg", "")
    if isinstance(m, list):
        msg = " ".join(str(x) for x in m)
    else:
        msg = str(m)
    if t == "success":
        print(msg)
        sys.exit(0)

print(msg or "request failed")
sys.exit(1)
PY
}

create_api_key_if_needed() {
  if [[ -n "${MAILCOW_API_KEY:-}" ]]; then
    echo "$MAILCOW_API_KEY"
    return 0
  fi

  local existing
  existing="$(sql "SELECT api_key FROM api WHERE active = 1 AND access = 'rw' ORDER BY created DESC LIMIT 1;" || true)"
  if [[ -n "$existing" ]]; then
    echo "$existing"
    return 0
  fi

  local key
  key="$(openssl rand -hex 32)"
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY_RUN=1: would create localhost-scoped rw API key"
    echo "$key"
    return 0
  fi

  sql "INSERT INTO api (api_key, allow_from, skip_ip_check, access, active) VALUES ('$key', '127.0.0.1/32,::1/128', 1, 'rw', 1);"
  log "Created Mailcow API key scoped to localhost"
  echo "$key"
}

call_api_add_mailbox() {
  local payload="$1"
  curl -skS \
    -H "X-API-Key: ${API_KEY}" \
    -H 'Content-Type: application/json' \
    -X POST "${MAILCOW_API_BASE}/api/v1/add/mailbox" \
    --data "$payload"
}

domain_exists="$(sql "SELECT COUNT(*) FROM domain WHERE domain='${DOMAIN}';" || true)"
[[ "$domain_exists" == "1" ]] || fail "Domain ${DOMAIN} not found in Mailcow. Create the domain first."

API_KEY="$(create_api_key_if_needed)"
[[ -n "$API_KEY" ]] || fail "Could not determine Mailcow API key"

if [[ "$DRY_RUN" != "1" ]]; then
  umask 077
  : > "$CREDS_FILE"
  {
    echo "# Generated $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo "# Mailboxes provisioned for ${DOMAIN}"
  } >> "$CREDS_FILE"
fi

IFS=',' read -r -a MAILBOXES <<< "$MAILBOXES_CSV"
created=0
skipped=0

for raw in "${MAILBOXES[@]}"; do
  local_part="$(echo "$raw" | tr '[:upper:]' '[:lower:]' | xargs)"
  [[ -n "$local_part" ]] || continue
  username="${local_part}@${DOMAIN}"

  exists="$(sql "SELECT COUNT(*) FROM mailbox WHERE username='${username}';" || true)"
  if [[ "$exists" != "0" ]]; then
    log "SKIP ${username}: mailbox already exists"
    skipped=$((skipped + 1))
    continue
  fi

  upper_name="$(echo "$local_part" | tr '[:lower:]' '[:upper:]')"
  pass_var="MAILBOX_PASSWORD_${upper_name}"
  password="${!pass_var:-}"
  if [[ -z "$password" ]]; then
    password="$(openssl rand -base64 24 | tr -d '=+/\n' | cut -c1-24)"
  fi

  display_name="$(echo "$local_part" | awk '{print toupper(substr($0,1,1)) substr($0,2)}')"
  payload="$(cat <<JSON
{"active":true,"domain":"${DOMAIN}","local_part":"${local_part}","name":"${display_name}","authsource":"mailcow","password":"${password}","password2":"${password}","quota":"${DEFAULT_QUOTA_MB}","force_pw_update":false,"tls_enforce_in":true,"tls_enforce_out":true}
JSON
)"

  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY_RUN=1: would create ${username}"
    created=$((created + 1))
    continue
  fi

  response="$(call_api_add_mailbox "$payload")"
  if msg="$(json_success "$response")"; then
    log "OK ${username}: ${msg}"
    {
      echo "${upper_name}_MAILBOX=${username}"
      echo "${upper_name}_PASSWORD=${password}"
      echo
    } >> "$CREDS_FILE"
    created=$((created + 1))
  else
    fail "Failed creating ${username}. API response: ${response}"
  fi
done

if [[ "$DRY_RUN" != "1" ]]; then
  chmod 600 "$CREDS_FILE"
fi

log "Completed. created=${created}, skipped=${skipped}, domain=${DOMAIN}"
if [[ "$DRY_RUN" != "1" ]]; then
  log "Credentials written to ${CREDS_FILE} (chmod 600)"
fi
