"""
Shared database models for microservices
Contains common Pydantic models and database utility functions
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal, List
from datetime import datetime, timezone
import uuid

# Common Pydantic models that can be shared across services

class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    is_admin: bool = False
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(min_length=6)
    promo_code: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserInDB(UserBase):
    id: str
    password_hash: str
    auth_provider: str = "password"
    plan_id: Optional[str] = None
    subscription_status: str = "trial"
    subscription_started_at: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

class UserResponse(UserBase):
    id: str
    plan_id: Optional[str] = None
    subscription_status: str
    created_at: str

class TokenResponse(BaseModel):
    token: str
    user: UserResponse

class KeywordBase(BaseModel):
    value: str
    type: Literal["name", "email", "phone", "address", "other"] = "name"

class KeywordCreate(KeywordBase):
    pass

class KeywordInDB(KeywordBase):
    id: str
    user_id: str
    created_at: str
    last_scan_at: Optional[str] = None

class FindingBase(BaseModel):
    keyword_value: str
    broker: str
    url: str
    data_found: List[str]
    severity: Literal["low", "medium", "high", "critical"]
    snippet: str
    source: str
    status: str = "active"

class FindingCreate(FindingBase):
    keyword_id: str
    user_id: str

class FindingInDB(FindingBase):
    id: str
    user_id: str
    keyword_id: str
    discovered_at: str

class RemovalRequestBase(BaseModel):
    finding_id: str

class RemovalRequestCreate(RemovalRequestBase):
    pass

class RemovalRequestInDB(RemovalRequestBase):
    id: str
    user_id: str
    broker: str
    broker_email: Optional[str] = None
    broker_form: Optional[str] = None
    status: str = "submitted"
    created_at: str
    removal_requested_at: str

class PaymentBase(BaseModel):
    plan_id: str
    amount_usd: int
    method: Literal["interac", "paypal", "crypto"]
    network: Optional[Literal["ethereum", "polygon", "base"]] = None
    tx_hash: Optional[str] = None
    paypal_order_id: Optional[str] = None
    note: Optional[str] = None

class PaymentCreate(PaymentBase):
    pass

class PaymentInDB(PaymentBase):
    id: str
    user_id: str
    status: str = "pending"
    created_at: str
    instructions: Optional[dict] = None
    verification: Optional[dict] = None
    confirmed_at: Optional[str] = None
    confirmed_by: Optional[str] = None

class ProfileBase(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[Literal["US", "CA", "MX"]] = None
    state: Optional[str] = None

class ProfileCreate(ProfileBase):
    user_id: str

class ProfileInDB(ProfileBase):
    user_id: str
    updated_at: str

class SignatureBase(BaseModel):
    data_url: str  # base64 PNG image data URL from canvas
    full_name: str

class SignatureCreate(SignatureBase):
    user_id: str

class SignatureInDB(SignatureBase):
    id: str
    user_id: str
    created_at: str

class DocumentBase(BaseModel):
    template_id: Literal["dmca_takedown", "cease_and_desist", "privacy_removal_request", "right_to_be_forgotten"]
    finding_id: Optional[str] = None
    recipient_broker: Optional[str] = None
    recipient_address: Optional[str] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentInDB(DocumentBase):
    id: str
    user_id: str
    title: str
    body: str
    status: str = "draft"
    signed_at: Optional[str] = None
    signature_image: Optional[str] = None
    signed_name: Optional[str] = None
    created_at: str
    dispatched_to: Optional[str] = None
    dispatched_at: Optional[str] = None
    dispatched_document_id: Optional[str] = None

class BrokerContactBase(BaseModel):
    broker: str
    email: Optional[str] = None
    form: Optional[str] = None

class BrokerContactCreate(BrokerContactBase):
    pass

class BrokerContactInDB(BrokerContactBase):
    id: str
    updated_at: str
    updated_by: str
    created_at: str

# Database utility functions
def generate_id() -> str:
    """Generate a unique ID"""
    return str(uuid.uuid4())

def now_iso() -> str:
    """Get current timestamp in ISO format"""
    return datetime.now(timezone.utc).isoformat()

def hash_password(pw: str) -> str:
    """Hash a password using bcrypt"""
    import bcrypt
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(pw: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    import bcrypt
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False

# Pagination helper
def paginate_query(query: dict, page: int = 1, limit: int = 100) -> dict:
    """Add pagination to a MongoDB query"""
    skip = (page - 1) * limit
    return {**query, "_skip": skip, "_limit": limit}