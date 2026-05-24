"""Session-based auth helpers + Role-based Access Control (RBAC) for staff."""
import hashlib
from datetime import datetime
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Seller, StaffMember


# ============================================================================
# Password hashing
# ============================================================================
def hash_password(password: str) -> str:
    salt = "creatorgate-salt"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


# ============================================================================
# Roles & permissions
# ============================================================================
ROLES = ("super_admin", "moderator", "financial", "support")

ROLE_LABELS = {
    "super_admin": "Super Admin",
    "moderator": "Moderador",
    "financial": "Financeiro",
    "support": "Suporte",
}

# Permissions per role. super_admin gets * (everything).
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "super_admin": {"*"},
    "moderator": {
        "dashboard.view",
        "sellers.view", "sellers.moderate",
        "products.view", "products.moderate",
        "users.view", "users.ban",
        "reports.view", "reports.resolve",
        "tickets.view", "tickets.reply",
        "categories.view",
        "orders.view",
    },
    "financial": {
        "dashboard.view",
        "sellers.view",
        "orders.view", "orders.mark_paid",
        "withdrawals.view", "withdrawals.manage",
        "wallets.view", "wallets.adjust",
        "tickets.view",
        "plans.view",
    },
    "support": {
        "dashboard.view",
        "sellers.view",
        "products.view",
        "orders.view",
        "users.view",
        "reports.view",
        "tickets.view", "tickets.reply", "tickets.assign",
    },
}


def has_perm(role: str, perm: str) -> bool:
    """Check if a role has a given permission."""
    if not role:
        return False
    perms = ROLE_PERMISSIONS.get(role, set())
    return "*" in perms or perm in perms


# ============================================================================
# Session helpers
# ============================================================================
def get_session_user(request: Request) -> dict | None:
    return request.session.get("user")


def login_super_admin_env(request: Request):
    """Login as the .env super admin (bootstrap)."""
    request.session["user"] = {
        "role": "staff",
        "staff_role": "super_admin",
        "staff_id": 0,  # 0 = env admin
        "username": settings.ADMIN_USERNAME,
        "full_name": "Super Admin",
    }


def login_staff(request: Request, staff: StaffMember):
    request.session["user"] = {
        "role": "staff",
        "staff_role": staff.role,
        "staff_id": staff.id,
        "username": staff.username,
        "full_name": staff.full_name or staff.username,
    }


def login_seller(request: Request, seller: Seller):
    request.session["user"] = {
        "role": "seller",
        "seller_id": seller.id,
        "store_name": seller.store_name,
        "slug": seller.slug,
    }


def logout(request: Request):
    request.session.clear()


# ============================================================================
# Route guards
# ============================================================================
def require_staff(request: Request) -> dict:
    """Any authenticated staff member (any role)."""
    user = get_session_user(request)
    if not user or user.get("role") != "staff":
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/api/admin/login?next=" + str(request.url.path)},
        )
    return user


def require_admin(request: Request) -> dict:
    """Backwards-compat alias for staff."""
    return require_staff(request)


def require_super_admin(request: Request) -> dict:
    user = require_staff(request)
    if user.get("staff_role") != "super_admin":
        raise HTTPException(status_code=403, detail="Apenas super admin pode realizar esta ação")
    return user


def require_perm(perm: str):
    """Dependency factory: requires staff with given permission."""
    def _dep(request: Request):
        user = require_staff(request)
        if not has_perm(user.get("staff_role", ""), perm):
            raise HTTPException(status_code=403,
                                detail=f"Sem permissão para '{perm}'")
        return user
    return _dep


def require_seller(request: Request, db: Session) -> Seller:
    user = get_session_user(request)
    if not user or user.get("role") != "seller":
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/api/login?next=" + str(request.url.path)},
        )
    seller = db.query(Seller).filter(Seller.id == user["seller_id"]).first()
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/api/login"},
        )
    return seller


def touch_staff_login(db: Session, staff_id: int):
    if staff_id <= 0:
        return
    s = db.query(StaffMember).get(staff_id)
    if s:
        s.last_login_at = datetime.utcnow()
        db.commit()
