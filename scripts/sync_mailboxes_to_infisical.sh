#!/usr/bin/env bash
set -euo pipefail

# Sync mailbox credentials into Infisical and set SMTP runtime secrets.
# This script intentionally avoids printing secret values.

ROOT_DIR="/home/D31337m3/Orm_d31337m3"
CSV_FILE="${CSV_FILE:-${ROOT_DIR}/.mailboxes_d31337m3.com_credentials.csv}"
RUNTIME_ENV_PRIMARY="${ROOT_DIR}/.env.infisical.runtime.generated"
RUNTIME_ENV_FALLBACK="${ROOT_DIR}/.env.infisical.runtime"
PYTHON_BIN="${ROOT_DIR}/microservices/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python venv not found at $PYTHON_BIN" >&2
  exit 1
fi

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

if [[ ! -f "$CSV_FILE" ]]; then
  echo "Mailbox credentials CSV not found: $CSV_FILE" >&2
  exit 1
fi

CSV_FILE="$CSV_FILE" "$PYTHON_BIN" - <<'PY'
import csv
import json
import os
import sys

from infisical_client import ClientSettings, InfisicalClient, schemas

csv_path = os.environ["CSV_FILE"]
site_url = os.environ.get("INFISICAL_SITE_URL", "https://app.infisical.com")
project_id = os.environ.get("INFISICAL_PROJECT_ID", "")
environment = os.environ.get("INFISICAL_ENVIRONMENT", "prod")
path = os.environ.get("INFISICAL_SECRETS_PATH", "/")
token = os.environ.get("INFISICAL_SERVICE_TOKEN", "")

if not project_id or not token:
    print("Missing Infisical auth context", file=sys.stderr)
    sys.exit(2)

mailboxes = {}
with open(csv_path, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        email = (row.get("email") or "").strip().lower()
        password = (row.get("password") or "").strip()
        status = (row.get("status") or "").strip().lower()
        if not email or not status:
            continue
        local = email.split("@", 1)[0]
        mailboxes[local] = {
            "email": email,
            "password": password,
            "status": status,
        }

required_locals = ["support", "payments", "security"]
missing = [k for k in required_locals if k not in mailboxes or not mailboxes[k]["password"]]
if missing:
    print(f"Missing generated passwords for: {', '.join(missing)}", file=sys.stderr)
    sys.exit(3)

support_email = mailboxes["support"]["email"]
support_password = mailboxes["support"]["password"]

secrets_to_upsert = {
    "SMTP_ENABLED": "true",
    "SMTP_HOST": "smtp.d31337m3.com",
    "SMTP_PORT": "465",
    "SMTP_USERNAME": support_email,
    "SMTP_PASSWORD": support_password,
    "SMTP_FROM": support_email,
    "MAILBOX_SUPPORT_EMAIL": support_email,
    "MAILBOX_SUPPORT_PASSWORD": support_password,
    "MAILBOX_PAYMENTS_EMAIL": mailboxes["payments"]["email"],
    "MAILBOX_PAYMENTS_PASSWORD": mailboxes["payments"]["password"],
    "MAILBOX_SECURITY_EMAIL": mailboxes["security"]["email"],
    "MAILBOX_SECURITY_PASSWORD": mailboxes["security"]["password"],
}

client = InfisicalClient(ClientSettings(site_url=site_url, access_token=token))

created = 0
updated = 0
for key, value in secrets_to_upsert.items():
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

print(json.dumps({"created": created, "updated": updated, "total": len(secrets_to_upsert)}))
PY
