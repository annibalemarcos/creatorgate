"""Admin panel routes."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_admin, require_perm
from app.models import (
    User, Seller, SellerPlan, Product, Order, Wallet, Withdrawal, Report,
    Category, Setting, ModerationLog,
)
from app.services import sellers as sellers_svc
from app.services import products as products_svc
from app.services import orders as orders_svc
from app.services import withdrawals as withdrawals_svc
from app.services import moderation as mod_svc
from app.services import wallets as wallets_svc
from app.services import users as users_svc
from app.services.delivery import deliver_order
from app.services.moderation import REASONS

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


def ctx(request: Request, **extra):
    base = {
        "request": request,
        "user": request.session.get("user"),
        "REASONS": REASONS,
        "active": extra.pop("active", ""),
    }
    base.update(extra)
    return base


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_revenue = db.query(func.coalesce(func.sum(Order.amount), 0)).filter(
        Order.status.in_(("paid", "delivered"))).scalar() or 0
    month_revenue = db.query(func.coalesce(func.sum(Order.amount), 0)).filter(
        Order.status.in_(("paid", "delivered")),
        Order.paid_at >= month_start).scalar() or 0
    platform_fee_total = db.query(func.coalesce(func.sum(Order.platform_fee), 0)).filter(
        Order.status.in_(("paid", "delivered"))).scalar() or 0

    stats = {
        "total_revenue": total_revenue,
        "month_revenue": month_revenue,
        "platform_fee_total": platform_fee_total,
        "total_sellers": db.query(Seller).count(),
        "pending_sellers": db.query(Seller).filter(Seller.status == "pending").count(),
        "active_products": db.query(Product).filter(Product.status == "active").count(),
        "pending_products": db.query(Product).filter(Product.status == "pending").count(),
        "paid_orders": db.query(Order).filter(Order.status.in_(("paid", "delivered"))).count(),
        "pending_withdrawals": db.query(Withdrawal).filter(Withdrawal.status == "pending").count(),
        "open_reports": db.query(Report).filter(Report.status == "open").count(),
        "banned_users": db.query(User).filter(User.status == "banned").count(),
    }
    recent_orders = db.query(Order).order_by(Order.created_at.desc()).limit(8).all()
    recent_sellers = db.query(Seller).order_by(Seller.created_at.desc()).limit(5).all()
    return templates.TemplateResponse("admin/dashboard.html", ctx(
        request, stats=stats, recent_orders=recent_orders, recent_sellers=recent_sellers,
        active="dashboard",
    ))


@router.get("/sellers", response_class=HTMLResponse)
def list_sellers(request: Request, status: str = "", q: str = "",
                 db: Session = Depends(get_db), _=Depends(require_admin)):
    query = db.query(Seller)
    if status:
        query = query.filter(Seller.status == status)
    if q:
        query = query.filter(Seller.store_name.ilike(f"%{q}%"))
    sellers = query.order_by(Seller.created_at.desc()).all()
    return templates.TemplateResponse("admin/sellers.html", ctx(
        request, sellers=sellers, status=status, q=q, active="sellers",
    ))


@router.post("/sellers/{sid}/approve")
def approve_seller(sid: int, db: Session = Depends(get_db), _=Depends(require_perm("sellers.moderate"))):
    sellers_svc.approve_seller(db, sid)
    return RedirectResponse("/api/admin/sellers", 303)


@router.post("/sellers/{sid}/suspend")
def suspend_seller(sid: int, reason: str = Form(""), db: Session = Depends(get_db),
                   _=Depends(require_perm("sellers.moderate"))):
    sellers_svc.suspend_seller(db, sid, reason)
    return RedirectResponse("/api/admin/sellers", 303)


@router.post("/sellers/{sid}/ban")
def ban_seller(sid: int, reason: str = Form(""), db: Session = Depends(get_db),
               _=Depends(require_perm("sellers.moderate"))):
    sellers_svc.ban_seller(db, sid, reason)
    return RedirectResponse("/api/admin/sellers", 303)


@router.post("/sellers/{sid}/reactivate")
def reactivate_seller(sid: int, db: Session = Depends(get_db), _=Depends(require_perm("sellers.moderate"))):
    sellers_svc.reactivate_seller(db, sid)
    return RedirectResponse("/api/admin/sellers", 303)


@router.post("/sellers/{sid}/commission")
def commission(sid: int, rate: float = Form(...), db: Session = Depends(get_db),
               _=Depends(require_perm("sellers.moderate"))):
    sellers_svc.update_commission(db, sid, rate)
    return RedirectResponse("/api/admin/sellers", 303)


@router.get("/products", response_class=HTMLResponse)
def list_products(request: Request, status: str = "", q: str = "",
                  db: Session = Depends(get_db), _=Depends(require_admin)):
    query = db.query(Product)
    if status:
        query = query.filter(Product.status == status)
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    products = query.order_by(Product.created_at.desc()).all()
    return templates.TemplateResponse("admin/products.html", ctx(
        request, products=products, status=status, q=q, active="products",
    ))


@router.post("/products/{pid}/approve")
def approve_product(pid: int, db: Session = Depends(get_db), _=Depends(require_perm("products.moderate"))):
    products_svc.approve_product(db, pid)
    return RedirectResponse("/api/admin/products", 303)


@router.post("/products/{pid}/reject")
def reject_product(pid: int, reason: str = Form(""), db: Session = Depends(get_db),
                   _=Depends(require_perm("products.moderate"))):
    products_svc.reject_product(db, pid, reason)
    return RedirectResponse("/api/admin/products", 303)


@router.post("/products/{pid}/suspend")
def suspend_product(pid: int, reason: str = Form(""), db: Session = Depends(get_db),
                    _=Depends(require_perm("products.moderate"))):
    products_svc.suspend_product(db, pid, reason)
    return RedirectResponse("/api/admin/products", 303)


@router.get("/orders", response_class=HTMLResponse)
def list_orders(request: Request, status: str = "", q: str = "",
                db: Session = Depends(get_db), _=Depends(require_admin)):
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)
    orders = query.order_by(Order.created_at.desc()).all()
    return templates.TemplateResponse("admin/orders.html", ctx(
        request, orders=orders, status=status, q=q, active="orders",
    ))


@router.post("/orders/{oid}/mark-paid")
def mark_paid(oid: int, db: Session = Depends(get_db), _=Depends(require_perm("orders.mark_paid"))):
    orders_svc.mark_order_paid(db, oid)
    return RedirectResponse("/api/admin/orders", 303)


@router.post("/orders/{oid}/deliver")
async def deliver(oid: int, db: Session = Depends(get_db), _=Depends(require_perm("orders.mark_paid"))):
    from app.bot import get_bot
    await deliver_order(db, oid, bot=get_bot())
    return RedirectResponse("/api/admin/orders", 303)


@router.post("/orders/{oid}/cancel")
def cancel_order(oid: int, db: Session = Depends(get_db), _=Depends(require_perm("orders.mark_paid"))):
    orders_svc.cancel_order(db, oid)
    return RedirectResponse("/api/admin/orders", 303)


@router.get("/users", response_class=HTMLResponse)
def users_list(request: Request, status: str = "", q: str = "",
               db: Session = Depends(get_db), _=Depends(require_admin)):
    query = db.query(User)
    if status:
        query = query.filter(User.status == status)
    if q:
        query = query.filter(User.username.ilike(f"%{q}%"))
    users = query.order_by(User.created_at.desc()).all()
    return templates.TemplateResponse("admin/users.html", ctx(
        request, users=users, status=status, q=q, active="users",
    ))


@router.post("/users/{uid}/ban")
def ban_user(uid: int, db: Session = Depends(get_db), _=Depends(require_perm("users.ban"))):
    users_svc.ban_user(db, uid)
    return RedirectResponse("/api/admin/users", 303)


@router.post("/users/{uid}/unban")
def unban_user(uid: int, db: Session = Depends(get_db), _=Depends(require_perm("users.ban"))):
    users_svc.unban_user(db, uid)
    return RedirectResponse("/api/admin/users", 303)


@router.get("/withdrawals", response_class=HTMLResponse)
def withdrawals(request: Request, status: str = "", db: Session = Depends(get_db),
                _=Depends(require_perm("withdrawals.view"))):
    query = db.query(Withdrawal)
    if status:
        query = query.filter(Withdrawal.status == status)
    items = query.order_by(Withdrawal.requested_at.desc()).all()
    return templates.TemplateResponse("admin/withdrawals.html", ctx(
        request, items=items, status=status, active="withdrawals",
    ))


@router.post("/withdrawals/{wid}/approve")
def approve_w(wid: int, note: str = Form(""), db: Session = Depends(get_db),
              _=Depends(require_perm("withdrawals.manage"))):
    withdrawals_svc.approve_withdrawal(db, wid, note)
    return RedirectResponse("/api/admin/withdrawals", 303)


@router.post("/withdrawals/{wid}/mark-paid")
def paid_w(wid: int, note: str = Form(""), db: Session = Depends(get_db),
           _=Depends(require_perm("withdrawals.manage"))):
    withdrawals_svc.mark_paid(db, wid, note)
    return RedirectResponse("/api/admin/withdrawals", 303)


@router.post("/withdrawals/{wid}/reject")
def reject_w(wid: int, note: str = Form(""), db: Session = Depends(get_db),
             _=Depends(require_perm("withdrawals.manage"))):
    withdrawals_svc.reject_withdrawal(db, wid, note)
    return RedirectResponse("/api/admin/withdrawals", 303)


@router.get("/reports", response_class=HTMLResponse)
def reports(request: Request, status: str = "", db: Session = Depends(get_db),
            _=Depends(require_perm("reports.view"))):
    query = db.query(Report)
    if status:
        query = query.filter(Report.status == status)
    items = query.order_by(Report.created_at.desc()).all()
    return templates.TemplateResponse("admin/reports.html", ctx(
        request, items=items, status=status, active="reports",
    ))


@router.post("/reports/{rid}/resolve")
def resolve_r(rid: int, note: str = Form(""), db: Session = Depends(get_db),
              _=Depends(require_perm("reports.resolve"))):
    mod_svc.resolve_report(db, rid, note)
    return RedirectResponse("/api/admin/reports", 303)


@router.post("/reports/{rid}/reject")
def reject_r(rid: int, note: str = Form(""), db: Session = Depends(get_db),
             _=Depends(require_perm("reports.resolve"))):
    mod_svc.reject_report(db, rid, note)
    return RedirectResponse("/api/admin/reports", 303)


@router.get("/categories", response_class=HTMLResponse)
def categories(request: Request, db: Session = Depends(get_db), _=Depends(require_perm("dashboard.view"))):
    items = db.query(Category).all()
    return templates.TemplateResponse("admin/categories.html", ctx(
        request, items=items, active="categories",
    ))


@router.post("/categories/create")
def create_cat(request: Request, name: str = Form(...), icon: str = Form("bi-tag"),
               description: str = Form(""), is_adult: bool = Form(False),
               db: Session = Depends(get_db), _=Depends(require_perm("settings.manage"))):
    if not db.query(Category).filter(Category.name == name).first():
        db.add(Category(name=name, icon=icon, description=description, is_adult=is_adult))
        db.commit()
    return RedirectResponse("/api/admin/categories", 303)


@router.post("/categories/{cid}/toggle")
def toggle_cat(cid: int, db: Session = Depends(get_db), _=Depends(require_perm("settings.manage"))):
    c = db.query(Category).get(cid)
    if c:
        c.is_active = not c.is_active
        db.commit()
    return RedirectResponse("/api/admin/categories", 303)


@router.get("/plans", response_class=HTMLResponse)
def plans(request: Request, db: Session = Depends(get_db), _=Depends(require_perm("plans.view"))):
    items = db.query(SellerPlan).all()
    return templates.TemplateResponse("admin/plans.html", ctx(
        request, items=items, active="plans",
    ))


@router.post("/plans/create")
def create_plan(name: str = Form(...), monthly_price: float = Form(0),
                commission_rate: float = Form(15), max_products: int = Form(20),
                allows_adult: bool = Form(False), db: Session = Depends(get_db),
                _=Depends(require_perm("settings.manage"))):
    db.add(SellerPlan(name=name, monthly_price=monthly_price,
                       commission_rate=commission_rate, max_products=max_products,
                       allows_adult=allows_adult))
    db.commit()
    return RedirectResponse("/api/admin/plans", 303)


@router.post("/plans/{pid}/toggle")
def toggle_plan(pid: int, db: Session = Depends(get_db), _=Depends(require_perm("settings.manage"))):
    p = db.query(SellerPlan).get(pid)
    if p:
        p.is_active = not p.is_active
        db.commit()
    return RedirectResponse("/api/admin/plans", 303)


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db), _=Depends(require_perm("settings.manage"))):
    items = {s.key: s.value for s in db.query(Setting).all()}
    return templates.TemplateResponse("admin/settings.html", ctx(
        request, items=items, active="settings",
    ))


@router.post("/settings/update")
async def update_settings_post(request: Request, db: Session = Depends(get_db),
                                _=Depends(require_perm("settings.manage"))):
    form = await request.form()
    for key, value in form.items():
        s = db.query(Setting).filter(Setting.key == key).first()
        if s:
            s.value = str(value)
        else:
            db.add(Setting(key=key, value=str(value)))
    db.commit()
    return RedirectResponse("/api/admin/settings", 303)


@router.get("/reports/logs", response_class=HTMLResponse)
def reports_logs(request: Request, db: Session = Depends(get_db), _=Depends(require_perm("reports.view"))):
    logs = db.query(ModerationLog).order_by(ModerationLog.created_at.desc()).limit(200).all()
    return templates.TemplateResponse("admin/reports.html", ctx(
        request, items=[], logs=logs, status="", active="reports",
    ))
