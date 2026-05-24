"""Staff management routes - super_admin only."""
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_super_admin, ROLE_LABELS, ROLES
from app.models import StaffMember, Seller
from app.services import staff as staff_svc

router = APIRouter(prefix="/admin/staff")
templates = Jinja2Templates(directory="app/templates")


def _ctx(request, **extra):
    base = {
        "request": request,
        "user": request.session.get("user"),
        "active": "staff",
        "ROLE_LABELS": ROLE_LABELS,
        "ROLES": ROLES,
    }
    base.update(extra)
    return base


@router.get("", response_class=HTMLResponse)
def list_staff(request: Request, role: str = "", q: str = "",
               db: Session = Depends(get_db), _=Depends(require_super_admin)):
    staffs = staff_svc.list_staff(db, role=role or None, q=q)
    return templates.TemplateResponse("admin/staff.html", _ctx(
        request, staffs=staffs, role=role, q=q,
    ))


@router.get("/new", response_class=HTMLResponse)
def new_staff(request: Request, error: str = "", db: Session = Depends(get_db),
              _=Depends(require_super_admin)):
    sellers = db.query(Seller).filter(Seller.status == "active").all()
    return templates.TemplateResponse("admin/staff_form.html", _ctx(
        request, staff=None, error=error, sellers=sellers,
    ))


@router.post("/new")
def create_staff_route(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    role: str = Form(...),
    full_name: str = Form(""),
    telegram_id: str = Form(""),
    db: Session = Depends(get_db),
    _=Depends(require_super_admin),
):
    if len(password) < 8:
        return RedirectResponse(
            "/api/admin/staff/new?error=Senha mínima de 8 caracteres", 303)
    if password != password_confirm:
        return RedirectResponse(
            "/api/admin/staff/new?error=As senhas não coincidem", 303)
    try:
        staff_svc.create_staff(db, username, password, role,
                                full_name=full_name, telegram_id=telegram_id)
    except ValueError as e:
        return RedirectResponse(f"/api/admin/staff/new?error={e}", 303)
    return RedirectResponse("/api/admin/staff", 303)


@router.post("/promote")
def promote_seller_route(
    request: Request,
    seller_id: int = Form(...),
    role: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db),
    _=Depends(require_super_admin),
):
    if len(password) < 8 or password != password_confirm:
        return RedirectResponse(
            "/api/admin/staff/new?error=Senha inválida", 303)
    try:
        staff_svc.promote_seller(db, seller_id, role, password)
    except ValueError as e:
        return RedirectResponse(f"/api/admin/staff/new?error={e}", 303)
    return RedirectResponse("/api/admin/staff", 303)


@router.get("/{sid}/edit", response_class=HTMLResponse)
def edit_staff(sid: int, request: Request, error: str = "",
               db: Session = Depends(get_db), _=Depends(require_super_admin)):
    staff = db.query(StaffMember).get(sid)
    if not staff:
        raise HTTPException(404)
    return templates.TemplateResponse("admin/staff_form.html", _ctx(
        request, staff=staff, error=error, sellers=[],
    ))


@router.post("/{sid}/edit")
def update_staff_route(
    sid: int,
    request: Request,
    role: str = Form(...),
    full_name: str = Form(""),
    telegram_id: str = Form(""),
    password: str = Form(""),
    password_confirm: str = Form(""),
    db: Session = Depends(get_db),
    _=Depends(require_super_admin),
):
    fields = {"role": role, "full_name": full_name,
              "telegram_id": telegram_id.strip() or None}
    if password:
        if len(password) < 8:
            return RedirectResponse(
                f"/api/admin/staff/{sid}/edit?error=Senha mínima 8 chars", 303)
        if password != password_confirm:
            return RedirectResponse(
                f"/api/admin/staff/{sid}/edit?error=Senhas não coincidem", 303)
        fields["password"] = password
    staff_svc.update_staff(db, sid, **fields)
    return RedirectResponse("/api/admin/staff", 303)


@router.post("/{sid}/toggle")
def toggle_staff_route(sid: int, db: Session = Depends(get_db),
                       _=Depends(require_super_admin)):
    staff_svc.toggle_staff_active(db, sid)
    return RedirectResponse("/api/admin/staff", 303)


@router.post("/{sid}/delete")
def delete_staff_route(sid: int, db: Session = Depends(get_db),
                       _=Depends(require_super_admin)):
    staff_svc.delete_staff(db, sid)
    return RedirectResponse("/api/admin/staff", 303)
