"""
Infisical Secrets Manager Integration
Replaces direct environment variable loading with secure secret retrieval from Infisical
"""

import os
import time
import random
import logging
from typing import Optional, Dict, Any, List, Callable, TypeVar
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_secrets_cache: Dict[str, str] = {}
_initialized = False

# Infisical connection health tracking
_infisical_connected = False
_infisical_last_success: Optional[float] = None
_infisical_last_failure: Optional[float] = None
_infisical_error: Optional[str] = None
_infisical_latency_ms: Optional[float] = None
_infisical_retry_count = 0

DEFAULT_CORS_ORIGINS = "https://d31337m3.com,https://www.d31337m3.com,http://localhost:3000,http://127.0.0.1:3000"
RETRY_BASE_DELAY = 1.0
RETRY_MAX_DELAY = 30.0
RETRY_MULTIPLIER = 2.0
RETRY_JITTER = 0.1


T = TypeVar("T")


def _with_retry_backoff(fn: Callable[[], T], max_retries: int = 5) -> T:
    """Execute fn with exponential backoff. Returns fn result or re-raises."""
    global _infisical_retry_count
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            start = time.monotonic()
            result = fn()
            elapsed = time.monotonic() - start
            _update_health_success(elapsed)
            _infisical_retry_count = 0
            return result
        except Exception as e:
            _infisical_retry_count = attempt + 1
            last_exc = e
            _update_health_failure(str(e))
            if attempt < max_retries:
                delay = min(RETRY_BASE_DELAY * (RETRY_MULTIPLIER ** attempt), RETRY_MAX_DELAY)
                delay += random.uniform(0, delay * RETRY_JITTER)
                logger.warning(
                    f"Infisical attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
    raise last_exc  # type: ignore[misc]


def _update_health_success(elapsed: float) -> None:
    global _infisical_connected, _infisical_last_success, _infisical_last_failure, _infisical_error, _infisical_latency_ms
    _infisical_connected = True
    _infisical_last_success = time.time()
    _infisical_error = None
    _infisical_latency_ms = round(elapsed * 1000, 1)


def _update_health_failure(error: str) -> None:
    global _infisical_connected, _infisical_last_failure, _infisical_error
    _infisical_connected = False
    _infisical_last_failure = time.time()
    _infisical_error = error


def get_infisical_status() -> dict:
    return {
        "connected": _infisical_connected,
        "initialized": _initialized,
        "cached_secrets": len(_secrets_cache),
        "last_success": _infisical_last_success,
        "last_failure": _infisical_last_failure,
        "error": _infisical_error,
        "latency_ms": _infisical_latency_ms,
        "retry_count": _infisical_retry_count,
    }


def _build_client(cfg: "InfisicalConfig"):
    """Create an Infisical client compatible with either SDK variant."""
    # Legacy SDK variant
    try:
        from infisical_python import InfisicalClient as LegacyClient  # type: ignore

        client_kwargs: Dict[str, Any] = {
            "site_url": cfg.site_url,
            "environment": cfg.environment,
        }

        if cfg.service_token:
            client_kwargs["token"] = cfg.service_token
        elif cfg.client_id and cfg.client_secret:
            client_kwargs["client_id"] = cfg.client_id
            client_kwargs["client_secret"] = cfg.client_secret
        else:
            return None

        return LegacyClient(**client_kwargs)
    except ImportError:
        pass

    # Current SDK variant
    try:
        from infisical_client import InfisicalClient, ClientSettings  # type: ignore

        settings_kwargs: Dict[str, Any] = {
            "site_url": cfg.site_url,
        }
        if cfg.service_token:
            settings_kwargs["access_token"] = cfg.service_token
        elif cfg.client_id and cfg.client_secret:
            settings_kwargs["client_id"] = cfg.client_id
            settings_kwargs["client_secret"] = cfg.client_secret
        else:
            return None

        return InfisicalClient(ClientSettings(**settings_kwargs))
    except ImportError:
        raise


def _list_secrets(client, cfg: "InfisicalConfig"):
    """List secrets across both SDK variants and normalize to an iterable."""
    if hasattr(client, "list_secrets"):
        return client.list_secrets(
            environment=cfg.environment,
            path=cfg.secrets_path,
            project_id=cfg.project_id,
        )

    from infisical_client import schemas  # type: ignore

    opts = schemas.ListSecretsOptions(
        environment=cfg.environment,
        project_id=cfg.project_id,
        path=cfg.secrets_path,
    )
    return client.listSecrets(opts)


def _extract_secret_fields(secret) -> tuple[Optional[str], Optional[str]]:
    """Extract secret key/value across SDK response shapes."""
    key = getattr(secret, "secret_key", None) or getattr(secret, "secretKey", None)
    val = getattr(secret, "secret_value", None) or getattr(secret, "secretValue", None)
    return key, val


@dataclass
class InfisicalConfig:
    site_url: str = field(default_factory=lambda: os.environ.get("INFISICAL_SITE_URL", "https://app.infisical.com"))
    client_id: Optional[str] = field(default_factory=lambda: os.environ.get("INFISICAL_CLIENT_ID"))
    client_secret: Optional[str] = field(default_factory=lambda: os.environ.get("INFISICAL_CLIENT_SECRET"))
    service_token: Optional[str] = field(default_factory=lambda: os.environ.get("INFISICAL_SERVICE_TOKEN"))
    project_id: str = field(default_factory=lambda: os.environ.get("INFISICAL_PROJECT_ID", ""))
    environment: str = field(default_factory=lambda: os.environ.get("INFISICAL_ENVIRONMENT", "prod"))
    secrets_path: str = field(default_factory=lambda: os.environ.get("INFISICAL_SECRETS_PATH", "/"))


def init_infisical(config: Optional[InfisicalConfig] = None) -> bool:
    global _initialized, _secrets_cache

    if _initialized:
        return True

    cfg = config or InfisicalConfig()

    if not cfg.project_id:
        logger.warning("INFISICAL_PROJECT_ID is empty. Infisical cannot be initialized.")
        _update_health_failure("INFISICAL_PROJECT_ID not set")
        return False

    try:
        def _do_init():
            client = _build_client(cfg)
            if not client:
                raise RuntimeError(
                    "No Infisical credentials configured. "
                    "Set INFISICAL_SERVICE_TOKEN or INFISICAL_CLIENT_ID/INFISICAL_CLIENT_SECRET."
                )
            secrets = _list_secrets(client, cfg)
            for secret in secrets:
                key, value = _extract_secret_fields(secret)
                if key is not None and value is not None:
                    _secrets_cache[key] = value

        _with_retry_backoff(_do_init, max_retries=5)

        _initialized = True
        logger.info(
            f"Infisical initialized successfully. Loaded {len(_secrets_cache)} secrets "
            f"from project {cfg.project_id}/{cfg.environment}"
        )
        return True

    except ImportError:
        logger.warning(
            "No supported Infisical SDK installed. "
            "Install with: pip install infisical-python"
        )
        _update_health_failure("Infisical SDK not installed")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Infisical after retries: {e}")
        logger.warning("Application secrets remain unavailable until Infisical initialization succeeds.")
        _update_health_failure(str(e))
        return False


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    if key in _secrets_cache:
        return _secrets_cache[key]
    return default


def require_secret(key: str) -> str:
    value = get_secret(key)
    if value is None or value == "":
        raise RuntimeError(f"Missing required Infisical secret: {key}")
    return value


def get_bool_secret(key: str, default: bool = False) -> bool:
    fallback = "true" if default else "false"
    value = (get_secret(key, fallback) or fallback).strip().lower()
    return value in {"1", "true", "yes", "on"}


def get_int_secret(key: str, default: int) -> int:
    raw = get_secret(key, str(default)) or str(default)
    return int(raw)


def get_csv_secret(key: str, default_csv: str) -> List[str]:
    raw = get_secret(key, default_csv) or default_csv
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_cors_allowed_origins() -> List[str]:
    return get_csv_secret("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)


def load_service_secrets(service_name: str) -> Dict[str, str]:
    cfg = InfisicalConfig()
    if not cfg.project_id:
        return {}

    secrets_path = f"/{service_name}" if cfg.secrets_path == "/" else f"{cfg.secrets_path}/{service_name}"

    try:
        def _do_load():
            client = _build_client(cfg)
            if not client:
                raise RuntimeError("Infisical client not available")
            service_cfg = InfisicalConfig(
                site_url=cfg.site_url,
                client_id=cfg.client_id,
                client_secret=cfg.client_secret,
                service_token=cfg.service_token,
                project_id=cfg.project_id,
                environment=cfg.environment,
                secrets_path=secrets_path,
            )
            return _list_secrets(client, service_cfg)

        service_secrets = _with_retry_backoff(_do_load, max_retries=3)

        result = {}
        for secret in service_secrets:
            key, value = _extract_secret_fields(secret)
            if key is not None and value is not None:
                result[key] = value
                _secrets_cache[key] = value

        return result

    except Exception as e:
        logger.error(f"Failed to load secrets for service '{service_name}' after retries: {e}")
        _update_health_failure(str(e))
        return {}
