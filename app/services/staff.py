"""Staff management service."""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import StaffMember, Seller, ModerationLog
from app.auth import hash_password, ROLES


def create_staff(db: Session, username: str, password: str, role: str,
                 full_name: str = "", telegram_id: str = "",
                 promoted_from_seller_id: int | None = None) -> StaffMember:
    if role not in ROLES:
        raise ValueError(f"Role inválido: {role}")
    if db.query(StaffMember).filter(StaffMember.username == username).first():
        raise ValueError("Usuário já existe")
    s = StaffMember(
        username=username.strip().lower(),
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        role=role,
        telegram_id=telegram_id.strip() or None,
        promoted_from_seller_id=promoted_from_seller_id,
        is_active=True,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    _log(db, "staff", s.id, "create", f"role={role}")
    return s


def update_staff(db: Session, staff_id: int, **fields):
    s = db.query(StaffMember).get(staff_id)
    if not s:
        return None
    if "password" in fields and fields["password"]:
        s.password_hash = hash_password(fields.pop("password"))
    else:
        fields.pop("password", None)
    for k, v in fields.items():
        if hasattr(s, k):
            setattr(s, k, v)
    db.commit()
    _log(db, "staff", s.id, "update", ",".join(fields.keys()))
    return s


def toggle_staff_active(db: Session, staff_id: int) -> StaffMember | None:
    s = db.query(StaffMember).get(staff_id)
    if not s:
        return None
    s.is_active = not s.is_active
    db.commit()
    _log(db, "staff", s.id, "toggle_active", str(s.is_active))
    return s


def delete_staff(db: Session, staff_id: int) -> bool:
    s = db.query(StaffMember).get(staff_id)
    if not s:
        return False
    db.delete(s)
    db.commit()
    _log(db, "staff", staff_id, "delete")
    return True


def promote_seller(db: Session, seller_id: int, role: str,
                   password: str, username: str | None = None) -> StaffMember:
    seller = db.query(Seller).get(seller_id)
    if not seller:
        raise ValueError("Vendedor não encontrado")
    uname = (username or seller.slug).strip().lower()
    full_name = seller.store_name
    tg_id = seller.user.telegram_id if seller.user else ""
    return create_staff(db, uname, password, role, full_name=full_name,
                        telegram_id=tg_id or "",
                        promoted_from_seller_id=seller.id)


def find_active_staff(db: Session, username: str) -> StaffMember | None:
    return db.query(StaffMember).filter(
        StaffMember.username == username.strip().lower(),
        StaffMember.is_active == True,  # noqa
    ).first()


def list_staff(db: Session, role: str | None = None, q: str = "") -> list[StaffMember]:
    qs = db.query(StaffMember)
    if role:
        qs = qs.filter(StaffMember.role == role)
    if q:
        like = f"%{q}%"
        from sqlalchemy import or_
        qs = qs.filter(or_(StaffMember.username.ilike(like),
                           StaffMember.full_name.ilike(like)))
    return qs.order_by(StaffMember.created_at.desc()).all()


def _log(db: Session, target_type: str, target_id: int, action: str, reason: str = ""):
    db.add(ModerationLog(target_type=target_type, target_id=target_id,
                          action=action, reason=reason))
    db.commit()
