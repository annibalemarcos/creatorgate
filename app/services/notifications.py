"""In-app notifications + Telegram push helper."""
import asyncio
import logging
from sqlalchemy.orm import Session
from app.models import Notification, StaffMember, Seller, User

logger = logging.getLogger(__name__)


def notify(db: Session, recipient_type: str, recipient_id: int,
           kind: str, title: str, body: str = "", link: str = "") -> Notification:
    n = Notification(
        recipient_type=recipient_type,
        recipient_id=recipient_id,
        kind=kind,
        title=title,
        body=body,
        link=link,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def notify_all_staff(db: Session, kind: str, title: str, body: str = "", link: str = "",
                     only_roles: list[str] | None = None):
    qs = db.query(StaffMember).filter(StaffMember.is_active == True)  # noqa
    if only_roles:
        qs = qs.filter(StaffMember.role.in_(only_roles))
    for s in qs.all():
        notify(db, "staff", s.id, kind, title, body, link)
    # also notify env super admin (id=0)
    notify(db, "staff", 0, kind, title, body, link)


def list_unread(db: Session, recipient_type: str, recipient_id: int, limit: int = 20):
    return db.query(Notification).filter(
        Notification.recipient_type == recipient_type,
        Notification.recipient_id == recipient_id,
        Notification.is_read == False,  # noqa
    ).order_by(Notification.created_at.desc()).limit(limit).all()


def count_unread(db: Session, recipient_type: str, recipient_id: int) -> int:
    return db.query(Notification).filter(
        Notification.recipient_type == recipient_type,
        Notification.recipient_id == recipient_id,
        Notification.is_read == False,  # noqa
    ).count()


def mark_read(db: Session, notif_id: int, recipient_type: str, recipient_id: int):
    n = db.query(Notification).filter(
        Notification.id == notif_id,
        Notification.recipient_type == recipient_type,
        Notification.recipient_id == recipient_id,
    ).first()
    if n:
        n.is_read = True
        db.commit()


def mark_all_read(db: Session, recipient_type: str, recipient_id: int):
    db.query(Notification).filter(
        Notification.recipient_type == recipient_type,
        Notification.recipient_id == recipient_id,
        Notification.is_read == False,  # noqa
    ).update({"is_read": True})
    db.commit()


def push_telegram(telegram_id: str | None, text: str):
    """Schedule a Telegram message to the given chat_id (if bot is running)."""
    if not telegram_id:
        return
    try:
        from app.bot import get_bot
        bot = get_bot()
        if not bot:
            return
        loop = asyncio.get_event_loop()
        loop.create_task(bot.send_message(int(telegram_id), text, parse_mode="HTML"))
    except Exception as e:
        logger.warning("Telegram push failed: %s", e)


def push_to_user(db: Session, user_id: int, text: str):
    user = db.query(User).get(user_id)
    if user and user.telegram_id:
        push_telegram(user.telegram_id, text)


def push_to_seller(db: Session, seller_id: int, text: str):
    seller = db.query(Seller).get(seller_id)
    if seller and seller.user and seller.user.telegram_id:
        push_telegram(seller.user.telegram_id, text)


def push_to_staff(db: Session, staff_id: int, text: str):
    if staff_id <= 0:
        return
    staff = db.query(StaffMember).get(staff_id)
    if staff and staff.telegram_id:
        push_telegram(staff.telegram_id, text)
