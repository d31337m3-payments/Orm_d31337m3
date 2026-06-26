#!/usr/bin/env python3
"""
Security Middleware for Microservices
Provides authentication and authorization for service-to-service communication
"""
from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt_utils import verify_service_token, verify_user_token

# Security scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def verify_service_request(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    expected_service: Optional[str] = None
) -> dict:
    """
    Verify incoming request is from an authorized service
    
    Args:
        credentials: HTTP authorization credentials
        expected_service: Optional expected service name
        
    Returns:
        Token payload if valid
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Service authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = verify_service_token(credentials.credentials, expected_service)
        return payload
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid service token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def verify_user_request(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> dict:
    """
    Verify incoming request is from an authenticated user
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Token payload if valid
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="User authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = verify_user_token(credentials.credentials)
        return payload
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid user token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_service_auth(expected_service: Optional[str] = None):
    """
    Dependency for requiring service-to-service authentication
    """
    async def auth_dependency(
        credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
    ) -> dict:
        return await verify_service_request(credentials, expected_service)
    return auth_dependency


def require_user_auth():
    """
    Dependency for requiring user authentication
    """
    async def auth_dependency(
        credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
    ) -> dict:
        return await verify_user_request(credentials)
    return auth_dependency
