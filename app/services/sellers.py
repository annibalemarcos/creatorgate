"""Seller service."""
import re
import unicodedata
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Seller, Wallet, SellerPlan, ModerationLog
from app.services.users import log_action


def slugify(text: str) -> str:
    # transliterate accents: 'Estúdio' -> 'Estudio'
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:80] or "loja"


def make_unique_slug(db: Session, base: str) -> str:
    slug = slugify(base)
    counter = 1
    final = slug
    while db.query(Seller).filter(Seller.slug == final).first():
        counter += 1
        final = f"{slug}-{counter}"
    return final


def create_seller(db: Session, user_id: int, store_name: str, bio: str = "",
                  plan_id: int | None = None, password: str | None = None) -> Seller:
    plan = db.query(SellerPlan).get(plan_id) if plan_id else None
    if not plan:
        plan = db.query(SellerPlan).filter(SellerPlan.is_active == True).first()  # noqa
    from app.auth import hash_password
    seller = Seller(
        user_id=user_id,
        store_name=store_name,
        slug=make_unique_slug(db, store_name),
        bio=bio,
        plan_id=plan.id if plan else None,
        commission_rate=plan.commission_rate if plan else 15.0,
        is_adult_enabled=False,
        status="pending",
        seller_password_hash=hash_password(password) if password else None,
    )
    db.add(seller)
    db.commit()
    db.refresh(seller)
    # create wallet
    wallet = Wallet(seller_id=seller.id)
    db.add(wallet)
    db.commit()
    log_action(db, user_id, "seller_created", "seller", seller.id)
    return seller


def approve_seller(db: Session, seller_id: int):
    s = db.query(Seller).get(seller_id)
    if s:
        s.status = "active"
        s.approved_at = datetime.utcnow()
        db.commit()
        _log_mod(db, "seller", seller_id, "approve")


def suspend_seller(db: Session, seller_id: int, reason: str = ""):
    s = db.query(Seller).get(seller_id)
    if s:
        s.status = "suspended"
        db.commit()
        _log_mod(db, "seller", seller_id, "suspend", reason)


def ban_seller(db: Session, seller_id: int, reason: str = ""):
    s = db.query(Seller).get(seller_id)
    if s:
        s.status = "banned"
        db.commit()
        _log_mod(db, "seller", seller_id, "ban", reason)


def reactivate_seller(db: Session, seller_id: int):
    s = db.query(Seller).get(seller_id)
    if s:
        s.status = "active"
        db.commit()
        _log_mod(db, "seller", seller_id, "reactivate")


def update_commission(db: Session, seller_id: int, rate: float):
    s = db.query(Seller).get(seller_id)
    if s:
        s.commission_rate = rate
        db.commit()
        _log_mod(db, "seller", seller_id, "update_commission", f"new rate: {rate}")


def _log_mod(db: Session, target_type: str, target_id: int, action: str, reason: str = ""):
    log = ModerationLog(target_type=target_type, target_id=target_id, action=action, reason=reason)
    db.add(log)
    db.commit()
