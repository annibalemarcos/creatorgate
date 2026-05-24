"""SQLAlchemy models for CreatorGate."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
)
from sqlalchemy.orm import relationship
from app.database import Base


def now_utc():
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(64), unique=True, index=True, nullable=True)
    username = Column(String(128), nullable=True)
    first_name = Column(String(128), nullable=True)
    last_name = Column(String(128), nullable=True)
    role = Column(String(20), default="buyer")  # buyer | seller | admin
    status = Column(String(20), default="active")  # active | banned | blocked
    age_confirmed = Column(Boolean, default=False)
    age_confirmed_at = Column(DateTime, nullable=True)
    terms_accepted = Column(Boolean, default=False)
    terms_accepted_at = Column(DateTime, nullable=True)
    total_spent = Column(Float, default=0.0)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    seller = relationship("Seller", back_populates="user", uselist=False)
    orders = relationship("Order", back_populates="buyer", foreign_keys="Order.buyer_id")


class SellerPlan(Base):
    __tablename__ = "seller_plans"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    monthly_price = Column(Float, default=0.0)
    commission_rate = Column(Float, default=15.0)
    max_products = Column(Integer, default=20)  # -1 means unlimited
    allows_adult = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_utc)


class Seller(Base):
    __tablename__ = "sellers"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    store_name = Column(String(120), nullable=False)
    slug = Column(String(120), unique=True, index=True, nullable=False)
    bio = Column(Text, default="")
    status = Column(String(20), default="pending")  # pending | active | suspended | banned
    plan_id = Column(Integer, ForeignKey("seller_plans.id"), nullable=True)
    commission_rate = Column(Float, default=15.0)  # overrides plan rate when set
    is_adult_enabled = Column(Boolean, default=False)
    pix_key = Column(String(255), default="")
    seller_password_hash = Column(String(255), nullable=True)  # for web panel login
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now_utc)

    user = relationship("User", back_populates="seller")
    plan = relationship("SellerPlan")
    products = relationship("Product", back_populates="seller")
    wallet = relationship("Wallet", back_populates="seller", uselist=False)


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True, nullable=False)
    icon = Column(String(40), default="bi-tag")
    description = Column(Text, default="")
    is_adult = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    price = Column(Float, default=0.0)
    product_type = Column(String(20), default="avulso")  # avulso | assinatura | acesso_grupo
    delivery_type = Column(String(20), default="texto")  # texto | arquivo | link | grupo_telegram
    content_text = Column(Text, default="")
    file_path = Column(String(500), default="")
    private_link = Column(String(500), default="")
    telegram_chat_id = Column(String(64), default="")
    cover_image = Column(String(500), default="")
    is_adult = Column(Boolean, default=False)
    status = Column(String(20), default="pending")  # pending | active | rejected | suspended
    requires_approval = Column(Boolean, default=True)
    sales_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    seller = relationship("Seller", back_populates="products")
    category = relationship("Category")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    amount = Column(Float, default=0.0)
    platform_fee = Column(Float, default=0.0)
    seller_amount = Column(Float, default=0.0)
    status = Column(String(20), default="pending")  # pending | paid | delivered | canceled | refunded
    payment_method = Column(String(30), default="pix_manual")  # pix_manual | mercado_pago | telegram_stars
    payment_reference = Column(String(255), default="")
    paid_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now_utc)

    buyer = relationship("User", foreign_keys=[buyer_id])
    seller = relationship("Seller")
    product = relationship("Product")


class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"), unique=True, nullable=False)
    available_balance = Column(Float, default=0.0)
    pending_balance = Column(Float, default=0.0)
    blocked_balance = Column(Float, default=0.0)
    total_earned = Column(Float, default=0.0)
    total_withdrawn = Column(Float, default=0.0)
    total_commission_paid = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    seller = relationship("Seller", back_populates="wallet")


class Withdrawal(Base):
    __tablename__ = "withdrawals"
    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    pix_key = Column(String(255), default="")
    status = Column(String(20), default="pending")  # pending | approved | paid | rejected
    admin_note = Column(Text, default="")
    requested_at = Column(DateTime, default=now_utc)
    paid_at = Column(DateTime, nullable=True)

    seller = relationship("Seller")


class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    reason = Column(String(80), nullable=False)
    details = Column(Text, default="")
    severity = Column(String(20), default="medium")  # low | medium | high | critical
    status = Column(String(20), default="open")  # open | reviewing | resolved | rejected
    created_at = Column(DateTime, default=now_utc)

    reporter = relationship("User", foreign_keys=[reporter_id])
    seller = relationship("Seller")
    product = relationship("Product")


class ModerationLog(Base):
    __tablename__ = "moderation_logs"
    id = Column(Integer, primary_key=True)
    admin_id = Column(String(64), default="admin")
    target_type = Column(String(40))  # seller | product | order | user | withdrawal | report
    target_id = Column(Integer)
    action = Column(String(80))
    reason = Column(Text, default="")
    created_at = Column(DateTime, default=now_utc)


class AccessLog(Base):
    __tablename__ = "access_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(80))
    target_type = Column(String(40), default="")
    target_id = Column(Integer, nullable=True)
    details = Column(Text, default="")
    created_at = Column(DateTime, default=now_utc)


class Setting(Base):
    __tablename__ = "settings"
    key = Column(String(80), primary_key=True)
    value = Column(Text, default="")
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)


# ============================================================================
# Staff system — different roles with different permissions
# ============================================================================
class StaffMember(Base):
    __tablename__ = "staff_members"
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(160), default="")
    role = Column(String(40), default="support")  # super_admin | moderator | financial | support
    telegram_id = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=True)
    promoted_from_seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=True)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)
    last_login_at = Column(DateTime, nullable=True)


# ============================================================================
# Support tickets
# ============================================================================
class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id = Column(Integer, primary_key=True)
    ticket_number = Column(String(20), unique=True, index=True, nullable=False)
    # Opener: a buyer (User.id) OR a seller (Seller.id) — exactly one of them
    opener_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    opener_seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=True)
    subject = Column(String(200), nullable=False)
    category = Column(String(40), default="other")  # payment | delivery | product | seller | account | other
    priority = Column(String(20), default="normal")  # low | normal | high | urgent
    status = Column(String(20), default="open")  # open | pending | answered | closed
    assigned_staff_id = Column(Integer, ForeignKey("staff_members.id"), nullable=True)
    related_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    related_product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)
    last_reply_at = Column(DateTime, default=now_utc)
    closed_at = Column(DateTime, nullable=True)

    opener_user = relationship("User", foreign_keys=[opener_user_id])
    opener_seller = relationship("Seller", foreign_keys=[opener_seller_id])
    assigned_staff = relationship("StaffMember", foreign_keys=[assigned_staff_id])
    messages = relationship("TicketMessage", back_populates="ticket",
                            cascade="all, delete-orphan",
                            order_by="TicketMessage.created_at")


class TicketMessage(Base):
    __tablename__ = "ticket_messages"
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False)
    sender_type = Column(String(20), nullable=False)  # user | seller | staff | system
    sender_id = Column(Integer, nullable=True)        # id depending on sender_type
    sender_name = Column(String(160), default="")
    content = Column(Text, nullable=False)
    is_internal_note = Column(Boolean, default=False)  # internal staff note
    created_at = Column(DateTime, default=now_utc)

    ticket = relationship("SupportTicket", back_populates="messages")


# ============================================================================
# Notifications (in-panel push + bot push)
# ============================================================================
class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    recipient_type = Column(String(20), nullable=False)  # staff | seller | user
    recipient_id = Column(Integer, nullable=False)
    kind = Column(String(40), default="info")  # ticket_reply | ticket_new | order_paid | seller_pending | ...
    title = Column(String(200), nullable=False)
    body = Column(Text, default="")
    link = Column(String(500), default="")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now_utc)
