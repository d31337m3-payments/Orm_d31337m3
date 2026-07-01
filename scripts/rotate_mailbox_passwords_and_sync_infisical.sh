#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/D31337m3/Orm_d31337m3"
MAILCOW_CONF="/opt/mailcow-dockerized/mailcow.conf"
MAILCOW_API_BASE="${MAILCOW_API_BASE:-https://127.0.0.1:8444}"
MAIL_DOMAIN="${MAIL_DOMAIN:-d31337m3.com}"
PYTHON_BIN="${ROOT_DIR}/microservices/.venv/bin/python"

RUNTIME_ENV_PRIMARY="${ROOT_DIR}/.env.infisical.runtime.generated"
RUNTIME_ENV_FALLBACK="${ROOT_DIR}/.env.infisical.runtime"

if [[ -f "$RUNTIME_ENV_PRIMARY" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$RUNTIME_ENV_PRIMARY"
  set +a
elif [[ -f "$RUNTIME_ENV_FALLBACK" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$RUNTIME_ENV_FALLBACK"
  set +a
else
  echo "No Infisical runtime env file found" >&2
  exit 1
fi

if [[ -z "${INFISICAL_SERVICE_TOKEN:-}" || -z "${INFISICAL_PROJECT_ID:-}" || -z "${INFISICAL_ENVIRONMENT:-}" ]]; then
  echo "Missing required INFISICAL_* runtime values" >&2
  exit 1
fi

if [[ ! -f "$MAILCOW_CONF" ]]; then
  echo "Missing Mailcow config at $MAILCOW_CONF" >&2
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python venv not found at $PYTHON_BIN" >&2
  exit 1
fi

DBROOT="$(sudo grep '^DBROOT=' "$MAILCOW_CONF" | cut -d= -f2-)"
if [[ -z "$DBROOT" ]]; then
  echo "Could not read DBROOT from $MAILCOW_CONF" >&2
  exit 1
fi

MAILCOW_API_KEY="$(sudo docker exec mailcowdockerized-mysql-mailcow-1 mysql -N -B -uroot -p"$DBROOT" -D mailcow -e "SELECT api_key FROM api WHERE access='rw' AND active=1 LIMIT 1;" 2>/dev/null || true)"
if [[ -z "$MAILCOW_API_KEY" ]]; then
  MAILCOW_API_KEY="$(openssl rand -hex 24)"
  sudo docker exec mailcowdockerized-mysql-mailcow-1 mysql -uroot -p"$DBROOT" -D mailcow -e "INSERT INTO api (api_key, allow_from, skip_ip_check, access, active, created) VALUES ('$MAILCOW_API_KEY', '127.0.0.1/32', 1, 'rw', 1, NOW());" >/dev/null
fi

INFISICAL_SITE_URL="${INFISICAL_SITE_URL:-https://app.infisical.com}" \
INFISICAL_SERVICE_TOKEN="$INFISICAL_SERVICE_TOKEN" \
INFISICAL_PROJECT_ID="$INFISICAL_PROJECT_ID" \
INFISICAL_ENVIRONMENT="$INFISICAL_ENVIRONMENT" \
INFISICAL_SECRETS_PATH="${INFISICAL_SECRETS_PATH:-/}" \
MAILCOW_API_BASE="$MAILCOW_API_BASE" \
MAILCOW_API_KEY="$MAILCOW_API_KEY" \
MAIL_DOMAIN="$MAIL_DOMAIN" \
"$PYTHON_BIN" - <<'PY'
import json
import os
import secrets
import ssl
import string
import sys
import urllib.error
import urllib.request

from infisical_client import ClientSettings, InfisicalClient, schemas

mailcow_api_base = os.environ["MAILCOW_API_BASE"].rstrip("/")
mailcow_api_key = os.environ["MAILCOW_API_KEY"]
mail_domain = os.environ["MAIL_DOMAIN"]

site_url = os.environ.get("INFISICAL_SITE_URL", "https://app.infisical.com")
project_id = os.environ["INFISICAL_PROJECT_ID"]
environment = os.environ.get("INFISICAL_ENVIRONMENT", "prod")
path = os.environ.get("INFISICAL_SECRETS_PATH", "/")
token = os.environ["INFISICAL_SERVICE_TOKEN"]

mailboxes = ["support", "payments", "security"]
alphabet = string.ascii_letters + string.digits
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def rand_pw(n=28):
    return "".join(secrets.choice(alphabet) for _ in range(n))

mailbox_passwords = {m: rand_pw() for m in mailboxes}

# Rotate mailbox passwords in Mailcow first.
for local, pw in mailbox_passwords.items():
    email = f"{local}@{mail_domain}"
    payload = {
        "attr": {
            "authsource": "mailcow",
            "password": pw,
            "password2": pw,
            "force_pw_update": False,
        },
        "items": [email],
    }
    req = urllib.request.Request(
        f"{mailcow_api_base}/api/v1/edit/mailbox",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-API-Key": mailcow_api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20, context=ssl_ctx) as r:
            body = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Mailcow update failed for {email}: HTTP {e.code}")
    except Exception as e:
        raise SystemExit(f"Mailcow update failed for {email}: {e}")

    try:
        data = json.loads(body)
    except Exception:
        raise SystemExit(f"Mailcow returned invalid JSON for {email}")

    ok = False
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and str(item.get("type", "")).lower() == "success":
                ok = True
                break
    if not ok:
        raise SystemExit(f"Mailcow update did not report success for {email}")

# Upsert related secrets in Infisical.
client = InfisicalClient(ClientSettings(site_url=site_url, access_token=token))

support_email = f"support@{mail_domain}"
sync_values = {
    "SMTP_ENABLED": "true",
    "SMTP_HOST": "smtp.d31337m3.com",
    "SMTP_PORT": "465",
    "SMTP_USERNAME": support_email,
    "SMTP_PASSWORD": mailbox_passwords["support"],
    "SMTP_FROM": support_email,
    "MAILBOX_SUPPORT_EMAIL": support_email,
    "MAILBOX_SUPPORT_PASSWORD": mailbox_passwords["support"],
    "MAILBOX_PAYMENTS_EMAIL": f"payments@{mail_domain}",
    "MAILBOX_PAYMENTS_PASSWORD": mailbox_passwords["payments"],
    "MAILBOX_SECURITY_EMAIL": f"security@{mail_domain}",
    "MAILBOX_SECURITY_PASSWORD": mailbox_passwords["security"],
}

created = 0
updated = 0
for key, value in sync_values.items():
    try:
        client.updateSecret(
            schemas.UpdateSecretOptions(
                environment=environment,
                project_id=project_id,
                path=path,
                secret_name=key,
                secret_value=value,
            )
        )
        updated += 1
        continue
    except Exception as exc:
        msg = str(exc).lower()
        if "not found" not in msg and "no secret" not in msg:
            raise

    client.createSecret(
        schemas.CreateSecretOptions(
            environment=environment,
            project_id=project_id,
            path=path,
            secret_name=key,
            secret_value=value,
        )
    )
    created += 1

print(json.dumps({"mailboxes_rotated": len(mailboxes), "created": created, "updated": updated}))
PY
