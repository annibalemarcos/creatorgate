"""Wallet service."""
from sqlalchemy.orm import Session
from app.models import Wallet


def get_or_create(db: Session, seller_id: int) -> Wallet:
    w = db.query(Wallet).filter(Wallet.seller_id == seller_id).first()
    if not w:
        w = Wallet(seller_id=seller_id)
        db.add(w)
        db.commit()
        db.refresh(w)
    return w


def release_pending(db: Session, seller_id: int, amount: float | None = None):
    """Move pending balance to available. If amount=None, release all pending."""
    w = get_or_create(db, seller_id)
    move = amount if amount is not None else w.pending_balance
    move = min(move, w.pending_balance)
    if move <= 0:
        return w
    w.pending_balance -= move
    w.available_balance += move
    db.commit()
    return w


def block_balance(db: Session, seller_id: int, amount: float):
    w = get_or_create(db, seller_id)
    move = min(amount, w.available_balance)
    w.available_balance -= move
    w.blocked_balance += move
    db.commit()
    return w


def unblock_balance(db: Session, seller_id: int, amount: float | None = None):
    w = get_or_create(db, seller_id)
    move = amount if amount is not None else w.blocked_balance
    move = min(move, w.blocked_balance)
    w.blocked_balance -= move
    w.available_balance += move
    db.commit()
    return w
