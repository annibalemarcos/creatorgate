"""Moderation service - reports and auto-actions."""
from sqlalchemy.orm import Session
from app.models import Report, ModerationLog
from app.services.products import suspend_product
from app.services.wallets import block_balance

CRITICAL_REASONS = {"menor_idade", "sem_consentimento", "conteudo_ilegal"}

REASONS = {
    "conteudo_ilegal": "Conteúdo ilegal",
    "sem_consentimento": "Conteúdo sem consentimento",
    "menor_idade": "Conteúdo de menor de idade",
    "golpe": "Golpe",
    "nao_entregue": "Produto não entregue",
    "diferente": "Produto diferente do anunciado",
    "spam": "Spam",
    "outro": "Outro",
}


def create_report(db: Session, reporter_id: int | None, reason: str,
                  product_id: int | None = None, seller_id: int | None = None,
                  details: str = "") -> Report:
    severity = "critical" if reason in CRITICAL_REASONS else "medium"
    r = Report(
        reporter_id=reporter_id,
        product_id=product_id,
        seller_id=seller_id,
        reason=reason,
        details=details,
        severity=severity,
        status="open",
    )
    db.add(r)
    db.commit()
    db.refresh(r)

    # Auto-action for critical reports
    if severity == "critical":
        if product_id:
            suspend_product(db, product_id, reason=f"Auto: denúncia {reason}")
        if seller_id:
            # block ALL seller's available balance
            from app.services.wallets import get_or_create
            wallet = get_or_create(db, seller_id)
            block_balance(db, seller_id, wallet.available_balance)
        db.add(ModerationLog(
            target_type="report", target_id=r.id, action="auto_suspend",
            reason=f"Critical report: {reason}",
        ))
        db.commit()
    return r


def resolve_report(db: Session, report_id: int, note: str = ""):
    r = db.query(Report).get(report_id)
    if r:
        r.status = "resolved"
        db.commit()
        db.add(ModerationLog(target_type="report", target_id=r.id, action="resolve", reason=note))
        db.commit()
    return r


def reject_report(db: Session, report_id: int, note: str = ""):
    r = db.query(Report).get(report_id)
    if r:
        r.status = "rejected"
        db.commit()
        db.add(ModerationLog(target_type="report", target_id=r.id, action="reject", reason=note))
        db.commit()
    return r
