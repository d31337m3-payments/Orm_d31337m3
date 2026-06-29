from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Dict, Any, Optional, List
import logging

import sys
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')

from shared.jwt_utils import verify_service_token, verify_user_token
from shared.database_models import generate_id, now_iso


support_router = APIRouter()
bearer = HTTPBearer(auto_error=False)
logger = logging.getLogger("support_hub.routes")

CHAT_SESSIONS: Dict[str, Dict[str, Any]] = {}
CHAT_MESSAGES: Dict[str, List[Dict[str, Any]]] = {}
TICKETS: Dict[str, Dict[str, Any]] = {}

MAX_CHAT_SESSIONS = 5000
MAX_MESSAGES_PER_CHAT = 1000
MAX_TICKETS = 10000
MAX_MESSAGE_LENGTH = 2000
MAX_TITLE_LENGTH = 200


def _evict_oldest_dict_entries(store: Dict[str, Dict[str, Any]], max_items: int, sort_key: str = "created_at") -> None:
    if len(store) <= max_items:
        return
    over = len(store) - max_items
    ordered = sorted(store.items(), key=lambda kv: str(kv[1].get(sort_key, "")))
    for key, _ in ordered[:over]:
        store.pop(key, None)
        if store is CHAT_SESSIONS:
            CHAT_MESSAGES.pop(key, None)


def _append_message(chat_id: str, message: Dict[str, Any]) -> None:
    bucket = CHAT_MESSAGES.setdefault(chat_id, [])
    bucket.append(message)
    if len(bucket) > MAX_MESSAGES_PER_CHAT:
        del bucket[: len(bucket) - MAX_MESSAGES_PER_CHAT]


async def verify_staff_or_service(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer),
) -> Dict[str, Any]:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    token = credentials.credentials
    try:
        payload = verify_service_token(token, None)
        payload["auth_type"] = "service"
        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.debug(f"service token verification failed: {e}")
        pass

    try:
        payload = verify_user_token(token)
        if not payload.get("is_admin"):
            raise HTTPException(status_code=403, detail="Staff access required")
        payload["auth_type"] = "staff"
        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.debug(f"user token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


@support_router.get("/chats")
async def list_chats(token: dict = Depends(verify_staff_or_service)):
    rows = sorted(CHAT_SESSIONS.values(), key=lambda r: r.get("updated_at", ""), reverse=True)
    return {"chats": rows, "count": len(rows)}


@support_router.post("/chats")
async def create_chat(payload: dict, token: dict = Depends(verify_staff_or_service)):
    customer_id = payload.get("customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="customer_id is required")

    _evict_oldest_dict_entries(CHAT_SESSIONS, MAX_CHAT_SESSIONS)

    chat_id = generate_id()
    rec = {
        "id": chat_id,
        "customer_id": customer_id,
        "status": payload.get("status", "open"),
        "priority": payload.get("priority", "normal"),
        "assigned_to": payload.get("assigned_to"),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    CHAT_SESSIONS[chat_id] = rec
    CHAT_MESSAGES[chat_id] = []
    return {"ok": True, "chat": rec}


@support_router.get("/chats/{chat_id}/messages")
async def list_messages(chat_id: str, token: dict = Depends(verify_staff_or_service)):
    if chat_id not in CHAT_SESSIONS:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"messages": CHAT_MESSAGES.get(chat_id, [])}


@support_router.post("/chats/{chat_id}/messages")
async def post_message(chat_id: str, payload: dict, token: dict = Depends(verify_staff_or_service)):
    if chat_id not in CHAT_SESSIONS:
        raise HTTPException(status_code=404, detail="Chat not found")
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    if len(text) > MAX_MESSAGE_LENGTH:
        raise HTTPException(status_code=400, detail=f"text must be <= {MAX_MESSAGE_LENGTH} chars")

    actor = token.get("sub") or token.get("iss") or "unknown"
    msg = {
        "id": generate_id(),
        "chat_id": chat_id,
        "sender": payload.get("sender") or actor,
        "text": text,
        "sent_at": now_iso(),
    }
    _append_message(chat_id, msg)
    CHAT_SESSIONS[chat_id]["updated_at"] = now_iso()
    return {"ok": True, "message": msg}


@support_router.get("/tickets")
async def list_tickets(token: dict = Depends(verify_staff_or_service)):
    rows = sorted(TICKETS.values(), key=lambda r: r.get("updated_at", ""), reverse=True)
    return {"tickets": rows, "count": len(rows)}


@support_router.post("/tickets")
async def create_ticket(payload: dict, token: dict = Depends(verify_staff_or_service)):
    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    if len(title) > MAX_TITLE_LENGTH:
        raise HTTPException(status_code=400, detail=f"title must be <= {MAX_TITLE_LENGTH} chars")

    _evict_oldest_dict_entries(TICKETS, MAX_TICKETS)

    ticket_id = generate_id()
    rec = {
        "id": ticket_id,
        "customer_id": payload.get("customer_id"),
        "title": title,
        "description": payload.get("description", ""),
        "status": payload.get("status", "open"),
        "priority": payload.get("priority", "normal"),
        "assigned_to": payload.get("assigned_to"),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    TICKETS[ticket_id] = rec
    return {"ok": True, "ticket": rec}


@support_router.patch("/tickets/{ticket_id}")
async def patch_ticket(ticket_id: str, payload: dict, token: dict = Depends(verify_staff_or_service)):
    rec = TICKETS.get(ticket_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Ticket not found")

    for key in ["status", "priority", "assigned_to", "title", "description"]:
        if key in payload:
            rec[key] = payload[key]
    rec["updated_at"] = now_iso()
    return {"ok": True, "ticket": rec}
