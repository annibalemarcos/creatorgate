"""Public routes - homepage, store pages, product pages."""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Seller, Product, Category
from app.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    sellers = db.query(Seller).filter(Seller.status == "active").limit(8).all()
    products = db.query(Product).filter(Product.status == "active").order_by(
        Product.created_at.desc()).limit(12).all()
    top = db.query(Product).filter(Product.status == "active").order_by(
        Product.sales_count.desc()).limit(6).all()
    categories = db.query(Category).filter(Category.is_active == True).all()  # noqa
    return templates.TemplateResponse("public/index.html", {
        "request": request,
        "sellers": sellers, "products": products, "top": top,
        "categories": categories, "settings": settings,
    })


@router.get("/s/{slug}", response_class=HTMLResponse)
def store_page(slug: str, request: Request, db: Session = Depends(get_db)):
    seller = db.query(Seller).filter(Seller.slug == slug, Seller.status == "active").first()
    if not seller:
        raise HTTPException(404, "Loja não encontrada")
    products = db.query(Product).filter(
        Product.seller_id == seller.id, Product.status == "active",
    ).all()
    return templates.TemplateResponse("public/store.html", {
        "request": request, "seller": seller, "products": products, "settings": settings,
    })


@router.get("/p/{pid}", response_class=HTMLResponse)
def product_page(pid: int, request: Request, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == pid, Product.status == "active").first()
    if not p:
        raise HTTPException(404, "Produto não encontrado")
    return templates.TemplateResponse("public/product.html", {
        "request": request, "product": p, "settings": settings,
    })
