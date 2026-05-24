"""Seed initial data: admin, categories, plans, sample sellers and products."""
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import (
    User, Seller, SellerPlan, Category, Product, Wallet, Setting, StaffMember,
)
from app.auth import hash_password
from app.services.sellers import make_unique_slug


def seed():
    db: Session = SessionLocal()
    try:
        # Categories
        if db.query(Category).count() == 0:
            cats = [
                ("Textos", "bi-file-text", "Histórias, contos e escritos", False),
                ("Poesias", "bi-feather", "Versos e poesia", False),
                ("Fotos", "bi-camera", "Fotografias e ensaios", False),
                ("Vídeos", "bi-camera-video", "Conteúdo em vídeo", False),
                ("Áudios", "bi-mic", "Podcasts, áudios e narrações", False),
                ("PDFs", "bi-file-pdf", "Ebooks e documentos", False),
                ("Packs", "bi-archive", "Coletâneas e pacotes", False),
                ("Cursos", "bi-mortarboard", "Cursos e aulas", False),
                ("Assinaturas", "bi-stars", "Conteúdo recorrente", False),
                ("Adulto +18", "bi-shield-lock", "Conteúdo exclusivo +18", True),
            ]
            for name, icon, desc, is_adult in cats:
                db.add(Category(name=name, icon=icon, description=desc, is_adult=is_adult))
            db.commit()

        # Plans
        if db.query(SellerPlan).count() == 0:
            db.add(SellerPlan(name="Start", monthly_price=29.0, commission_rate=15.0,
                              max_products=20, allows_adult=False))
            db.add(SellerPlan(name="Pro", monthly_price=59.0, commission_rate=10.0,
                              max_products=100, allows_adult=True))
            db.add(SellerPlan(name="Elite", monthly_price=99.0, commission_rate=7.0,
                              max_products=-1, allows_adult=True))
            db.commit()

        # Sample sellers (pending + active)
        if db.query(Seller).count() == 0:
            # Active seller
            u1 = User(telegram_id="100001", username="creator_active",
                      first_name="Ana", last_name="Silva", role="seller",
                      age_confirmed=True, terms_accepted=True)
            db.add(u1)
            db.commit()
            plan_pro = db.query(SellerPlan).filter(SellerPlan.name == "Pro").first()
            s1 = Seller(
                user_id=u1.id,
                store_name="Loja da Ana",
                slug=make_unique_slug(db, "Loja da Ana"),
                bio="Conteúdos criativos e cursos exclusivos sobre escrita criativa.",
                status="active",
                plan_id=plan_pro.id if plan_pro else None,
                commission_rate=10.0,
                is_adult_enabled=False,
                pix_key="ana@email.com",
                seller_password_hash=hash_password("seller123"),
            )
            db.add(s1)
            db.commit()
            db.add(Wallet(seller_id=s1.id, available_balance=120.50, pending_balance=45.0,
                          total_earned=165.50))
            db.commit()

            # Pending seller
            u2 = User(telegram_id="100002", username="creator_pending",
                      first_name="Bruno", last_name="Costa", role="seller",
                      age_confirmed=True, terms_accepted=True)
            db.add(u2)
            db.commit()
            plan_start = db.query(SellerPlan).filter(SellerPlan.name == "Start").first()
            s2 = Seller(
                user_id=u2.id,
                store_name="Estúdio Bruno",
                slug=make_unique_slug(db, "Estúdio Bruno"),
                bio="Pacote de poesias e textos curtos.",
                status="pending",
                plan_id=plan_start.id if plan_start else None,
                commission_rate=15.0,
                is_adult_enabled=False,
                pix_key="",
                seller_password_hash=hash_password("seller123"),
            )
            db.add(s2)
            db.commit()
            db.add(Wallet(seller_id=s2.id))
            db.commit()

            # Sample products for active seller
            cat_textos = db.query(Category).filter(Category.name == "Textos").first()
            cat_pdf = db.query(Category).filter(Category.name == "PDFs").first()
            cat_cursos = db.query(Category).filter(Category.name == "Cursos").first()

            db.add(Product(
                seller_id=s1.id, category_id=cat_textos.id if cat_textos else None,
                name="Conto: A Última Folha",
                description="Um conto inédito sobre superação, com 12 páginas.",
                price=9.90, delivery_type="texto",
                content_text="A última folha caiu... [conteúdo completo entregue após pagamento]",
                status="active",
            ))
            db.add(Product(
                seller_id=s1.id, category_id=cat_pdf.id if cat_pdf else None,
                name="Ebook: Escrita Criativa em 7 Dias",
                description="Guia prático com exercícios diários para destravar sua escrita.",
                price=29.90, delivery_type="link",
                private_link="https://drive.google.com/exemplo",
                status="active",
            ))
            db.add(Product(
                seller_id=s1.id, category_id=cat_cursos.id if cat_cursos else None,
                name="Mini-curso: Storytelling para Iniciantes",
                description="Aulas em vídeo + apostila exclusiva. Acesso ao grupo VIP.",
                price=79.00, delivery_type="grupo_telegram",
                telegram_chat_id="@grupo_exemplo",
                status="active",
            ))
            db.add(Product(
                seller_id=s1.id, category_id=cat_textos.id if cat_textos else None,
                name="Pack: Poesias Inéditas (aguardando aprovação)",
                description="Coletânea com 30 poemas inéditos.",
                price=19.90, delivery_type="texto",
                content_text="[Conteúdo aguardando moderação]",
                status="pending",
            ))
            db.commit()

        # Staff (exemplo): moderador + suporte
        if db.query(StaffMember).count() == 0:
            db.add(StaffMember(
                username="maria-mod",
                password_hash=hash_password("staff1234"),
                full_name="Maria Moderadora",
                role="moderator",
                is_active=True,
            ))
            db.add(StaffMember(
                username="joao-suporte",
                password_hash=hash_password("staff1234"),
                full_name="João Suporte",
                role="support",
                is_active=True,
            ))
            db.add(StaffMember(
                username="paula-financeiro",
                password_hash=hash_password("staff1234"),
                full_name="Paula Financeiro",
                role="financial",
                is_active=True,
            ))
            db.commit()

        # Settings defaults
        defaults = {
            "pix_key": "",
            "pix_instructions": "Faça o Pix para a chave acima e envie o comprovante para o suporte.",
            "support_username": "@suporte_creatorgate",
            "platform_name": "CreatorGate",
        }
        for k, v in defaults.items():
            if not db.query(Setting).filter(Setting.key == k).first():
                db.add(Setting(key=k, value=v))
        db.commit()
    finally:
        db.close()
