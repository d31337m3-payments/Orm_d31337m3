"""
Database Layer for Microservices
Handles SQLAlchemy ORM configuration and session management
"""

import logging
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, Float, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime, timezone
import json
from secrets_manager import init_infisical, get_secret, get_bool_secret

logger = logging.getLogger(__name__)

# Database URL configuration
init_infisical()
DATABASE_URL = get_secret("DATABASE_URL", "sqlite:////tmp/d31337m3.db")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    pool_pre_ping=True,
    echo=get_bool_secret("SQL_DEBUG", False)
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
    employee_number = Column(String(50), unique=True, nullable=True, index=True)
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
            "employee_number": self.employee_number,
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


class EmployeeProfile(Base):
    """Extended employee profile linked to a User."""
    __tablename__ = "employee_profiles"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, index=True, nullable=False)
    department = Column(String(100), nullable=True)
    role = Column(String(100), nullable=True)
    hire_date = Column(DateTime, nullable=True)
    pay_rate = Column(Float, nullable=True)
    pay_currency = Column(String(3), default="USD")
    is_offboarded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "department": self.department,
            "role": self.role,
            "hire_date": self.hire_date.isoformat() if self.hire_date else None,
            "pay_rate": self.pay_rate,
            "pay_currency": self.pay_currency,
            "is_offboarded": self.is_offboarded,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkforceShift(Base):
    """Shift schedule entries."""
    __tablename__ = "workforce_shifts"

    id = Column(String(36), primary_key=True, index=True)
    employee_id = Column(String(36), ForeignKey("employee_profiles.id"), index=True, nullable=False)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    role = Column(String(100), nullable=True)
    location = Column(String(200), nullable=True)
    status = Column(String(30), default="scheduled")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "start_at": self.start_at.isoformat() if self.start_at else None,
            "end_at": self.end_at.isoformat() if self.end_at else None,
            "role": self.role,
            "location": self.location,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkforceTimesheet(Base):
    """Timesheet entries for payroll."""
    __tablename__ = "workforce_timesheets"

    id = Column(String(36), primary_key=True, index=True)
    employee_id = Column(String(36), ForeignKey("employee_profiles.id"), index=True, nullable=False)
    date = Column(DateTime, nullable=False)
    hours = Column(Float, nullable=False)
    overtime_hours = Column(Float, default=0)
    approved = Column(Boolean, default=False)
    approved_by = Column(String(36), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "date": self.date.isoformat() if self.date else None,
            "hours": self.hours,
            "overtime_hours": self.overtime_hours,
            "approved": self.approved,
            "approved_by": self.approved_by,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkforcePayrollRun(Base):
    """Payroll run records."""
    __tablename__ = "workforce_payroll_runs"

    id = Column(String(36), primary_key=True, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    status = Column(String(30), default="draft")
    total_amount = Column(Float, default=0)
    line_items_json = Column(Text, nullable=True)
    approved_by = Column(String(36), nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        line_items = None
        if self.line_items_json:
            try:
                line_items = json.loads(self.line_items_json)
            except Exception:
                line_items = None
        return {
            "id": self.id,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "status": self.status,
            "total_amount": self.total_amount,
            "line_items": line_items,
            "approved_by": self.approved_by,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ShiftComment(Base):
    """Comments on shifts (employee-to-employee)."""
    __tablename__ = "shift_comments"

    id = Column(String(36), primary_key=True, index=True)
    shift_id = Column(String(36), ForeignKey("workforce_shifts.id"), index=True, nullable=False)
    author_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "shift_id": self.shift_id,
            "author_id": self.author_id,
            "text": self.text,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PayrollTimeLog(Base):
    """Auto-logged chat/queue time for payroll precision tracking."""
    __tablename__ = "payroll_time_logs"

    id = Column(String(36), primary_key=True, index=True)
    employee_id = Column(String(36), ForeignKey("employee_profiles.id"), index=True, nullable=False)
    activity_type = Column(String(50), nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Float, default=0)
    source = Column(String(50), default="chat_queue")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "activity_type": self.activity_type,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_minutes": self.duration_minutes,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    logger.info("Database tables initialized successfully")


def _run_migrations():
    """Apply column additions that create_all won't do on existing tables."""
    try:
        with engine.connect() as conn:
            conn.execute("ALTER TABLE users ADD COLUMN employee_number VARCHAR(50)")
            conn.commit()
    except Exception:
        pass  # column already exists


def drop_all_tables():
    """Drop all database tables (use with caution)"""
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")
