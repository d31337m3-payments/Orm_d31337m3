#!/usr/bin/env python3
"""
JWT Utility Service for Microservices Authentication
Handles service-to-service authentication using JWT tokens
"""
import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from secrets_manager import get_secret

# Service-specific JWT secrets (loaded from Infisical vault in production)
SERVICE_JWT_SECRETS = {
    "client_index": get_secret("CLIENT_INDEX_JWT_SECRET", "client_index_secret_change_in_prod"),
    "payments": get_secret("PAYMENTS_JWT_SECRET", "payments_secret_change_in_prod"),
    "data_handling": get_secret("DATA_HANDLING_JWT_SECRET", "data_handling_secret_change_in_prod"),
    "auditor": get_secret("AUDITOR_JWT_SECRET", "auditor_secret_change_in_prod"),
    "watchdog": get_secret("WATCHDOG_JWT_SECRET", "watchdog_secret_change_in_prod"),
    "orchestrator": get_secret("ORCHESTRATOR_JWT_SECRET", "orchestrator_secret_change_in_prod"),
}

# Shared secret for backward compatibility with existing frontend
LEGACY_JWT_SECRET = get_secret("JWT_SECRET", "your_jwt_secret_here_change_this_in_production")
JWT_ALGORITHM = get_secret("JWT_ALGORITHM", "HS256")
TOKEN_EXP_MIN = int(get_secret("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
SECRET_MANAGED_ADMIN_EMAIL = "admin@d31337m3.com"


def _normalize_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    normalized = str(email).strip().lower()
    return normalized or None


def configured_admin_email() -> Optional[str]:
    return _normalize_email(get_secret("ADMIN_EMAIL"))


def user_has_admin_access(email: Optional[str], stored_is_admin: bool = False) -> bool:
    normalized_email = _normalize_email(email)
    configured_email = configured_admin_email()

    if configured_email and normalized_email == configured_email:
        return True

    return bool(stored_is_admin)


def _lookup_user_email(user_id: Optional[str]) -> Optional[str]:
    if not user_id:
        return None

    try:
        from database import SessionLocal, User

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            return _normalize_email(user.email if user else None)
        finally:
            db.close()
    except Exception:
        return None


def create_service_token(service_name: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token for service-to-service authentication
    
    Args:
        service_name: Name of the service creating the token
        expires_delta: Optional expiration time delta
        
    Returns:
        JWT token string
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXP_MIN)
    
    payload = {
        "iss": service_name,  # Issuer - which service created this token
        "iat": datetime.now(timezone.utc),
        "exp": expire,
        "type": "service_to_service"
    }
    
    secret = SERVICE_JWT_SECRETS.get(service_name, LEGACY_JWT_SECRET)
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def verify_service_token(token: str, expected_issuer: Optional[str] = None) -> Dict[str, Any]:
    """
    Verify a JWT token for service-to-service authentication
    
    Args:
        token: JWT token to verify
        expected_issuer: Optional expected issuer service name
        
    Returns:
        Decoded token payload
        
    Raises:
        jwt.InvalidTokenError: If token is invalid
    """
    # Try to decode with each service secret to support service-to-service communication
    last_exception = None
    
    for service_name, secret in SERVICE_JWT_SECRETS.items():
        try:
            payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
            
            # Verify issuer if expected
            if expected_issuer and payload.get("iss") != expected_issuer:
                continue
                
            # Verify token type
            if payload.get("type") != "service_to_service":
                continue
                
            return payload
        except jwt.InvalidTokenError as e:
            last_exception = e
            continue
    
    # Also try legacy secret for backward compatibility
    try:
        payload = jwt.decode(token, LEGACY_JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if expected_issuer and payload.get("iss") != expected_issuer:
            raise jwt.InvalidTokenError("Invalid issuer")
        if payload.get("type") != "service_to_service":
            raise jwt.InvalidTokenError("Invalid token type")
        return payload
    except jwt.InvalidTokenError as e:
        last_exception = e
    
    raise last_exception


def create_user_token(
    user_id: str,
    is_admin: bool = False,
    service_name: str = "legacy",
    email: Optional[str] = None,
    employee_number: Optional[str] = None,
) -> str:
    """
    Create a JWT token for user authentication (backward compatibility)
    
    Args:
        user_id: User identifier
        is_admin: Whether user is admin
        service_name: Service creating the token (for tracking)
        email: User email
        employee_number: Employee number (for workforce/support portal access)
        
    Returns:
        JWT token string
    """
    normalized_email = _normalize_email(email)
    payload = {
        "sub": user_id,
        "is_admin": user_has_admin_access(normalized_email, is_admin),
        "iss": service_name,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXP_MIN),
        "type": "user"
    }
    if normalized_email:
        payload["email"] = normalized_email
    if employee_number:
        payload["employee_number"] = employee_number
    
    secret = SERVICE_JWT_SECRETS.get(service_name, LEGACY_JWT_SECRET)
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def verify_user_token(token: str) -> Dict[str, Any]:
    """
    Verify a JWT token for user authentication
    
    Args:
        token: JWT token to verify
        
    Returns:
        Decoded token payload
        
    Raises:
        jwt.InvalidTokenError: If token is invalid
    """
    # Try service secrets first, then legacy
    all_secrets = {**SERVICE_JWT_SECRETS, "legacy": LEGACY_JWT_SECRET}
    
    last_exception = None
    for name, secret in all_secrets.items():
        try:
            payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
            
            # Verify token type
            if payload.get("type") != "user":
                continue

            email = _normalize_email(payload.get("email")) or _lookup_user_email(payload.get("sub"))
            if email:
                payload["email"] = email
            payload["is_admin"] = user_has_admin_access(email, bool(payload.get("is_admin")))
                 
            return payload
        except jwt.InvalidTokenError as e:
            last_exception = e
            continue
    
    raise last_exception
