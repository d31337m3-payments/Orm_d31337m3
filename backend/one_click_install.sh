#!/usr/bin/env bash
###############################################################################
# d31337m3 — One-Click Installer
# -----------------------------------------------------------------------------
# Usage (after `git clone` on a fresh server):
#   chmod +x install.sh && sudo ./install.sh
#
# Supported: Ubuntu 20.04+, Debian 11+, Linux Mint 20+, Pop!_OS 20.04+
# What it does:
#   1. Installs system deps (Python 3.11, Node 18+, Yarn, MongoDB, supervisor)
#   2. Installs backend Python deps
#   3. Installs frontend yarn deps
#   4. Bootstraps backend/.env and frontend/.env with safe defaults (interactive)
#   5. Generates a random JWT secret
#   6. Seeds the admin user
#   7. Writes supervisor configs and starts both services
#   8. Prints the working URLs
###############################################################################

set -e
set -u
set -o pipefail

# ── COLORS ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$REPO_DIR/backend"
FRONTEND_DIR="$REPO_DIR/frontend"

# ── BANNER ───────────────────────────────────────────────────────────────────
banner() {
cat <<'EOF'

  ╔════════════════════════════════════════════════════════════════════╗
  ║                                                                    ║
  ║    d3 1337 m3   —   delete me from the internet.                   ║
  ║                                                                    ║
  ║    One-click installer · Made in Canada 🇨🇦                       ║
  ║                                                                    ║
  ╚════════════════════════════════════════════════════════════════════╝

EOF
}

log()  { echo -e "${CYAN}[$(date +%H:%M:%S)]${NC} $*"; }
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
err()  { echo -e "${RED}✗${NC} $*"; }
section() { echo -e "\n${BOLD}${BLUE}━━━ $* ━━━${NC}\n"; }

require_root() {
  if [[ $EUID -ne 0 ]]; then
    err "This script must be run as root. Try: ${BOLD}sudo $0${NC}"
    exit 1
  fi
}

detect_distro() {
  if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    DISTRO="${ID:-unknown}"
    DISTRO_VER="${VERSION_ID:-unknown}"
  else
    DISTRO="unknown"; DISTRO_VER="unknown"
  fi
  log "Detected: $DISTRO $DISTRO_VER"
  if [[ "$DISTRO" != "ubuntu" && "$DISTRO" != "debian" && "$DISTRO" != "linuxmint" && "$DISTRO" != "pop" ]]; then
    warn "Untested distro ($DISTRO). Proceeding — your mileage may vary."
  fi
}

# ── PROMPTS ──────────────────────────────────────────────────────────────────
prompt_default() {
  local question="$1" default="$2" varname="$3"
  read -r -p "  $question [$default]: " input || true
  eval "$varname=\"${input:-$default}\""
}

prompt_secret() {
  local question="$1" varname="$2"
  read -r -s -p "  $question: " input || true
  echo
  eval "$varname=\"$input\""
}

# ── SYSTEM PACKAGES ──────────────────────────────────────────────────────────
install_system_deps() {
  section "Step 1/7 · System packages"

  log "Updating apt cache..."
  apt-get update -qq

  log "Installing base packages..."
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    curl wget gnupg ca-certificates lsb-release software-properties-common \
    build-essential git ufw supervisor

  # Python 3.11
  if ! command -v python3.11 >/dev/null 2>&1; then
    log "Installing Python 3.11..."
    add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
      python3.11 python3.11-venv python3.11-dev python3-pip || \
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3 python3-venv python3-dev python3-pip
  fi
  ok "Python: $(python3 --version)"

  # Node.js 20 LTS
  if ! command -v node >/dev/null 2>&1 || [[ "$(node -v | cut -d. -f1 | tr -d 'v')" -lt 18 ]]; then
    log "Installing Node.js 20 LTS..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >/dev/null
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nodejs
  fi
  ok "Node.js: $(node -v)"

  # Yarn
  if ! command -v yarn >/dev/null 2>&1; then
    log "Installing Yarn..."
    npm install -g yarn >/dev/null 2>&1
  fi
  ok "Yarn: $(yarn -v)"

  # MongoDB Community 7.0
  if ! command -v mongod >/dev/null 2>&1; then
    log "Installing MongoDB Community 7.0..."
    curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg
    local codename
    codename=$(lsb_release -cs)
    # MongoDB doesn't always publish for every codename; fall back to jammy on Ubuntu
    if [[ "$DISTRO" == "ubuntu" ]]; then
      echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu ${codename}/mongodb-org/7.0 multiverse" \
        > /etc/apt/sources.list.d/mongodb-org-7.0.list || true
    else
      echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/debian ${codename}/mongodb-org/7.0 main" \
        > /etc/apt/sources.list.d/mongodb-org-7.0.list || true
    fi
    apt-get update -qq || warn "MongoDB repo not available for ${codename}, falling back to default."
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq mongodb-org || {
      warn "mongodb-org install failed. Trying generic mongodb package..."
      DEBIAN_FRONTEND=noninteractive apt-get install -y -qq mongodb || {
        err "Failed to install MongoDB. Install it manually then re-run this script."
        exit 1
      }
    }
  fi

  log "Starting MongoDB..."
  systemctl enable mongod 2>/dev/null || systemctl enable mongodb 2>/dev/null || true
  systemctl start mongod 2>/dev/null || systemctl start mongodb 2>/dev/null || true
  sleep 2
  if pgrep -f mongod >/dev/null; then
    ok "MongoDB running"
  else
    warn "MongoDB may not have started — check 'systemctl status mongod'"
  fi
}

# ── ENV BOOTSTRAPPING ────────────────────────────────────────────────────────
collect_config() {
  section "Step 2/7 · Configuration"

  echo "  Press ENTER to accept the default values shown in brackets."
  echo

  prompt_default "Public site URL (no trailing slash)" "http://localhost:3000"           PUBLIC_URL
  prompt_default "Backend public URL (use the same hostname; backend is auto-proxied)" "$PUBLIC_URL" BACKEND_URL
  prompt_default "MongoDB URL" "mongodb://localhost:27017"                                MONGO_URL
  prompt_default "Database name" "d31337m3_db"                                            DB_NAME

  echo
  echo "  ${BOLD}— Admin user (seeded on first boot) —${NC}"
  prompt_default "Admin email" "admin@d31337m3.com"                                       ADMIN_EMAIL
  prompt_secret  "Admin password (will not echo)"                                         ADMIN_PASSWORD
  ADMIN_PASSWORD="${ADMIN_PASSWORD:-Admin2026!!}"

  echo
  echo "  ${BOLD}— SMTP (for outbound email) —${NC}"
  prompt_default "SMTP host" "mail.d31337m3.com"                                          SMTP_HOST
  prompt_default "SMTP port (465 SSL · 587 STARTTLS)" "465"                               SMTP_PORT
  prompt_default "SMTP username" "support@d31337m3.com"                                     SMTP_USERNAME
  prompt_secret  "SMTP password (will not echo)"                                          SMTP_PASSWORD
  SMTP_PASSWORD="${SMTP_PASSWORD:-Admin2026!!}"
  prompt_default "Enable SMTP delivery now? (true/false)" "true"                          SMTP_ENABLED

  echo
  echo "  ${BOLD}— Payments —${NC}"
  prompt_default "Interac auto-deposit email" "payments@d31337m3.com"                     PAYMENTS_EMAIL
  prompt_default "Crypto receiving wallet (USDC on ETH/Polygon/Base)" "0x4Ffd3170C4b650b2D7681e402b49e6C341274299" CRYPTO_WALLET
  prompt_default "PayPal Client ID (leave empty to disable PayPal)" ""                    PAYPAL_CLIENT_ID
  if [[ -n "$PAYPAL_CLIENT_ID" ]]; then
    prompt_secret "PayPal Client Secret"                                                  PAYPAL_CLIENT_SECRET
  else
    PAYPAL_CLIENT_SECRET=""
  fi

  JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || head -c 64 /dev/urandom | base64 | tr -d '/+=' | head -c 64)

  ok "Configuration captured."
}

write_env_files() {
  section "Step 3/7 · Writing .env files"

  cat > "$BACKEND_DIR/.env" <<EOF
MONGO_URL="$MONGO_URL"
DB_NAME="$DB_NAME"
CORS_ORIGINS="$PUBLIC_URL,http://localhost:3000"
JWT_SECRET="$JWT_SECRET"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440
PROMO_CODE_PRIMARY="OCanada75"
PROMO_PERCENT_PRIMARY=75
PROMO_EXPIRES_PRIMARY="2026-12-31"
PROMO_CODE_SECONDARY=""
PROMO_PERCENT_SECONDARY=0
PROMO_EXPIRES_SECONDARY=""
SMTP_HOST="$SMTP_HOST"
SMTP_PORT=$SMTP_PORT
SMTP_USERNAME="$SMTP_USERNAME"
SMTP_PASSWORD="$SMTP_PASSWORD"
SMTP_FROM="d31337m3 <$SMTP_USERNAME>"
SMTP_ENABLED="$SMTP_ENABLED"
CRYPTO_WALLET="$CRYPTO_WALLET"
ETHEREUM_RPC_URL="https://eth.llamarpc.com"
POLYGON_RPC_URL="https://polygon-rpc.com"
BASE_RPC_URL="https://mainnet.base.org"
USDC_ETHEREUM="0xA0b86991c6218b36c1D19D4a2e9Eb0cE3606eB48"
USDC_POLYGON="0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
USDC_BASE="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
PAYPAL_CLIENT_ID="$PAYPAL_CLIENT_ID"
PAYPAL_CLIENT_SECRET="$PAYPAL_CLIENT_SECRET"
PAYPAL_API_BASE="https://api-m.paypal.com"
PAYMENTS_EMAIL="$PAYMENTS_EMAIL"
ADMIN_EMAIL="$ADMIN_EMAIL"
ADMIN_PASSWORD="$ADMIN_PASSWORD"
EOF
  chmod 600 "$BACKEND_DIR/.env"
  ok "backend/.env written"

  cat > "$FRONTEND_DIR/.env" <<EOF
REACT_APP_BACKEND_URL=$BACKEND_URL
WDS_SOCKET_PORT=443
ENABLE_HEALTH_CHECK=false
EOF
  ok "frontend/.env written"
}

# ── INSTALL DEPS ─────────────────────────────────────────────────────────────
install_backend() {
  section "Step 4/7 · Backend Python dependencies"
  cd "$BACKEND_DIR"

  if ! command -v pip3 >/dev/null 2>&1; then
    log "Installing pip..."
    apt-get install -y -qq python3-pip
  fi

  log "Installing requirements.txt..."
  pip3 install --quiet --upgrade pip
  pip3 install --quiet -r requirements.txt
  # Extra deps used by d31337m3
  pip3 install --quiet aiosmtplib web3 beautifulsoup4 lxml aiohttp pyjwt bcrypt 'passlib[bcrypt]' || true
  ok "Backend deps installed"
}

install_frontend() {
  section "Step 5/7 · Frontend dependencies"
  cd "$FRONTEND_DIR"
  log "Running yarn install (this can take a few minutes)..."
  yarn install --silent --frozen-lockfile 2>&1 | tail -3 || yarn install --silent
  ok "Frontend deps installed"
}

# ── SUPERVISOR ───────────────────────────────────────────────────────────────
write_supervisor_configs() {
  section "Step 6/7 · Supervisor configuration"

  cat > /etc/supervisor/conf.d/d31337m3-backend.conf <<EOF
[program:d31337m3-backend]
command=/usr/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload
directory=$BACKEND_DIR
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/var/log/supervisor/d31337m3-backend.err.log
stdout_logfile=/var/log/supervisor/d31337m3-backend.out.log
environment=PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EOF

  cat > /etc/supervisor/conf.d/d31337m3-frontend.conf <<EOF
[program:d31337m3-frontend]
command=/usr/bin/yarn start
directory=$FRONTEND_DIR
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/var/log/supervisor/d31337m3-frontend.err.log
stdout_logfile=/var/log/supervisor/d31337m3-frontend.out.log
environment=HOST="0.0.0.0",PORT="3000",PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EOF
  ok "Supervisor configs written"

  log "Reloading supervisor..."
  systemctl enable supervisor >/dev/null 2>&1 || true
  systemctl start supervisor >/dev/null 2>&1 || true
  supervisorctl reread >/dev/null
  supervisorctl update >/dev/null
  ok "Supervisor reloaded"
}

# ── FIREWALL ─────────────────────────────────────────────────────────────────
configure_firewall() {
  if command -v ufw >/dev/null 2>&1; then
    log "Configuring UFW (allowing 22, 80, 443, 3000, 8001)..."
    ufw allow 22/tcp     >/dev/null 2>&1 || true
    ufw allow 80/tcp     >/dev/null 2>&1 || true
    ufw allow 443/tcp    >/dev/null 2>&1 || true
    ufw allow 3000/tcp   >/dev/null 2>&1 || true
    ufw allow 8001/tcp   >/dev/null 2>&1 || true
    ok "Firewall rules applied (run 'ufw enable' manually when ready)."
  fi
}

# ── HEALTH CHECK ─────────────────────────────────────────────────────────────
health_check() {
  section "Step 7/7 · Health check"
  log "Waiting 10s for services to boot..."
  sleep 10

  if curl -fs http://localhost:8001/api/ >/dev/null 2>&1; then
    ok "Backend responding on http://localhost:8001"
  else
    warn "Backend not yet responding. Check: ${BOLD}sudo supervisorctl tail d31337m3-backend stderr${NC}"
  fi

  if curl -fs http://localhost:3000 >/dev/null 2>&1; then
    ok "Frontend responding on http://localhost:3000"
  else
    warn "Frontend not yet responding (first compile takes ~30-60s). Check: ${BOLD}sudo supervisorctl tail d31337m3-frontend stdout${NC}"
  fi
}

# ── DONE ─────────────────────────────────────────────────────────────────────
print_summary() {
  echo
  echo -e "${GREEN}${BOLD}╔════════════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}${BOLD}║                  ✓  d31337m3 INSTALL COMPLETE                      ║${NC}"
  echo -e "${GREEN}${BOLD}╚════════════════════════════════════════════════════════════════════╝${NC}"
  echo
  echo -e "  ${BOLD}Frontend:${NC}     $PUBLIC_URL"
  echo -e "  ${BOLD}Backend API:${NC}  ${BACKEND_URL}/api"
  echo -e "  ${BOLD}Admin login:${NC}  $ADMIN_EMAIL"
  echo
  echo -e "  ${CYAN}Useful commands:${NC}"
  echo -e "    • Tail backend logs   : ${BOLD}sudo supervisorctl tail -f d31337m3-backend stderr${NC}"
  echo -e "    • Restart backend     : ${BOLD}sudo supervisorctl restart d31337m3-backend${NC}"
  echo -e "    • Restart frontend    : ${BOLD}sudo supervisorctl restart d31337m3-frontend${NC}"
  echo -e "    • Check service status: ${BOLD}sudo supervisorctl status${NC}"
  echo -e "    • Mongo shell         : ${BOLD}mongosh $DB_NAME${NC}"
  echo
  echo -e "  ${YELLOW}Next steps:${NC}"
  if [[ -z "$PAYPAL_CLIENT_ID" ]]; then
    echo -e "    • Add PayPal credentials to ${BOLD}backend/.env${NC} and run ${BOLD}sudo supervisorctl restart d31337m3-backend${NC}"
  fi
  echo -e "    • Set up an Nginx reverse proxy + Let's Encrypt for HTTPS in production."
  echo -e "    • Enable the firewall once you've tested everything: ${BOLD}sudo ufw enable${NC}"
  echo
  echo -e "  ${RED}Made in Canada 🇨🇦${NC}  ·  delete me, dot com."
  echo
}

# ── MAIN ─────────────────────────────────────────────────────────────────────
main() {
  banner
  require_root
  detect_distro
  install_system_deps
  collect_config
  write_env_files
  install_backend
  install_frontend
  write_supervisor_configs
  configure_firewall
  health_check
  print_summary
}

main "$@"
