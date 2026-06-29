"""
Database Layer for Microservices
Handles SQLAlchemy ORM configuration and session management
"""

import os
import logging
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)

# Database URL configuration
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:////tmp/d31337m3.db"  # Default to SQLite for development
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    pool_pre_ping=True,
    echo=os.environ.get("SQL_DEBUG", "false").lower() == "true"
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Session:
    """Dependency injection for database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# SQLAlchemy ORM Models


class User(Base):
    """User model for storing user account information"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=False)
    auth_provider = Column(String(50), default="password")
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    plan_id = Column(String(36), nullable=True)
    subscription_status = Column(String(50), default="trial")
    subscription_started_at = Column(DateTime, nullable=True)
    promo_code = Column(String(50), nullable=True)
    promo_discount_percent = Column(Integer, nullable=True)
    promo_expires_at = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "is_admin": self.is_admin,
            "is_active": self.is_active,
            "plan_id": self.plan_id,
            "subscription_status": self.subscription_status,
            "subscription_started_at": self.subscription_started_at.isoformat() if self.subscription_started_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Profile(Base):
    """User profile model"""
    __tablename__ = "profiles"

    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    address = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)
    country = Column(String(2), default="CA")
    state = Column(String(50), nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "country": self.country,
            "state": self.state,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Keyword(Base):
    """Keyword model for storing user keywords to monitor"""
    __tablename__ = "keywords"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    value = Column(String(255), nullable=False)
    type = Column(String(50), default="name")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_scan_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "value": self.value,
            "type": self.type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_scan_at": self.last_scan_at.isoformat() if self.last_scan_at else None,
        }


class Finding(Base):
    """Finding model for storing detection results"""
    __tablename__ = "findings"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    keyword_id = Column(String(36), ForeignKey("keywords.id"), index=True, nullable=False)
    keyword_value = Column(String(255), nullable=False)
    broker = Column(String(100), nullable=False)
    url = Column(Text, nullable=False)
    data_found = Column(Text, nullable=False)  # JSON array as text
    severity = Column(String(20), default="medium")
    snippet = Column(Text, nullable=True)
    source = Column(String(100), nullable=False)
    status = Column(String(50), default="active")
    discovered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "keyword_id": self.keyword_id,
            "keyword_value": self.keyword_value,
            "broker": self.broker,
            "url": self.url,
            "data_found": json.loads(self.data_found) if isinstance(self.data_found, str) else self.data_found,
            "severity": self.severity,
            "snippet": self.snippet,
            "source": self.source,
            "status": self.status,
            "discovered_at": self.discovered_at.isoformat() if self.discovered_at else None,
        }


class RemovalRequest(Base):
    """Removal request model"""
    __tablename__ = "removal_requests"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    finding_id = Column(String(36), ForeignKey("findings.id"), nullable=False)
    broker = Column(String(100), nullable=False)
    broker_email = Column(String(255), nullable=True)
    broker_form = Column(Text, nullable=True)
    status = Column(String(50), default="submitted")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    removal_requested_at = Column(DateTime, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "finding_id": self.finding_id,
            "broker": self.broker,
            "broker_email": self.broker_email,
            "broker_form": self.broker_form,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "removal_requested_at": self.removal_requested_at.isoformat() if self.removal_requested_at else None,
        }


class Signature(Base):
    """Document signature model"""
    __tablename__ = "signatures"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    data_url = Column(Text, nullable=False)  # Base64 PNG data URL
    full_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserSecurity(Base):
    """Per-user auth security configuration."""
    __tablename__ = "user_security"

    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True, index=True)
    email_verified = Column(Boolean, default=True, nullable=False)
    two_fa_enabled = Column(Boolean, default=False, nullable=False)
    two_fa_method = Column(String(30), default="email", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "email_verified": self.email_verified,
            "two_fa_enabled": self.two_fa_enabled,
            "two_fa_method": self.two_fa_method,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AuthChallenge(Base):
    """Stores one-time OTP challenges for registration/login/2FA flows."""
    __tablename__ = "auth_challenges"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=True)
    email = Column(String(255), index=True, nullable=False)
    purpose = Column(String(50), index=True, nullable=False)
    otp_hash = Column(String(128), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=5, nullable=False)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        metadata = None
        if self.metadata_json:
            try:
                metadata = json.loads(self.metadata_json)
            except Exception:
                metadata = None
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email": self.email,
            "purpose": self.purpose,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "consumed_at": self.consumed_at.isoformat() if self.consumed_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "metadata": metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TrustedDevice(Base):
    """Trusted/recognized device records used for adaptive login challenges."""
    __tablename__ = "trusted_devices"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    device_id = Column(String(255), nullable=False)
    device_name = Column(String(120), nullable=True)
    trusted_until = Column(DateTime, nullable=False)
    last_seen_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "trusted_until": self.trusted_until.isoformat() if self.trusted_until else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AuthAudit(Base):
    """Append-only authentication and security audit events."""
    __tablename__ = "auth_audit"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=True)
    email = Column(String(255), index=True, nullable=True)
    event = Column(String(80), index=True, nullable=False)
    detail_json = Column(Text, nullable=True)
    ip_address = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        detail = None
        if self.detail_json:
            try:
                detail = json.loads(self.detail_json)
            except Exception:
                detail = None
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email": self.email,
            "event": self.event,
            "detail": detail,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully")


def drop_all_tables():
    """Drop all database tables (use with caution)"""
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")
