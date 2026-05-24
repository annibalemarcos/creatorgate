"""Support ticket service."""
import secrets
import string
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models import (
    SupportTicket, TicketMessage, User, Seller, StaffMember,
)
from app.services.notifications import (
    notify, notify_all_staff, push_to_user, push_to_seller, push_to_staff,
)


CATEGORIES = {
    "payment": "Pagamento",
    "delivery": "Entrega / Acesso",
    "product": "Problema com produto",
    "seller": "Sobre o vendedor",
    "account": "Conta / Cadastro",
    "other": "Outro",
}

PRIORITIES = {
    "low": "Baixa",
    "normal": "Normal",
    "high": "Alta",
    "urgent": "Urgente",
}

STATUS_LABELS = {
    "open": "Aberto",
    "pending": "Aguardando usuário",
    "answered": "Respondido",
    "closed": "Fechado",
}


def _new_number() -> str:
    return "T-" + "".join(secrets.choice(string.digits) for _ in range(6))


def create_ticket(
    db: Session, *,
    subject: str, category: str = "other", priority: str = "normal",
    opener_user_id: int | None = None, opener_seller_id: int | None = None,
    initial_message: str = "",
    related_order_id: int | None = None,
    related_product_id: int | None = None,
) -> SupportTicket:
    if not opener_user_id and not opener_seller_id:
        raise ValueError("Ticket precisa ter um abridor (user ou seller)")

    number = _new_number()
    while db.query(SupportTicket).filter(SupportTicket.ticket_number == number).first():
        number = _new_number()

    t = SupportTicket(
        ticket_number=number,
        subject=subject.strip()[:200] or "Sem assunto",
        category=category if category in CATEGORIES else "other",
        priority=priority if priority in PRIORITIES else "normal",
        status="open",
        opener_user_id=opener_user_id,
        opener_seller_id=opener_seller_id,
        related_order_id=related_order_id,
        related_product_id=related_product_id,
        last_reply_at=datetime.utcnow(),
    )
    db.add(t)
    db.commit()
    db.refresh(t)

    # Initial message
    if initial_message:
        sender_name = ""
        if opener_user_id:
            u = db.query(User).get(opener_user_id)
            sender_name = (u.first_name or u.username or f"Usuário #{u.id}") if u else "Usuário"
            sender_type = "user"
            sender_id = opener_user_id
        else:
            s = db.query(Seller).get(opener_seller_id)
            sender_name = s.store_name if s else "Vendedor"
            sender_type = "seller"
            sender_id = opener_seller_id
        add_message(db, t.id, sender_type, sender_id, sender_name,
                    initial_message, notify_recipient=False)

    # Notify all staff (support+moderator) + super admin
    notify_all_staff(
        db, kind="ticket_new",
        title=f"Novo ticket #{t.ticket_number}",
        body=f"[{CATEGORIES.get(t.category, t.category)}] {t.subject}",
        link=f"/api/admin/tickets/{t.id}",
        only_roles=["super_admin", "moderator", "support"],
    )
    return t


def add_message(
    db: Session, ticket_id: int,
    sender_type: str, sender_id: int | None, sender_name: str,
    content: str, is_internal_note: bool = False,
    notify_recipient: bool = True,
) -> TicketMessage:
    t = db.query(SupportTicket).get(ticket_id)
    if not t:
        raise ValueError("Ticket não encontrado")
    if t.status == "closed":
        raise ValueError("Ticket fechado")

    msg = TicketMessage(
        ticket_id=ticket_id,
        sender_type=sender_type,
        sender_id=sender_id,
        sender_name=sender_name[:160],
        content=content.strip()[:5000],
        is_internal_note=is_internal_note,
    )
    db.add(msg)
    t.last_reply_at = datetime.utcnow()

    # Status transitions
    if not is_internal_note:
        if sender_type == "staff":
            t.status = "answered"
        else:
            t.status = "open"
    db.commit()
    db.refresh(msg)

    if notify_recipient and not is_internal_note:
        _push_recipients(db, t, msg)
    return msg


def _push_recipients(db: Session, ticket: SupportTicket, msg: TicketMessage):
    """Send notification + Telegram push to relevant parties."""
    if msg.sender_type == "staff":
        # Notify the opener (user or seller)
        title = f"Resposta no ticket {ticket.ticket_number}"
        body = msg.content[:200]
        if ticket.opener_user_id:
            link = "https://t.me/"  # bot handles "minhas conversas"
            notify(db, "user", ticket.opener_user_id, "ticket_reply", title, body, link)
            push_to_user(
                db, ticket.opener_user_id,
                f"💬 <b>{title}</b>\n\n<b>Assunto:</b> {ticket.subject}\n\n"
                f"<b>Suporte respondeu:</b>\n{msg.content[:1000]}\n\n"
                f"Use /suporte no bot para responder.",
            )
        elif ticket.opener_seller_id:
            link = f"/api/seller/tickets/{ticket.id}"
            notify(db, "seller", ticket.opener_seller_id, "ticket_reply",
                   title, body, link)
            push_to_seller(
                db, ticket.opener_seller_id,
                f"💬 <b>{title}</b>\n\n<b>Assunto:</b> {ticket.subject}\n\n"
                f"{msg.content[:1000]}\n\n"
                f"Acesse o painel para responder.",
            )
    else:
        # User/seller replied → notify assigned staff or all support
        title = f"Nova mensagem no ticket {ticket.ticket_number}"
        body = msg.content[:200]
        link = f"/api/admin/tickets/{ticket.id}"
        if ticket.assigned_staff_id:
            notify(db, "staff", ticket.assigned_staff_id, "ticket_reply",
                   title, body, link)
            push_to_staff(db, ticket.assigned_staff_id,
                          f"💬 {title}\n{ticket.subject}\n{msg.content[:500]}")
        else:
            notify_all_staff(db, kind="ticket_reply", title=title, body=body, link=link,
                             only_roles=["super_admin", "moderator", "support"])


def assign_ticket(db: Session, ticket_id: int, staff_id: int | None):
    t = db.query(SupportTicket).get(ticket_id)
    if not t:
        return None
    t.assigned_staff_id = staff_id if staff_id and staff_id > 0 else None
    db.commit()
    return t


def set_status(db: Session, ticket_id: int, status: str):
    t = db.query(SupportTicket).get(ticket_id)
    if not t:
        return None
    t.status = status
    if status == "closed":
        t.closed_at = datetime.utcnow()
    db.commit()
    return t


def set_priority(db: Session, ticket_id: int, priority: str):
    t = db.query(SupportTicket).get(ticket_id)
    if t and priority in PRIORITIES:
        t.priority = priority
        db.commit()
    return t


def list_tickets(db: Session, *, status: str = "", category: str = "",
                 priority: str = "", q: str = "",
                 opener_seller_id: int | None = None,
                 opener_user_id: int | None = None,
                 assigned_staff_id: int | None = None,
                 limit: int = 200):
    qs = db.query(SupportTicket)
    if status:
        qs = qs.filter(SupportTicket.status == status)
    if category:
        qs = qs.filter(SupportTicket.category == category)
    if priority:
        qs = qs.filter(SupportTicket.priority == priority)
    if opener_seller_id is not None:
        qs = qs.filter(SupportTicket.opener_seller_id == opener_seller_id)
    if opener_user_id is not None:
        qs = qs.filter(SupportTicket.opener_user_id == opener_user_id)
    if assigned_staff_id is not None:
        qs = qs.filter(SupportTicket.assigned_staff_id == assigned_staff_id)
    if q:
        like = f"%{q}%"
        qs = qs.filter(or_(
            SupportTicket.subject.ilike(like),
            SupportTicket.ticket_number.ilike(like),
        ))
    return qs.order_by(SupportTicket.last_reply_at.desc()).limit(limit).all()
