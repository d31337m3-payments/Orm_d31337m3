import os
import sys
from datetime import datetime, timezone

# Ensure the backend directory is on sys.path so we can import server.py directly.
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import server


def test_build_promo_code_normalizes_and_parses_expiry():
    promo = server.build_promo_code("  ocAnada75  ", 75, "2026-12-31")
    assert promo["code"] == "OCANADA75"
    assert promo["percent_off"] == 75
    assert promo["expires_at"] == datetime(2026, 12, 31, tzinfo=timezone.utc)
    assert promo["expires_raw"] == "2026-12-31"


def test_promo_is_expired_returns_true_for_past_date():
    expired = server.build_promo_code("EXPIRED", 50, "2020-01-01")
    assert expired is not None
    assert server.promo_is_expired(expired) is True


def test_promo_is_expired_returns_false_for_no_expiry():
    no_expiry = server.build_promo_code("FOREVER", 10, "")
    assert no_expiry is not None
    assert server.promo_is_expired(no_expiry) is False


def test_find_promo_for_code_is_case_insensitive(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "PROMO_CODES", [
        {"code": "OCANADA75", "percent_off": 75, "expires_at": None, "expires_raw": ""}
    ])
    promo = server.find_promo_for_code("ocanada75")
    assert promo is not None
    assert promo["code"] == "OCANADA75"
