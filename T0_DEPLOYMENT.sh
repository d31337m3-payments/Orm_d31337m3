#!/usr/bin/env bash
set -euo pipefail

# D31337m3 T-0 Deployment Script
# Run on production server as root
# Usage: sudo bash t0_deployment.sh

DOMAIN="d31337m3.com"
REPO_DIR="/home/D31337m3/Orm_d31337m3"
SYSTEMD_DIR="/etc/systemd/system"
LETSENCRYPT_DIR="/etc/letsencrypt/live/${DOMAIN}"

echo "=========================================="
echo "D31337m3 T-0 PRODUCTION DEPLOYMENT"
echo "=========================================="
echo ""

# STEP 1: Install Certbot and generate SSL certificates
echo "[T-60m] STEP 1: Installing Certbot and generating SSL certificates..."
if ! command -v certbot &> /dev/null; then
    echo "Installing Certbot..."
    apt-get update -qq
    apt-get install -y certbot python3-certbot-nginx
fi

if [[ ! -d "${LETSENCRYPT_DIR}" ]]; then
    echo "Generating Let's Encrypt certificate for ${DOMAIN}..."
    certbot certonly --nginx -d ${DOMAIN} -d www.${DOMAIN} --non-interactive --agree-tos -m security@${DOMAIN}
    echo "✓ SSL certificate generated at ${LETSENCRYPT_DIR}"
else
    echo "✓ SSL certificate already exists at ${LETSENCRYPT_DIR}"
fi

# STEP 2: Configure systemd services with Infisical token
echo ""
echo "[T-30m] STEP 2: Configuring systemd services..."
echo "⚠️  CRITICAL: Set the INFISICAL_SERVICE_TOKEN environment variable"
echo ""
echo "Export to shell before proceeding:"
echo "   export INFISICAL_SERVICE_TOKEN=<your-token-from-infisical>"
echo ""
read -p "Press Enter once INFISICAL_SERVICE_TOKEN is exported to your shell..."

if [[ -z "${INFISICAL_SERVICE_TOKEN:-}" ]]; then
    echo "❌ ERROR: INFISICAL_SERVICE_TOKEN not set!"
    exit 1
fi

# Install systemd services
for service_file in ${REPO_DIR}/microservices/systemd/d31337m3-*.service; do
    service_name=$(basename "${service_file}")
    echo "Installing systemd unit: ${service_name}"
    
    # Copy service file and inject INFISICAL_SERVICE_TOKEN
    temp_file="/tmp/${service_name}.tmp"
    cp "${service_file}" "${temp_file}"
    
    # Add INFISICAL_SERVICE_TOKEN if not already present
    if ! grep -q "INFISICAL_SERVICE_TOKEN" "${temp_file}"; then
        sed -i "/^Environment=INFISICAL_ENVIRONMENT=/a Environment=INFISICAL_SERVICE_TOKEN=${INFISICAL_SERVICE_TOKEN}" "${temp_file}"
    fi
    
    cp "${temp_file}" "${SYSTEMD_DIR}/${service_name}"
    rm "${temp_file}"
done

systemctl daemon-reload
echo "✓ Systemd services configured"

# STEP 3: Setup Nginx reverse proxy
echo ""
echo "[T-30m] STEP 3: Configuring Nginx reverse proxy..."
cp "${REPO_DIR}/nginx-d31337m3.conf" /etc/nginx/sites-available/d31337m3
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/d31337m3 /etc/nginx/sites-enabled/d31337m3
nginx -t && systemctl reload nginx
echo "✓ Nginx configured and reloaded"

# STEP 4: Verify prerequisites
echo ""
echo "[T-30m] STEP 4: Verifying deployment prerequisites..."
echo "Testing critical endpoints..."

echo -n "  → Verifying DNS resolution: "
if getent hosts ${DOMAIN} > /dev/null; then
    echo "✓"
else
    echo "❌ DNS not resolving. Check DNS records."
    exit 1
fi

echo -n "  → Verifying SSL certificate: "
if openssl x509 -in "${LETSENCRYPT_DIR}/fullchain.pem" -noout 2>/dev/null; then
    echo "✓"
else
    echo "❌ SSL certificate not valid"
    exit 1
fi

echo -n "  → Verifying Nginx config: "
if nginx -t 2>&1 | grep -q "successful"; then
    echo "✓"
else
    echo "❌ Nginx config invalid"
    exit 1
fi

# STEP 5: Start microservices
echo ""
echo "[T-0] STEP 5: Starting microservices..."
for service in client-index payments data-handling auditor watchdog orchestrator support-hub workforce-ops; do
    echo "  → Starting d31337m3-${service}..."
    systemctl start d31337m3-${service}
    sleep 1
done

# STEP 6: Verify services are running
echo ""
echo "[T+5m] STEP 6: Verifying microservice health..."
sleep 3

services=(
    "client-index:8002"
    "payments:8003"
    "data-handling:8004"
    "auditor:8005"
    "orchestrator:8006"
    "watchdog:8007"
    "support-hub:8008"
    "workforce-ops:8009"
)

all_healthy=true
for service_info in "${services[@]}"; do
    service_name=$(echo "${service_info}" | cut -d: -f1)
    port=$(echo "${service_info}" | cut -d: -f2)
    
    if curl -s http://127.0.0.1:${port}/health > /dev/null 2>&1; then
        echo "  ✓ ${service_name} (port ${port})"
    else
        echo "  ❌ ${service_name} (port ${port}) - NOT RESPONDING"
        systemctl status d31337m3-${service_name} || true
        all_healthy=false
    fi
done

if [[ "${all_healthy}" == false ]]; then
    echo ""
    echo "⚠️  Some services are not healthy. Check logs:"
    echo "   journalctl -u d31337m3-orchestrator -n 50"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE - T+5m"
echo "=========================================="
echo ""
echo "Next: Run smoke tests from: ${REPO_DIR}/T0_SMOKE_TESTS.sh"
echo ""
