from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Dict, Any, Optional, List
import logging

import sys
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')

from shared.jwt_utils import verify_service_token, verify_user_token, user_has_admin_access
from shared.database_models import generate_id, now_iso


workforce_router = APIRouter()
bearer = HTTPBearer(auto_error=False)
logger = logging.getLogger("workforce_ops.routes")

SHIFTS: Dict[str, Dict[str, Any]] = {}
TIMESHEETS: Dict[str, Dict[str, Any]] = {}
PAYROLL_RUNS: Dict[str, Dict[str, Any]] = {}

MAX_SHIFTS = 20000
MAX_TIMESHEETS = 50000
MAX_PAYROLL_RUNS = 10000


def _evict_oldest_dict_entries(store: Dict[str, Dict[str, Any]], max_items: int, sort_key: str = "created_at") -> None:
    if len(store) <= max_items:
        return
    over = len(store) - max_items
    ordered = sorted(store.items(), key=lambda kv: str(kv[1].get(sort_key, "")))
    for key, _ in ordered[:over]:
        store.pop(key, None)


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
        if not user_has_admin_access(payload.get("email"), bool(payload.get("is_admin"))):
            raise HTTPException(status_code=403, detail="Staff access required")
        payload["auth_type"] = "staff"
        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.debug(f"user token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


@workforce_router.get("/shifts")
async def list_shifts(token: dict = Depends(verify_staff_or_service)):
    rows = sorted(SHIFTS.values(), key=lambda r: r.get("start_at", ""))
    return {"shifts": rows, "count": len(rows)}


@workforce_router.post("/shifts")
async def create_shift(payload: dict, token: dict = Depends(verify_staff_or_service)):
    employee_id = payload.get("employee_id")
    start_at = payload.get("start_at")
    end_at = payload.get("end_at")
    if not employee_id or not start_at or not end_at:
        raise HTTPException(status_code=400, detail="employee_id, start_at and end_at are required")

    _evict_oldest_dict_entries(SHIFTS, MAX_SHIFTS)

    shift_id = generate_id()
    rec = {
        "id": shift_id,
        "employee_id": employee_id,
        "role": payload.get("role"),
        "location": payload.get("location"),
        "start_at": start_at,
        "end_at": end_at,
        "status": payload.get("status", "scheduled"),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    SHIFTS[shift_id] = rec
    return {"ok": True, "shift": rec}


@workforce_router.patch("/shifts/{shift_id}")
async def patch_shift(shift_id: str, payload: dict, token: dict = Depends(verify_staff_or_service)):
    rec = SHIFTS.get(shift_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Shift not found")
    for key in ["role", "location", "start_at", "end_at", "status"]:
        if key in payload:
            rec[key] = payload[key]
    rec["updated_at"] = now_iso()
    return {"ok": True, "shift": rec}


@workforce_router.get("/timesheets")
async def list_timesheets(token: dict = Depends(verify_staff_or_service)):
    rows = sorted(TIMESHEETS.values(), key=lambda r: r.get("date", ""), reverse=True)
    return {"timesheets": rows, "count": len(rows)}


@workforce_router.post("/timesheets")
async def create_timesheet(payload: dict, token: dict = Depends(verify_staff_or_service)):
    employee_id = payload.get("employee_id")
    date = payload.get("date")
    hours = payload.get("hours")
    if not employee_id or not date or hours is None:
        raise HTTPException(status_code=400, detail="employee_id, date and hours are required")

    try:
        hours_value = float(hours)
        overtime_value = float(payload.get("overtime_hours", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="hours and overtime_hours must be numbers")

    _evict_oldest_dict_entries(TIMESHEETS, MAX_TIMESHEETS)

    sheet_id = generate_id()
    rec = {
        "id": sheet_id,
        "employee_id": employee_id,
        "date": date,
        "hours": hours_value,
        "overtime_hours": overtime_value,
        "approved": bool(payload.get("approved", False)),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    TIMESHEETS[sheet_id] = rec
    return {"ok": True, "timesheet": rec}


@workforce_router.post("/payroll-runs")
async def create_payroll_run(payload: dict, token: dict = Depends(verify_staff_or_service)):
    period_start = payload.get("period_start")
    period_end = payload.get("period_end")
    if not period_start or not period_end:
        raise HTTPException(status_code=400, detail="period_start and period_end are required")

    try:
        gross = float(payload.get("total_gross", 0))
        net = float(payload.get("total_net", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="total_gross and total_net must be numbers")

    _evict_oldest_dict_entries(PAYROLL_RUNS, MAX_PAYROLL_RUNS)

    run_id = generate_id()
    run = {
        "id": run_id,
        "period_start": period_start,
        "period_end": period_end,
        "status": payload.get("status", "draft"),
        "total_gross": gross,
        "total_net": net,
        "line_items": payload.get("line_items", []),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    PAYROLL_RUNS[run_id] = run
    return {"ok": True, "payroll_run": run}


@workforce_router.get("/payroll-runs")
async def list_payroll_runs(token: dict = Depends(verify_staff_or_service)):
    rows = sorted(PAYROLL_RUNS.values(), key=lambda r: r.get("created_at", ""), reverse=True)
    return {"payroll_runs": rows, "count": len(rows)}
