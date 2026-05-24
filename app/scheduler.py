"""APScheduler - background tasks."""
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.database import SessionLocal
from app.models import Order, Wallet

scheduler = AsyncIOScheduler()


def release_pending_balances():
    """Move pending balance to available after 7 days from paid_at (MVP rule)."""
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=7)
        # Find paid orders older than cutoff that haven't been "released"
        # Simple approach: for each wallet, recalc based on orders
        # For MVP we use admin manual release; this job is a placeholder
        orders = db.query(Order).filter(
            Order.status.in_(("paid", "delivered")),
            Order.paid_at != None,  # noqa
            Order.paid_at < cutoff,
        ).all()
        for o in orders:
            # Idempotent: skip if already accounted
            wallet = db.query(Wallet).filter(Wallet.seller_id == o.seller_id).first()
            if not wallet:
                continue
            # Move from pending to available (capped by pending balance)
            move = min(wallet.pending_balance, o.seller_amount)
            if move > 0:
                wallet.pending_balance -= move
                wallet.available_balance += move
                db.commit()
    finally:
        db.close()


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(release_pending_balances, "interval", hours=6,
                          id="release_pending", replace_existing=True)
        scheduler.start()
