"""Auth routes - login/logout for sellers; separate admin login URL; seller registration."""
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.auth import (
    login_super_admin_env, login_staff, login_seller,
    logout as do_logout, hash_password, verify_password,
    touch_staff_login,
)
from app.models import Seller, SellerPlan, User
from app.services.sellers import create_seller
from app.services.staff import find_active_staff

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


MIN_PASSWORD_LEN = 8


# ---------------- Seller login (público) ----------------
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "", error: str = ""):
    return templates.TemplateResponse("login.html", {
        "request": request, "next": next, "error": error,
    })


@router.post("/login")
def login_submit(request: Request, username: str = Form(...), password: str = Form(...),
                 next: str = Form(""), db: Session = Depends(get_db)):
    """Login exclusivo de vendedor por slug + senha."""
    seller = db.query(Seller).filter(Seller.slug == username.strip().lower()).first()
    if seller and seller.seller_password_hash and verify_password(password, seller.seller_password_hash):
        if seller.status == "banned":
            return RedirectResponse("/api/login?error=Conta banida", status_code=303)
        login_seller(request, seller)
        return RedirectResponse(next or "/api/seller", status_code=303)
    return RedirectResponse("/api/login?error=Credenciais inválidas", status_code=303)


# ---------------- Cadastro de vendedor (web) ----------------
@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, error: str = "", success: str = "",
                  db: Session = Depends(get_db)):
    plans = db.query(SellerPlan).filter(SellerPlan.is_active == True).order_by(  # noqa
        SellerPlan.monthly_price).all()
    return templates.TemplateResponse("register.html", {
        "request": request, "error": error, "success": success, "plans": plans,
    })


@router.post("/register")
def register_submit(
    request: Request,
    store_name: str = Form(...),
    bio: str = Form(""),
    plan_id: int = Form(None),
    telegram_username: str = Form(""),
    password: str = Form(...),
    password_confirm: str = Form(...),
    terms: str = Form(None),
    db: Session = Depends(get_db),
):
    # Validações
    store_name = (store_name or "").strip()
    if len(store_name) < 3:
        return RedirectResponse("/api/register?error=Nome da loja deve ter pelo menos 3 caracteres",
                                status_code=303)
    if not terms:
        return RedirectResponse("/api/register?error=Você precisa aceitar os termos",
                                status_code=303)
    if len(password) < MIN_PASSWORD_LEN:
        return RedirectResponse(
            f"/api/register?error=A senha precisa ter no mínimo {MIN_PASSWORD_LEN} caracteres",
            status_code=303)
    if password != password_confirm:
        return RedirectResponse("/api/register?error=As senhas não coincidem",
                                status_code=303)

    # Cria User + Seller (status pending)
    tg_username = (telegram_username or "").lstrip("@").strip() or None
    user = User(
        telegram_id=None,
        username=tg_username,
        first_name=store_name[:40],
        role="seller",
        terms_accepted=True,
    )
    from datetime import datetime
    user.terms_accepted_at = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)

    seller = create_seller(
        db, user.id, store_name, bio=bio or "",
        plan_id=int(plan_id) if plan_id else None,
        password=password,
    )

    return RedirectResponse(
        f"/api/login?next=&error=Cadastro recebido! Loja '{seller.store_name}' (slug: {seller.slug}) está pendente de aprovação. Faça login após a aprovação.",
        status_code=303,
    )


# ---------------- Admin login (URL separada / oculta) ----------------
@router.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request, next: str = "", error: str = ""):
    return templates.TemplateResponse("admin_login.html", {
        "request": request, "next": next, "error": error,
    })


@router.post("/admin/login")
def admin_login_submit(request: Request, username: str = Form(...),
                       password: str = Form(...), next: str = Form(""),
                       db: Session = Depends(get_db)):
    # 1) Env super admin
    if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
        login_super_admin_env(request)
        return RedirectResponse(next or "/api/admin", status_code=303)
    # 2) Staff member
    staff = find_active_staff(db, username)
    if staff and verify_password(password, staff.password_hash):
        login_staff(request, staff)
        touch_staff_login(db, staff.id)
        return RedirectResponse(next or "/api/admin", status_code=303)
    return RedirectResponse("/api/admin/login?error=Credenciais inválidas", status_code=303)


# ---------------- Logout ----------------
@router.get("/logout")
def logout(request: Request):
    user = request.session.get("user") or {}
    role = user.get("role")
    do_logout(request)
    if role == "staff":
        return RedirectResponse("/api/admin/login", status_code=303)
    return RedirectResponse("/api/login", status_code=303)
