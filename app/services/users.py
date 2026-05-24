"""User service - manages buyers/users."""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import User, AccessLog


def get_or_create_telegram_user(db: Session, telegram_id: str, username: str = "",
                                 first_name: str = "", last_name: str = "") -> User:
    user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
    if not user:
        user = User(
            telegram_id=str(telegram_id),
            username=username,
            first_name=first_name,
            last_name=last_name,
            role="buyer",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if username and user.username != username:
            user.username = username
        if first_name and user.first_name != first_name:
            user.first_name = first_name
        if last_name and user.last_name != last_name:
            user.last_name = last_name
        db.commit()
    return user


def confirm_age(db: Session, user: User):
    user.age_confirmed = True
    user.age_confirmed_at = datetime.utcnow()
    user.terms_accepted = True
    user.terms_accepted_at = datetime.utcnow()
    db.commit()


def ban_user(db: Session, user_id: int):
    u = db.query(User).get(user_id)
    if u:
        u.status = "banned"
        db.commit()
        log_action(db, user_id, "user_banned")


def unban_user(db: Session, user_id: int):
    u = db.query(User).get(user_id)
    if u:
        u.status = "active"
        db.commit()
        log_action(db, user_id, "user_unbanned")


def log_action(db: Session, user_id: int | None, action: str, target_type: str = "",
               target_id: int | None = None, details: str = ""):
    log = AccessLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
    )
    db.add(log)
    db.commit()
