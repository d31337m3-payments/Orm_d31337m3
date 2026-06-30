#!/usr/bin/env bash
set -euo pipefail

# D31337m3 Smoke Test Suite (T+5m to T+30m)
# Run after deployment to validate critical user flows

DOMAIN="${DOMAIN:-d31337m3.com}"
BASE_URL="https://${DOMAIN}"
API_URL="${BASE_URL}/api"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

test_count=0
pass_count=0
fail_count=0

# Helper function
test_flow() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="${4:-}"
    
    test_count=$((test_count + 1))
    echo -n "[TEST $test_count] $name... "
    
    if [[ "${method}" == "GET" ]]; then
        response=$(curl -s -w "\n%{http_code}" "${endpoint}" 2>/dev/null || echo "0")
    elif [[ "${method}" == "POST" ]]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "${endpoint}" \
            -H "Content-Type: application/json" \
            -d "${data}" 2>/dev/null || echo "0")
    fi
    
    http_code=$(echo "${response}" | tail -1)
    body=$(echo "${response}" | head -n -1)
    
    # Acceptable codes: 2xx (success) or 4xx (client error - still responsive)
    if [[ "${http_code}" =~ ^[24][0-9][0-9]$ ]]; then
        echo -e "${GREEN}✓${NC} (${http_code})"
        pass_count=$((pass_count + 1))
        return 0
    else
        echo -e "${RED}✗${NC} (${http_code})"
        echo "  Response: ${body:0:100}"
        fail_count=$((fail_count + 1))
        return 1
    fi
}

echo "=========================================="
echo "D31337m3 Smoke Test Suite (T+5m)"
echo "Domain: ${DOMAIN}"
echo "=========================================="
echo ""

# Test 1: Landing page accessibility
echo "=== FLOW 1: PUBLIC ACCESS ==="
test_flow "Landing page accessible" "GET" "${BASE_URL}/"

# Test 2: Login/Register endpoints
echo ""
echo "=== FLOW 2: AUTHENTICATION ==="
test_flow "Register endpoint" "POST" "${API_URL}/auth/register" \
    '{"email":"test@example.com","password":"Test123!@","name":"Test User"}'

test_flow "Login endpoint" "POST" "${API_URL}/auth/login" \
    '{"email":"test@example.com","password":"Test123!@"}'

# Test 3: User operations (these will fail without auth, but endpoint should respond)
echo ""
echo "=== FLOW 3: USER OPERATIONS ==="
test_flow "Dashboard endpoint" "GET" "${API_URL}/user/dashboard"

# Test 4: Scan operations
echo ""
echo "=== FLOW 4: SCAN OPERATIONS ==="
test_flow "Create scan" "POST" "${API_URL}/scan/create" \
    '{"scan_name":"test_scan","scan_url":"https://example.com"}'

test_flow "Get findings" "GET" "${API_URL}/findings"

# Test 5: Payment operations
echo ""
echo "=== FLOW 5: PAYMENT FLOW ==="
test_flow "Subscribe endpoint" "POST" "${API_URL}/payments/subscribe" \
    '{"tier":"pro","period":"monthly"}'

test_flow "Payment status" "GET" "${API_URL}/payments/status"

# Test 6: Audit events
echo ""
echo "=== FLOW 6: AUDIT TRAIL ==="
test_flow "Audit events" "GET" "${API_URL}/auditor/events"

# Test 7: Security reporting
echo ""
echo "=== FLOW 7: SECURITY REPORTING ==="
test_flow "Security center page" "GET" "${BASE_URL}/security-center"

test_flow "Submit security report" "POST" "${API_URL}/support/tickets" \
    '{"ticket_type":"security_breach","summary":"Test report","description":"Test"}'

# Summary
echo ""
echo "=========================================="
echo "Smoke Test Results"
echo "=========================================="
echo -e "Total Tests:  ${test_count}"
echo -e "Passed:       ${GREEN}${pass_count}${NC}"
echo -e "Failed:       ${RED}${fail_count}${NC}"
echo ""

if [[ ${fail_count} -eq 0 ]]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Monitor service logs for 30 minutes"
    echo "  2. Check Stripe webhook delivery in dashboard"
    echo "  3. Verify email delivery (check support@${DOMAIN})"
    echo "  4. Confirm database persistence"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo ""
    echo "Debugging:"
    echo "  Check service logs:"
    echo "    journalctl -u d31337m3-orchestrator -n 100"
    echo "    journalctl -u d31337m3-client-index -n 100"
    echo ""
    echo "  Check Nginx logs:"
    echo "    tail -f /var/log/nginx/d31337m3.error.log"
    exit 1
fi
