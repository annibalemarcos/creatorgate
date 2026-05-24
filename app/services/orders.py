"""Order service - handles orders, payments, commissions."""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Order, Product, Seller, User, Wallet, ModerationLog
from app.config import settings


def create_order(db: Session, buyer_id: int, product_id: int,
                 payment_method: str = "pix_manual") -> Order | None:
    product = db.query(Product).get(product_id)
    if not product or product.status != "active":
        return None
    seller = db.query(Seller).get(product.seller_id)
    if not seller or seller.status not in ("active",):
        return None
    buyer = db.query(User).get(buyer_id)
    if not buyer or buyer.status != "active":
        return None

    commission_rate = seller.commission_rate or settings.PLATFORM_COMMISSION_PERCENT
    platform_fee = round(product.price * commission_rate / 100.0, 2)
    seller_amount = round(product.price - platform_fee, 2)

    order = Order(
        buyer_id=buyer_id,
        seller_id=seller.id,
        product_id=product.id,
        amount=product.price,
        platform_fee=platform_fee,
        seller_amount=seller_amount,
        status="pending",
        payment_method=payment_method,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def mark_order_paid(db: Session, order_id: int, reference: str = ""):
    order = db.query(Order).get(order_id)
    if not order or order.status != "pending":
        return None
    order.status = "paid"
    order.paid_at = datetime.utcnow()
    if reference:
        order.payment_reference = reference

    # Add to seller pending balance
    wallet = db.query(Wallet).filter(Wallet.seller_id == order.seller_id).first()
    if not wallet:
        wallet = Wallet(seller_id=order.seller_id)
        db.add(wallet)
    wallet.pending_balance = (wallet.pending_balance or 0) + order.seller_amount
    wallet.total_earned = (wallet.total_earned or 0) + order.seller_amount
    wallet.total_commission_paid = (wallet.total_commission_paid or 0) + order.platform_fee

    # Increase product sales count
    product = db.query(Product).get(order.product_id)
    if product:
        product.sales_count = (product.sales_count or 0) + 1

    # Increase buyer total_spent
    buyer = db.query(User).get(order.buyer_id)
    if buyer:
        buyer.total_spent = (buyer.total_spent or 0) + order.amount

    db.commit()
    db.add(ModerationLog(target_type="order", target_id=order.id, action="mark_paid"))
    db.commit()
    return order


def mark_delivered(db: Session, order_id: int):
    order = db.query(Order).get(order_id)
    if not order:
        return None
    order.status = "delivered"
    order.delivered_at = datetime.utcnow()
    db.commit()
    db.add(ModerationLog(target_type="order", target_id=order.id, action="delivered"))
    db.commit()
    return order


def cancel_order(db: Session, order_id: int):
    order = db.query(Order).get(order_id)
    if not order:
        return None
    order.status = "canceled"
    db.commit()
    return order
