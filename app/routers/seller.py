"""Seller panel routes."""
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_seller
from app.config import settings
from app.models import Product, Order, Category, Wallet, Withdrawal
from app.services import products as products_svc
from app.services import wallets as wallets_svc
from app.services import withdrawals as withdrawals_svc

router = APIRouter(prefix="/seller")
templates = Jinja2Templates(directory="app/templates")


def sctx(request: Request, seller, **extra):
    base = {
        "request": request,
        "user": request.session.get("user"),
        "seller": seller,
        "active": extra.pop("active", ""),
    }
    base.update(extra)
    return base


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def seller_dashboard(request: Request, db: Session = Depends(get_db)):
    seller = require_seller(request, db)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    sales_today = db.query(func.coalesce(func.sum(Order.amount), 0)).filter(
        Order.seller_id == seller.id,
        Order.status.in_(("paid", "delivered")),
        Order.paid_at >= today_start).scalar() or 0
    sales_month = db.query(func.coalesce(func.sum(Order.amount), 0)).filter(
        Order.seller_id == seller.id,
        Order.status.in_(("paid", "delivered")),
        Order.paid_at >= month_start).scalar() or 0
    paid_orders = db.query(Order).filter(
        Order.seller_id == seller.id,
        Order.status.in_(("paid", "delivered"))).count()
    pending_withdrawals = db.query(Withdrawal).filter(
        Withdrawal.seller_id == seller.id,
        Withdrawal.status == "pending").count()
    wallet = wallets_svc.get_or_create(db, seller.id)
    active_products = db.query(Product).filter(
        Product.seller_id == seller.id, Product.status == "active").count()
    recent_sales = db.query(Order).filter(Order.seller_id == seller.id).order_by(
        Order.created_at.desc()).limit(5).all()

    stats = {
        "sales_today": sales_today,
        "sales_month": sales_month,
        "paid_orders": paid_orders,
        "pending_withdrawals": pending_withdrawals,
        "available": wallet.available_balance,
        "pending": wallet.pending_balance,
        "blocked": wallet.blocked_balance,
        "active_products": active_products,
    }
    return templates.TemplateResponse("seller/dashboard.html", sctx(
        request, seller, stats=stats, wallet=wallet, recent_sales=recent_sales,
        active="dashboard",
    ))


@router.get("/products", response_class=HTMLResponse)
def my_products(request: Request, db: Session = Depends(get_db)):
    seller = require_seller(request, db)
    products = db.query(Product).filter(Product.seller_id == seller.id).order_by(
        Product.created_at.desc()).all()
    return templates.TemplateResponse("seller/products.html", sctx(
        request, seller, products=products, active="products",
    ))


@router.get("/products/new", response_class=HTMLResponse)
def new_product_form(request: Request, db: Session = Depends(get_db)):
    seller = require_seller(request, db)
    if seller.status != "active":
        return templates.TemplateResponse("seller/products.html", sctx(
            request, seller, products=[], blocked=True, active="products",
        ))
    categories = db.query(Category).filter(Category.is_active == True).all()  # noqa
    return templates.TemplateResponse("seller/product_form.html", sctx(
        request, seller, categories=categories, product=None, active="products",
    ))


@router.post("/products/new")
async def create_product(
    request: Request,
    name: str = Form(...), description: str = Form(""),
    price: float = Form(...), category_id: int = Form(None),
    delivery_type: str = Form("texto"),
    content_text: str = Form(""), private_link: str = Form(""),
    telegram_chat_id: str = Form(""), is_adult: bool = Form(False),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    seller = require_seller(request, db)
    if seller.status != "active":
        raise HTTPException(403, "Vendedor não está ativo")

    file_path = ""
    if file and file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"Extensão {ext} não permitida")
        dest = settings.PROTECTED_DIR / f"s{seller.id}_{int(datetime.utcnow().timestamp())}{ext}"
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(400, f"Arquivo maior que {settings.MAX_UPLOAD_MB}MB")
        dest.write_bytes(content)
        file_path = str(dest)

    products_svc.create_product(
        db, seller.id,
        name=name, description=description, price=price,
        category_id=category_id if category_id else None,
        delivery_type=delivery_type, content_text=content_text,
        private_link=private_link, telegram_chat_id=telegram_chat_id,
        is_adult=is_adult, file_path=file_path,
    )
    return RedirectResponse("/api/seller/products", 303)


@router.get("/products/{pid}/edit", response_class=HTMLResponse)
def edit_product_form(pid: int, request: Request, db: Session = Depends(get_db)):
    seller = require_seller(request, db)
    p = db.query(Product).filter(Product.id == pid, Product.seller_id == seller.id).first()
    if not p:
        raise HTTPException(404)
    categories = db.query(Category).filter(Category.is_active == True).all()  # noqa
    return templates.TemplateResponse("seller/product_form.html", sctx(
        request, seller, categories=categories, product=p, active="products",
    ))


@router.post("/products/{pid}/edit")
def edit_product(pid: int, request: Request,
                 name: str = Form(...), description: str = Form(""),
                 price: float = Form(...), category_id: int = Form(None),
                 delivery_type: str = Form("texto"), content_text: str = Form(""),
                 private_link: str = Form(""), telegram_chat_id: str = Form(""),
                 is_adult: bool = Form(False),
                 db: Session = Depends(get_db)):
    seller = require_seller(request, db)
    p = db.query(Product).filter(Product.id == pid, Product.seller_id == seller.id).first()
    if not p:
        raise HTTPException(404)
    p.name = name
    p.description = description
    p.price = price
    p.category_id = category_id if category_id else None
    p.delivery_type = delivery_type
    p.content_text = content_text
    p.private_link = private_link
    p.telegram_chat_id = telegram_chat_id
    p.is_adult = is_adult
    # Re-moderate if was active and admin requires approval
    p.status = "pending"
    db.commit()
    return RedirectResponse("/api/seller/products", 303)


@router.get("/sales", response_class=HTMLResponse)
def sales(request: Request, db: Session = Depends(get_db)):
    seller = require_seller(request, db)
    orders = db.query(Order).filter(Order.seller_id == seller.id).order_by(
        Order.created_at.desc()).all()
    return templates.TemplateResponse("seller/sales.html", sctx(
        request, seller, orders=orders, active="sales",
    ))


@router.get("/wallet", response_class=HTMLResponse)
def wallet(request: Request, db: Session = Depends(get_db)):
    seller = require_seller(request, db)
    w = wallets_svc.get_or_create(db, seller.id)
    withdrawals = db.query(Withdrawal).filter(Withdrawal.seller_id == seller.id).order_by(
        Withdrawal.requested_at.desc()).all()
    return templates.TemplateResponse("seller/wallet.html", sctx(
        request, seller, wallet=w, withdrawals=withdrawals, active="wallet",
    ))


@router.post("/withdrawals/request")
def request_withdrawal(request: Request, amount: float = Form(...),
                       pix_key: str = Form(...), db: Session = Depends(get_db)):
    seller = require_seller(request, db)
    if seller.status != "active":
        raise HTTPException(403)
    withdrawals_svc.request_withdrawal(db, seller.id, amount, pix_key)
    return RedirectResponse("/api/seller/wallet", 303)


@router.get("/profile", response_class=HTMLResponse)
def profile(request: Request, db: Session = Depends(get_db)):
    seller = require_seller(request, db)
    return templates.TemplateResponse("seller/profile.html", sctx(
        request, seller, active="profile",
    ))


@router.post("/profile")
def update_profile(request: Request, store_name: str = Form(...),
                   bio: str = Form(""), pix_key: str = Form(""),
                   db: Session = Depends(get_db)):
    seller = require_seller(request, db)
    seller.store_name = store_name
    seller.bio = bio
    seller.pix_key = pix_key
    db.commit()
    return RedirectResponse("/api/seller/profile", 303)



# ============================================================================
# Tickets (seller side)
# ============================================================================
from app.services import tickets as t_svc  # noqa: E402
from app.services import notifications as notif_svc  # noqa: E402
from app.models import SupportTicket  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402


@router.get("/tickets", response_class=HTMLResponse)
def seller_tickets(request: Request, status: str = "",
                   db: Session = Depends(get_db)):
    seller = require_seller(request, db)
    items = t_svc.list_tickets(db, status=status, opener_seller_id=seller.id)
    return templates.TemplateResponse("seller/tickets.html", sctx(
        request, seller, items=items, status=status, active="tickets",
        CATEGORIES=t_svc.CATEGORIES, PRIORITIES=t_svc.PRIORITIES,
        STATUS_LABELS=t_svc.STATUS_LABELS,
    ))


@router.get("/tickets/new", response_class=HTMLResponse)
def seller_tickets_new(request: Request, error: str = "",
                       db: Session = Depends(get_db)):
    seller = require_seller(request, db)
    return templates.TemplateResponse("seller/ticket_form.html", sctx(
        request, seller, error=error, active="tickets",
        CATEGORIES=t_svc.CATEGORIES, PRIORITIES=t_svc.PRIORITIES,
    ))


@router.post("/tickets/new")
def seller_tickets_create(
    request: Request,
    subject: str = Form(...),
    category: str = Form("other"),
    priority: str = Form("normal"),
    message: str = Form(...),
    db: Session = Depends(get_db),
):
    seller = require_seller(request, db)
    if len(subject.strip()) < 3 or len(message.strip()) < 5:
        return RedirectResponse(
            "/api/seller/tickets/new?error=Preencha assunto e mensagem", 303)
    t = t_svc.create_ticket(
        db, subject=subject, category=category, priority=priority,
        opener_seller_id=seller.id, initial_message=message,
    )
    return RedirectResponse(f"/api/seller/tickets/{t.id}", 303)


@router.get("/tickets/{tid}", response_class=HTMLResponse)
def seller_ticket_detail(tid: int, request: Request,
                         db: Session = Depends(get_db)):
    seller = require_seller(request, db)
    t = db.query(SupportTicket).filter(
        SupportTicket.id == tid,
        SupportTicket.opener_seller_id == seller.id,
    ).first()
    if not t:
        raise HTTPException(404)
    # mark seller's notifications for this ticket as read
    return templates.TemplateResponse("seller/ticket_detail.html", sctx(
        request, seller, ticket=t, active="tickets",
        CATEGORIES=t_svc.CATEGORIES, PRIORITIES=t_svc.PRIORITIES,
        STATUS_LABELS=t_svc.STATUS_LABELS,
    ))


@router.post("/tickets/{tid}/reply")
def seller_ticket_reply(tid: int, request: Request,
                        content: str = Form(...),
                        db: Session = Depends(get_db)):
    seller = require_seller(request, db)
    t = db.query(SupportTicket).filter(
        SupportTicket.id == tid,
        SupportTicket.opener_seller_id == seller.id,
    ).first()
    if not t:
        raise HTTPException(404)
    if not content.strip():
        return RedirectResponse(f"/api/seller/tickets/{tid}", 303)
    try:
        t_svc.add_message(db, tid, "seller", seller.id, seller.store_name, content)
    except ValueError as e:
        return RedirectResponse(f"/api/seller/tickets/{tid}?error={e}", 303)
    return RedirectResponse(f"/api/seller/tickets/{tid}", 303)


@router.post("/tickets/{tid}/close")
def seller_ticket_close(tid: int, request: Request,
                        db: Session = Depends(get_db)):
    seller = require_seller(request, db)
    t = db.query(SupportTicket).filter(
        SupportTicket.id == tid,
        SupportTicket.opener_seller_id == seller.id,
    ).first()
    if t:
        t_svc.set_status(db, tid, "closed")
    return RedirectResponse(f"/api/seller/tickets/{tid}", 303)


# --------- Seller notifications feed (polling) ---------
@router.get("/notifications/feed")
def seller_notif_feed(request: Request, db: Session = Depends(get_db)):
    seller = require_seller(request, db)
    items = notif_svc.list_unread(db, "seller", seller.id, limit=10)
    count = notif_svc.count_unread(db, "seller", seller.id)
    return JSONResponse({
        "count": count,
        "items": [
            {"id": n.id, "kind": n.kind, "title": n.title, "body": n.body,
             "link": n.link, "created_at": n.created_at.isoformat()}
            for n in items
        ],
    })


@router.post("/notifications/{nid}/read")
def seller_notif_read(nid: int, request: Request, db: Session = Depends(get_db)):
    seller = require_seller(request, db)
    notif_svc.mark_read(db, nid, "seller", seller.id)
    return JSONResponse({"ok": True})


@router.post("/notifications/read-all")
def seller_notif_read_all(request: Request, db: Session = Depends(get_db)):
    seller = require_seller(request, db)
    notif_svc.mark_all_read(db, "seller", seller.id)
    return JSONResponse({"ok": True})
