#!/usr/bin/env bash
set -euo pipefail

# Configure Systemd Services with Infisical Token
# Run on production server as root
# Usage: sudo bash configure_systemd_infisical.sh <INFISICAL_SERVICE_TOKEN>

if [[ $# -ne 1 ]]; then
    echo "Usage: sudo bash configure_systemd_infisical.sh <INFISICAL_SERVICE_TOKEN>"
    echo ""
    echo "Example:"
    echo "  sudo bash configure_systemd_infisical.sh 'st_0123456789abcdef...'"
    exit 1
fi

INFISICAL_TOKEN="$1"
REPO_DIR="/home/D31337m3/Orm_d31337m3"
SYSTEMD_DIR="/etc/systemd/system"

echo "Configuring systemd services with Infisical token..."
echo ""

# Update each systemd service file
for service_file in ${REPO_DIR}/microservices/systemd/d31337m3-*.service; do
    service_name=$(basename "${service_file}")
    dest_file="${SYSTEMD_DIR}/${service_name}"
    
    # Copy service file
    cp "${service_file}" "${dest_file}"
    
    # Add INFISICAL_SERVICE_TOKEN if not already present
    if ! grep -q "INFISICAL_SERVICE_TOKEN" "${dest_file}"; then
        # Find the line with "INFISICAL_ENVIRONMENT=" and add token after it
        sed -i "/^Environment=INFISICAL_ENVIRONMENT=/a Environment=INFISICAL_SERVICE_TOKEN=${INFISICAL_TOKEN}" "${dest_file}"
    else
        # Replace existing token
        sed -i "s|^Environment=INFISICAL_SERVICE_TOKEN=.*|Environment=INFISICAL_SERVICE_TOKEN=${INFISICAL_TOKEN}|" "${dest_file}"
    fi
    
    echo "✓ ${service_name}"
done

# Reload systemd daemon
systemctl daemon-reload
echo ""
echo "✓ Systemd daemon reloaded"
echo ""
echo "Services ready to start:"
echo "  systemctl start d31337m3-client-index"
echo "  systemctl start d31337m3-payments"
echo "  systemctl start d31337m3-orchestrator"
echo "  # ... etc for all 8 services"
echo ""
echo "Or use: ./microservices/start_all.sh"
