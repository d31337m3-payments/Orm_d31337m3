#!/usr/bin/env python3
"""
JWT Utility Service for Microservices Authentication
Handles service-to-service authentication using JWT tokens
"""
import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

# Service-specific JWT secrets (in production, these would come from a secure vault)
SERVICE_JWT_SECRETS = {
    "client_index": os.environ.get("CLIENT_INDEX_JWT_SECRET", "client_index_secret_change_in_prod"),
    "payments": os.environ.get("PAYMENTS_JWT_SECRET", "payments_secret_change_in_prod"),
    "data_handling": os.environ.get("DATA_HANDLING_JWT_SECRET", "data_handling_secret_change_in_prod"),
    "auditor": os.environ.get("AUDITOR_JWT_SECRET", "auditor_secret_change_in_prod"),
    "watchdog": os.environ.get("WATCHDOG_JWT_SECRET", "watchdog_secret_change_in_prod"),
    "orchestrator": os.environ.get("ORCHESTRATOR_JWT_SECRET", "orchestrator_secret_change_in_prod"),
}

# Shared secret for backward compatibility with existing frontend
LEGACY_JWT_SECRET = os.environ.get("JWT_SECRET", "your_jwt_secret_here_change_this_in_production")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
TOKEN_EXP_MIN = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))


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


def create_user_token(user_id: str, is_admin: bool = False, service_name: str = "legacy") -> str:
    """
    Create a JWT token for user authentication (backward compatibility)
    
    Args:
        user_id: User identifier
        is_admin: Whether user is admin
        service_name: Service creating the token (for tracking)
        
    Returns:
        JWT token string
    """
    payload = {
        "sub": user_id,
        "is_admin": is_admin,
        "iss": service_name,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXP_MIN),
        "type": "user"
    }
    
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
                
            return payload
        except jwt.InvalidTokenError as e:
            last_exception = e
            continue
    
    raise last_exception
