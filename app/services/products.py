"""Product service."""
from sqlalchemy.orm import Session
from app.models import Product, Seller, ModerationLog


def create_product(db: Session, seller_id: int, **kwargs) -> Product:
    seller = db.query(Seller).get(seller_id)
    # Always pending if seller is new (no products approved yet) OR product is adult
    requires_approval = True
    status_value = "pending"
    if seller and seller.status == "active":
        approved_count = db.query(Product).filter(
            Product.seller_id == seller_id, Product.status == "active"
        ).count()
        if approved_count >= 1 and not kwargs.get("is_adult"):
            status_value = "active"

    product = Product(
        seller_id=seller_id,
        status=status_value,
        requires_approval=requires_approval,
        **kwargs,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    _log(db, "product", product.id, "created")
    return product


def approve_product(db: Session, product_id: int):
    p = db.query(Product).get(product_id)
    if p:
        p.status = "active"
        db.commit()
        _log(db, "product", product_id, "approve")


def reject_product(db: Session, product_id: int, reason: str = ""):
    p = db.query(Product).get(product_id)
    if p:
        p.status = "rejected"
        db.commit()
        _log(db, "product", product_id, "reject", reason)


def suspend_product(db: Session, product_id: int, reason: str = ""):
    p = db.query(Product).get(product_id)
    if p:
        p.status = "suspended"
        db.commit()
        _log(db, "product", product_id, "suspend", reason)


def delete_product(db: Session, product_id: int):
    p = db.query(Product).get(product_id)
    if p:
        db.delete(p)
        db.commit()
        _log(db, "product", product_id, "delete")


def _log(db: Session, target_type: str, target_id: int, action: str, reason: str = ""):
    log = ModerationLog(target_type=target_type, target_id=target_id, action=action, reason=reason)
    db.add(log)
    db.commit()
