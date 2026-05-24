"""Admin ticket routes - view, reply, assign, status."""
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_perm, require_staff
from app.models import SupportTicket, StaffMember
from app.services import tickets as t_svc
from app.services import notifications as notif_svc

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


def _ctx(request, **extra):
    base = {
        "request": request,
        "user": request.session.get("user"),
        "active": "tickets",
        "CATEGORIES": t_svc.CATEGORIES,
        "PRIORITIES": t_svc.PRIORITIES,
        "STATUS_LABELS": t_svc.STATUS_LABELS,
    }
    base.update(extra)
    return base


@router.get("/tickets", response_class=HTMLResponse)
def list_tickets(request: Request, status: str = "", category: str = "",
                 priority: str = "", q: str = "", mine: str = "",
                 db: Session = Depends(get_db),
                 user=Depends(require_perm("tickets.view"))):
    assigned = None
    if mine and user.get("staff_id", 0) > 0:
        assigned = user["staff_id"]
    items = t_svc.list_tickets(db, status=status, category=category,
                                priority=priority, q=q,
                                assigned_staff_id=assigned)
    return templates.TemplateResponse("admin/tickets.html", _ctx(
        request, items=items, status=status, category=category,
        priority=priority, q=q, mine=mine,
    ))


@router.get("/tickets/{tid}", response_class=HTMLResponse)
def view_ticket(tid: int, request: Request, db: Session = Depends(get_db),
                user=Depends(require_perm("tickets.view"))):
    t = db.query(SupportTicket).get(tid)
    if not t:
        raise HTTPException(404)
    staffs = db.query(StaffMember).filter(StaffMember.is_active == True).all()  # noqa
    return templates.TemplateResponse("admin/ticket_detail.html", _ctx(
        request, ticket=t, staffs=staffs,
    ))


@router.post("/tickets/{tid}/reply")
def reply_ticket(tid: int, request: Request, content: str = Form(...),
                 internal: str = Form(""),
                 db: Session = Depends(get_db),
                 user=Depends(require_perm("tickets.reply"))):
    if not content.strip():
        return RedirectResponse(f"/api/admin/tickets/{tid}", 303)
    t_svc.add_message(
        db, tid, "staff",
        sender_id=user.get("staff_id") or 0,
        sender_name=user.get("full_name") or user.get("username", "Staff"),
        content=content,
        is_internal_note=bool(internal),
    )
    return RedirectResponse(f"/api/admin/tickets/{tid}", 303)


@router.post("/tickets/{tid}/assign")
def assign_ticket(tid: int, staff_id: int = Form(0),
                  db: Session = Depends(get_db),
                  _=Depends(require_perm("tickets.view"))):
    t_svc.assign_ticket(db, tid, staff_id or None)
    return RedirectResponse(f"/api/admin/tickets/{tid}", 303)


@router.post("/tickets/{tid}/status")
def status_ticket(tid: int, status: str = Form(...),
                  db: Session = Depends(get_db),
                  _=Depends(require_perm("tickets.view"))):
    t_svc.set_status(db, tid, status)
    return RedirectResponse(f"/api/admin/tickets/{tid}", 303)


@router.post("/tickets/{tid}/priority")
def priority_ticket(tid: int, priority: str = Form(...),
                    db: Session = Depends(get_db),
                    _=Depends(require_perm("tickets.view"))):
    t_svc.set_priority(db, tid, priority)
    return RedirectResponse(f"/api/admin/tickets/{tid}", 303)


# --------- Notifications endpoints (polling-based "push") ---------
@router.get("/notifications/feed")
def notifications_feed(request: Request, db: Session = Depends(get_db),
                       user=Depends(require_staff)):
    sid = user.get("staff_id", 0)
    items = notif_svc.list_unread(db, "staff", sid, limit=10)
    count = notif_svc.count_unread(db, "staff", sid)
    return JSONResponse({
        "count": count,
        "items": [
            {"id": n.id, "kind": n.kind, "title": n.title,
             "body": n.body, "link": n.link,
             "created_at": n.created_at.isoformat()}
            for n in items
        ],
    })


@router.post("/notifications/{nid}/read")
def mark_notif_read(nid: int, request: Request, db: Session = Depends(get_db),
                    user=Depends(require_staff)):
    notif_svc.mark_read(db, nid, "staff", user.get("staff_id", 0))
    return JSONResponse({"ok": True})


@router.post("/notifications/read-all")
def mark_all(request: Request, db: Session = Depends(get_db),
             user=Depends(require_staff)):
    notif_svc.mark_all_read(db, "staff", user.get("staff_id", 0))
    return JSONResponse({"ok": True})
