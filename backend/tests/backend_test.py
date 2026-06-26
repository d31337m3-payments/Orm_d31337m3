"""d31337m3 backend API integration tests."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://server-connect-30.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@d31337m3.com"
ADMIN_PASSWORD = "Admin2026!!"
CRYPTO_WALLET = "0x4Ffd3170C4b650b2D7681e402b49e6C341274299"


# ---------------- Fixtures ----------------
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_token(session):
    r = session.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["user"]["is_admin"] is True
    return data["token"]


@pytest.fixture(scope="session")
def user_creds():
    return {
        "email": f"testuser+{uuid.uuid4().hex[:8]}@example.com",
        "password": "password123",
        "name": "Test User",
    }


@pytest.fixture(scope="session")
def user_token(session, user_creds):
    r = session.post(f"{API}/auth/register", json=user_creds)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["user"]["subscription_status"] == "trial"
    return data["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------------- Public endpoints ----------------
class TestPublic:
    def test_root(self, session):
        r = session.get(f"{API}/")
        assert r.status_code == 200
        d = r.json()
        assert d["service"] == "d31337m3"
        assert d["status"] == "online"

    def test_plans(self, session):
        r = session.get(f"{API}/plans")
        assert r.status_code == 200
        plans = r.json()["plans"]
        assert len(plans) == 3
        by_id = {p["id"]: p for p in plans}
        assert by_id["basic"]["price_usd"] == 29
        assert by_id["pro"]["price_usd"] == 79
        assert by_id["enterprise"]["price_usd"] == 199
        assert by_id["basic"]["keyword_limit"] == 5

    def test_brokers(self, session):
        r = session.get(f"{API}/data-brokers")
        assert r.status_code == 200
        brokers = r.json()["brokers"]
        assert isinstance(brokers, list) and len(brokers) >= 10
        assert "Spokeo" in brokers


# ---------------- Auth ----------------
class TestAuth:
    def test_register_and_duplicate(self, session, user_token, user_creds):
        # second registration should fail
        r = session.post(f"{API}/auth/register", json=user_creds)
        assert r.status_code == 400

    def test_register_with_valid_promo_code(self, session):
        creds = {
            "email": f"promo+{uuid.uuid4().hex[:8]}@example.com",
            "password": "password123",
            "name": "Promo User",
            "promo_code": "OCanada75",
        }
        r = session.post(f"{API}/auth/register", json=creds)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["user"]["promo_code"] == "OCANADA75"
        assert data["user"]["promo_discount_percent"] == 75
        assert data["user"]["promo_expires_at"]

    def test_register_with_invalid_promo_code(self, session):
        creds = {
            "email": f"promo-invalid+{uuid.uuid4().hex[:8]}@example.com",
            "password": "password123",
            "name": "Promo Invalid",
            "promo_code": "BADCODE",
        }
        r = session.post(f"{API}/auth/register", json=creds)
        assert r.status_code == 400
        assert "Invalid promo code" in r.text

    def test_login_admin(self, session):
        r = session.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        assert r.json()["user"]["is_admin"] is True

    def test_login_wrong_password(self, session):
        r = session.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrongpw"})
        assert r.status_code == 401

    def test_me_requires_token(self, session):
        r = session.get(f"{API}/auth/me")
        assert r.status_code in (401, 403)

    def test_me_with_token(self, session, user_token, user_creds):
        r = session.get(f"{API}/auth/me", headers=auth(user_token))
        assert r.status_code == 200
        assert r.json()["user"]["email"] == user_creds["email"].lower()

    def test_google_auth_creates_user(self, session):
        email = f"gtest+{uuid.uuid4().hex[:8]}@example.com"
        payload = {"email": email, "name": "G User", "google_id": "g-" + uuid.uuid4().hex}
        r = session.post(f"{API}/auth/google", json=payload)
        assert r.status_code == 200
        d = r.json()
        assert "token" in d
        assert d["user"]["email"] == email
        # Repeat call returns existing user
        r2 = session.post(f"{API}/auth/google", json=payload)
        assert r2.status_code == 200
        assert r2.json()["user"]["email"] == email


# ---------------- Keywords ----------------
class TestKeywords:
    def test_add_list_delete(self, session, user_token):
        # add
        r = session.post(f"{API}/keywords", headers=auth(user_token),
                         json={"value": "TEST_John Doe", "type": "name"})
        assert r.status_code == 200, r.text
        kw = r.json()["keyword"]
        assert kw["value"] == "TEST_John Doe"
        kid = kw["id"]
        # list
        r = session.get(f"{API}/keywords", headers=auth(user_token))
        assert r.status_code == 200
        ids = [k["id"] for k in r.json()["keywords"]]
        assert kid in ids
        # delete
        r = session.delete(f"{API}/keywords/{kid}", headers=auth(user_token))
        assert r.status_code == 200

    def test_basic_keyword_limit(self, session):
        # Fresh user (trial -> defaults to basic limit of 5)
        creds = {"email": f"limit+{uuid.uuid4().hex[:8]}@example.com", "password": "password123", "name": "L"}
        r = session.post(f"{API}/auth/register", json=creds)
        assert r.status_code == 200
        tok = r.json()["token"]
        for i in range(5):
            rr = session.post(f"{API}/keywords", headers=auth(tok),
                              json={"value": f"TEST_kw{i}", "type": "name"})
            assert rr.status_code == 200, rr.text
        rr = session.post(f"{API}/keywords", headers=auth(tok),
                          json={"value": "TEST_overflow", "type": "name"})
        assert rr.status_code == 400


# ---------------- Scan + Findings ----------------
class TestScanFindings:
    @pytest.fixture(scope="class")
    def scan_user(self, session):
        creds = {"email": f"scan+{uuid.uuid4().hex[:8]}@example.com", "password": "password123", "name": "S"}
        r = session.post(f"{API}/auth/register", json=creds)
        assert r.status_code == 200
        tok = r.json()["token"]
        # add keyword
        r = session.post(f"{API}/keywords", headers=auth(tok),
                         json={"value": "TEST_Jane Smith", "type": "name"})
        assert r.status_code == 200
        return tok

    def test_scan_run_and_findings(self, session, scan_user):
        tok = scan_user
        r = session.post(f"{API}/scan/run", headers=auth(tok), json={})
        assert r.status_code == 200
        assert r.json()["status"] == "queued"
        # wait for background scan
        findings = []
        for _ in range(8):
            time.sleep(3)
            r = session.get(f"{API}/findings", headers=auth(tok))
            assert r.status_code == 200
            findings = r.json()["findings"]
            if findings:
                break
        assert len(findings) >= 2, f"expected >=2 findings, got {len(findings)}"
        f0 = findings[0]
        for key in ("broker", "severity", "status", "data_found"):
            assert key in f0
        assert f0["status"] == "active"
        assert isinstance(f0["data_found"], list)

    def test_removal_request(self, session, scan_user):
        tok = scan_user
        r = session.get(f"{API}/findings", headers=auth(tok))
        active = [f for f in r.json()["findings"] if f["status"] == "active"]
        assert active, "no active findings to remove"
        fid = active[0]["id"]
        r = session.post(f"{API}/findings/removal-request", headers=auth(tok),
                         json={"finding_id": fid})
        assert r.status_code == 200
        # verify status changed
        r = session.get(f"{API}/findings", headers=auth(tok))
        target = next(f for f in r.json()["findings"] if f["id"] == fid)
        assert target["status"] == "pending_removal"

    def test_reputation(self, session, scan_user):
        r = session.get(f"{API}/reputation", headers=auth(scan_user))
        assert r.status_code == 200
        d = r.json()
        assert 0 <= d["score"] <= 100
        bd = d["breakdown"]
        for k in ("total_findings", "active", "removed", "pending_removal", "high_severity"):
            assert k in bd


# ---------------- Subscribe / Payments ----------------
class TestSubscribe:
    @pytest.fixture(scope="class")
    def sub_user(self, session):
        creds = {"email": f"sub+{uuid.uuid4().hex[:8]}@example.com", "password": "password123", "name": "Sub"}
        r = session.post(f"{API}/auth/register", json=creds)
        assert r.status_code == 200
        return r.json()["token"]

    def test_subscribe_interac(self, session, sub_user):
        r = session.post(f"{API}/subscribe", headers=auth(sub_user),
                         json={"plan_id": "basic", "payment_method": "interac"})
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "awaiting_confirmation"
        instr = d["instructions"]
        assert instr["recipient_email"] == "payments@d31337m3.com"
        assert instr["amount_usd"] == 29

    def test_subscribe_crypto_no_tx(self, session, sub_user):
        r = session.post(f"{API}/subscribe", headers=auth(sub_user),
                         json={"plan_id": "pro", "payment_method": "crypto"})
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "awaiting_tx_hash"
        assert d["instructions"]["wallet"] == CRYPTO_WALLET
        assert set(d["instructions"]["networks"]) == {"ethereum", "polygon", "base"}

    def test_subscribe_crypto_invalid_tx(self, session, sub_user):
        r = session.post(f"{API}/subscribe", headers=auth(sub_user),
                         json={"plan_id": "basic", "payment_method": "crypto",
                               "network": "base", "tx_hash": "0xinvalid"})
        assert r.status_code == 200
        assert r.json()["status"] == "pending_manual_review"

    def test_subscribe_paypal_unavailable(self, session, sub_user):
        r = session.post(f"{API}/subscribe", headers=auth(sub_user),
                         json={"plan_id": "basic", "payment_method": "paypal"})
        assert r.status_code == 200
        assert r.json()["status"] == "paypal_unavailable"

    def test_list_payments(self, session, sub_user):
        r = session.get(f"{API}/payments", headers=auth(sub_user))
        assert r.status_code == 200
        assert len(r.json()["payments"]) >= 4


# ---------------- Admin ----------------
class TestAdmin:
    def test_admin_stats(self, session, admin_token):
        r = session.get(f"{API}/admin/stats", headers=auth(admin_token))
        assert r.status_code == 200
        d = r.json()
        for k in ("users", "active_subs", "keywords", "findings_total"):
            assert k in d

    def test_admin_users(self, session, admin_token):
        r = session.get(f"{API}/admin/users", headers=auth(admin_token))
        assert r.status_code == 200
        assert len(r.json()["users"]) >= 1

    def test_admin_payments(self, session, admin_token):
        r = session.get(f"{API}/admin/payments", headers=auth(admin_token))
        assert r.status_code == 200

    def test_admin_email_log(self, session, admin_token):
        r = session.get(f"{API}/admin/email-log", headers=auth(admin_token))
        assert r.status_code == 200
        emails = r.json()["emails"]
        # registration/welcome emails should have been logged
        assert len(emails) >= 1
        assert any(e.get("mocked") is True for e in emails)

    def test_non_admin_forbidden(self, session, user_token):
        for path in ["/admin/stats", "/admin/users", "/admin/payments", "/admin/email-log"]:
            r = session.get(f"{API}{path}", headers=auth(user_token))
            assert r.status_code == 403, f"{path} expected 403 got {r.status_code}"

    def test_admin_confirm_and_reject(self, session, admin_token):
        # find pending interac payment
        r = session.get(f"{API}/admin/payments", headers=auth(admin_token))
        payments = r.json()["payments"]
        confirmable = [p for p in payments if p["status"] in ("awaiting_confirmation", "pending_manual_review")]
        if not confirmable:
            pytest.skip("no payments to confirm")
        target = confirmable[0]
        r = session.post(f"{API}/admin/payments/{target['id']}/confirm", headers=auth(admin_token))
        assert r.status_code == 200
        # reject second one
        rej_target = next((p for p in confirmable[1:]), None)
        if rej_target:
            r = session.post(f"{API}/admin/payments/{rej_target['id']}/reject", headers=auth(admin_token))
            assert r.status_code == 200
