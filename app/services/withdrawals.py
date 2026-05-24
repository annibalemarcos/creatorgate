"""Withdrawals service."""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Withdrawal, ModerationLog
from app.services import wallets as wallets_svc


def request_withdrawal(db: Session, seller_id: int, amount: float, pix_key: str) -> Withdrawal | None:
    w = wallets_svc.get_or_create(db, seller_id)
    if amount <= 0 or amount > w.available_balance:
        return None
    # Move funds to blocked while pending
    w.available_balance -= amount
    w.blocked_balance += amount
    wd = Withdrawal(seller_id=seller_id, amount=amount, pix_key=pix_key, status="pending")
    db.add(wd)
    db.commit()
    db.refresh(wd)
    db.add(ModerationLog(target_type="withdrawal", target_id=wd.id, action="requested"))
    db.commit()
    return wd


def approve_withdrawal(db: Session, wid: int, note: str = ""):
    wd = db.query(Withdrawal).get(wid)
    if wd and wd.status == "pending":
        wd.status = "approved"
        wd.admin_note = note
        db.commit()
        db.add(ModerationLog(target_type="withdrawal", target_id=wid, action="approve", reason=note))
        db.commit()
    return wd


def mark_paid(db: Session, wid: int, note: str = ""):
    wd = db.query(Withdrawal).get(wid)
    if wd and wd.status in ("pending", "approved"):
        wd.status = "paid"
        wd.paid_at = datetime.utcnow()
        if note:
            wd.admin_note = note
        # Subtract from blocked, add to total_withdrawn
        w = wallets_svc.get_or_create(db, wd.seller_id)
        w.blocked_balance = max(0, w.blocked_balance - wd.amount)
        w.total_withdrawn = (w.total_withdrawn or 0) + wd.amount
        db.commit()
        db.add(ModerationLog(target_type="withdrawal", target_id=wid, action="mark_paid"))
        db.commit()
    return wd


def reject_withdrawal(db: Session, wid: int, note: str = ""):
    wd = db.query(Withdrawal).get(wid)
    if wd and wd.status in ("pending", "approved"):
        wd.status = "rejected"
        wd.admin_note = note
        # Refund: move from blocked back to available
        w = wallets_svc.get_or_create(db, wd.seller_id)
        w.blocked_balance = max(0, w.blocked_balance - wd.amount)
        w.available_balance += wd.amount
        db.commit()
        db.add(ModerationLog(target_type="withdrawal", target_id=wid, action="reject", reason=note))
        db.commit()
    return wd
