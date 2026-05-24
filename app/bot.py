"""Aiogram Telegram bot for CreatorGate."""
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.database import SessionLocal
from app.models import Seller, Product, Order, User, Setting
from app.services.users import get_or_create_telegram_user, confirm_age, log_action
from app.services.orders import create_order
from app.services.moderation import create_report, REASONS
from app.services.telegram_access import parse_start_payload

logger = logging.getLogger(__name__)

bot: Bot | None = None
dp: Dispatcher = Dispatcher(storage=MemoryStorage())


class SellerSignup(StatesGroup):
    waiting_store_name = State()
    waiting_bio = State()
    waiting_password = State()
    waiting_password_confirm = State()


class TicketFlow(StatesGroup):
    choosing_category = State()
    typing_subject = State()
    typing_message = State()
    replying = State()


def main_menu_kb():
    kb = [
        [InlineKeyboardButton(text="🛍 Ver lojas", callback_data="list_sellers")],
        [InlineKeyboardButton(text="🔥 Mais vendidos", callback_data="list_top"),
         InlineKeyboardButton(text="🆕 Novidades", callback_data="list_new")],
        [InlineKeyboardButton(text="🔎 Buscar", callback_data="search"),
         InlineKeyboardButton(text="📦 Minhas compras", callback_data="my_orders")],
        [InlineKeyboardButton(text="💰 Quero vender", callback_data="become_seller")],
        [InlineKeyboardButton(text="🆘 Suporte", callback_data="support")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


async def show_main_menu(target, user_first: str = ""):
    text = (
        f"👋 Olá {user_first or 'criador'}! Bem-vindo ao <b>CreatorGate</b>.\n\n"
        "Marketplace de conteúdos digitais. Escolha uma opção:"
    )
    if isinstance(target, Message):
        await target.answer(text, reply_markup=main_menu_kb())
    else:
        await target.message.edit_text(text, reply_markup=main_menu_kb())


@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    db = SessionLocal()
    try:
        user = get_or_create_telegram_user(
            db, str(message.from_user.id), message.from_user.username or "",
            message.from_user.first_name or "", message.from_user.last_name or "",
        )
        payload = parse_start_payload(command.args or "")
        if payload["type"] == "product":
            await show_product(message, db, payload["id"])
            return
        if payload["type"] == "seller":
            await show_seller(message, db, payload["slug"])
            return
        await show_main_menu(message, user.first_name)
    finally:
        db.close()


@dp.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    await show_main_menu(message, message.from_user.first_name or "")


@dp.callback_query(F.data == "list_sellers")
async def cb_list_sellers(cb: CallbackQuery):
    db = SessionLocal()
    try:
        sellers = db.query(Seller).filter(Seller.status == "active").limit(20).all()
        if not sellers:
            await cb.message.edit_text("Nenhuma loja ativa no momento.",
                                       reply_markup=back_kb())
            return
        kb = [[InlineKeyboardButton(text=f"🏪 {s.store_name}",
                                    callback_data=f"seller_{s.id}")] for s in sellers]
        kb.append([InlineKeyboardButton(text="⬅️ Voltar", callback_data="main_menu")])
        await cb.message.edit_text("🛍 <b>Lojas ativas</b>:",
                                   reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    finally:
        db.close()


@dp.callback_query(F.data == "list_top")
async def cb_top(cb: CallbackQuery):
    db = SessionLocal()
    try:
        prods = db.query(Product).filter(Product.status == "active").order_by(
            Product.sales_count.desc()).limit(10).all()
        await _list_products(cb, prods, "🔥 Mais vendidos")
    finally:
        db.close()


@dp.callback_query(F.data == "list_new")
async def cb_new(cb: CallbackQuery):
    db = SessionLocal()
    try:
        prods = db.query(Product).filter(Product.status == "active").order_by(
            Product.created_at.desc()).limit(10).all()
        await _list_products(cb, prods, "🆕 Novidades")
    finally:
        db.close()


async def _list_products(cb: CallbackQuery, prods, title: str):
    if not prods:
        await cb.message.edit_text(f"{title}\n\nNada por aqui ainda.", reply_markup=back_kb())
        return
    kb = [[InlineKeyboardButton(
        text=f"📦 {p.name} — R$ {p.price:.2f}",
        callback_data=f"prod_{p.id}")] for p in prods]
    kb.append([InlineKeyboardButton(text="⬅️ Voltar", callback_data="main_menu")])
    await cb.message.edit_text(f"<b>{title}</b>",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@dp.callback_query(F.data.startswith("seller_"))
async def cb_seller_view(cb: CallbackQuery):
    sid = int(cb.data.split("_", 1)[1])
    db = SessionLocal()
    try:
        s = db.query(Seller).get(sid)
        if not s or s.status != "active":
            await cb.answer("Loja indisponível", show_alert=True)
            return
        prods = db.query(Product).filter(
            Product.seller_id == s.id, Product.status == "active",
        ).all()
        text = f"🏪 <b>{s.store_name}</b>\n\n{s.bio or ''}\n\n"
        text += f"📦 {len(prods)} produtos ativos"
        kb = [[InlineKeyboardButton(text=f"📦 {p.name} — R$ {p.price:.2f}",
                                    callback_data=f"prod_{p.id}")] for p in prods[:15]]
        kb.append([InlineKeyboardButton(text="⬅️ Voltar", callback_data="list_sellers")])
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    finally:
        db.close()


async def show_seller(message: Message, db, slug: str):
    s = db.query(Seller).filter(Seller.slug == slug, Seller.status == "active").first()
    if not s:
        await message.answer("Loja não encontrada.", reply_markup=main_menu_kb())
        return
    prods = db.query(Product).filter(Product.seller_id == s.id, Product.status == "active").all()
    text = f"🏪 <b>{s.store_name}</b>\n\n{s.bio or ''}"
    kb = [[InlineKeyboardButton(text=f"📦 {p.name} — R$ {p.price:.2f}",
                                callback_data=f"prod_{p.id}")] for p in prods[:15]]
    kb.append([InlineKeyboardButton(text="⬅️ Menu", callback_data="main_menu")])
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@dp.callback_query(F.data.startswith("prod_"))
async def cb_product(cb: CallbackQuery):
    pid = int(cb.data.split("_", 1)[1])
    db = SessionLocal()
    try:
        await _show_product_view(cb, db, pid)
    finally:
        db.close()


async def show_product(message: Message, db, pid: int):
    p = db.query(Product).get(pid)
    if not p or p.status != "active":
        await message.answer("Produto indisponível.", reply_markup=main_menu_kb())
        return
    user = get_or_create_telegram_user(db, str(message.from_user.id),
                                       message.from_user.username or "")
    if p.is_adult and not user.age_confirmed:
        await ask_age_confirmation(message, pid)
        return
    text = product_text(p)
    kb = product_kb(p.id)
    await message.answer(text, reply_markup=kb)


async def _show_product_view(cb: CallbackQuery, db, pid: int):
    p = db.query(Product).get(pid)
    if not p or p.status != "active":
        await cb.answer("Produto indisponível", show_alert=True)
        return
    user = get_or_create_telegram_user(db, str(cb.from_user.id), cb.from_user.username or "")
    if p.is_adult and not user.age_confirmed:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tenho 18+", callback_data=f"age_yes_{pid}")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="main_menu")],
        ])
        await cb.message.edit_text(
            "⚠️ <b>Conteúdo Adulto +18</b>\n\nVocê confirma que tem 18 anos ou mais e aceita os termos da plataforma?",
            reply_markup=kb,
        )
        return
    await cb.message.edit_text(product_text(p), reply_markup=product_kb(p.id))


def product_text(p: Product) -> str:
    seller_name = p.seller.store_name if p.seller else ""
    adult = "\n🔞 <i>Conteúdo +18</i>" if p.is_adult else ""
    return (
        f"📦 <b>{p.name}</b>\n\n"
        f"{p.description or ''}\n\n"
        f"💵 <b>R$ {p.price:.2f}</b>\n"
        f"🏪 Vendedor: {seller_name}\n"
        f"📂 Categoria: {p.category.name if p.category else 'Geral'}{adult}"
    )


def product_kb(pid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Comprar", callback_data=f"buy_{pid}")],
        [InlineKeyboardButton(text="⚠️ Denunciar", callback_data=f"report_{pid}")],
        [InlineKeyboardButton(text="⬅️ Voltar", callback_data="main_menu")],
    ])


async def ask_age_confirmation(message: Message, pid: int):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tenho 18+", callback_data=f"age_yes_{pid}")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="main_menu")],
    ])
    await message.answer(
        "⚠️ <b>Conteúdo Adulto +18</b>\n\nVocê confirma que tem 18 anos ou mais e aceita os termos?",
        reply_markup=kb,
    )


@dp.callback_query(F.data.startswith("age_yes_"))
async def cb_age_yes(cb: CallbackQuery):
    pid = int(cb.data.split("_")[-1])
    db = SessionLocal()
    try:
        user = get_or_create_telegram_user(db, str(cb.from_user.id), cb.from_user.username or "")
        confirm_age(db, user)
        await _show_product_view(cb, db, pid)
    finally:
        db.close()


@dp.callback_query(F.data.startswith("buy_"))
async def cb_buy(cb: CallbackQuery):
    pid = int(cb.data.split("_", 1)[1])
    db = SessionLocal()
    try:
        user = get_or_create_telegram_user(db, str(cb.from_user.id), cb.from_user.username or "")
        order = create_order(db, user.id, pid)
        if not order:
            await cb.answer("Não foi possível criar o pedido.", show_alert=True)
            return
        pix = db.query(Setting).filter(Setting.key == "pix_key").first()
        instr = db.query(Setting).filter(Setting.key == "pix_instructions").first()
        text = (
            f"🧾 <b>Pedido #{order.id} criado!</b>\n\n"
            f"Valor: <b>R$ {order.amount:.2f}</b>\n"
            f"Status: ⏳ aguardando pagamento\n\n"
            f"💰 <b>Pagamento via Pix:</b>\n"
            f"Chave Pix: <code>{pix.value if pix and pix.value else 'Solicite ao suporte'}</code>\n\n"
            f"{instr.value if instr else 'Envie o comprovante ao suporte.'}\n\n"
            f"Após confirmação, o produto será entregue automaticamente."
        )
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Menu", callback_data="main_menu")],
        ]))
        log_action(db, user.id, "order_created", "order", order.id)
    finally:
        db.close()


@dp.callback_query(F.data == "my_orders")
async def cb_my_orders(cb: CallbackQuery):
    db = SessionLocal()
    try:
        user = get_or_create_telegram_user(db, str(cb.from_user.id), cb.from_user.username or "")
        orders = db.query(Order).filter(Order.buyer_id == user.id).order_by(
            Order.created_at.desc()).limit(15).all()
        if not orders:
            await cb.message.edit_text("📦 Você ainda não fez compras.", reply_markup=back_kb())
            return
        lines = ["📦 <b>Suas compras:</b>\n"]
        for o in orders:
            status_emoji = {"pending": "⏳", "paid": "✅", "delivered": "📬",
                            "canceled": "❌", "refunded": "↩️"}.get(o.status, "•")
            lines.append(f"{status_emoji} #{o.id} • {o.product.name if o.product else '?'} "
                         f"• R$ {o.amount:.2f} • {o.status}")
        await cb.message.edit_text("\n".join(lines), reply_markup=back_kb())
    finally:
        db.close()


@dp.callback_query(F.data.startswith("report_"))
async def cb_report(cb: CallbackQuery):
    pid = int(cb.data.split("_", 1)[1])
    kb = [[InlineKeyboardButton(text=label, callback_data=f"rsn_{key}_{pid}")]
          for key, label in REASONS.items()]
    kb.append([InlineKeyboardButton(text="⬅️ Voltar", callback_data=f"prod_{pid}")])
    await cb.message.edit_text("⚠️ Selecione o motivo da denúncia:",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@dp.callback_query(F.data.startswith("rsn_"))
async def cb_reason(cb: CallbackQuery):
    _, reason, pid = cb.data.split("_", 2)
    pid = int(pid)
    db = SessionLocal()
    try:
        user = get_or_create_telegram_user(db, str(cb.from_user.id), cb.from_user.username or "")
        p = db.query(Product).get(pid)
        seller_id = p.seller_id if p else None
        create_report(db, user.id, reason, product_id=pid, seller_id=seller_id)
        await cb.message.edit_text(
            "✅ Denúncia registrada. Nossa equipe irá analisar.",
            reply_markup=back_kb(),
        )
    finally:
        db.close()


@dp.callback_query(F.data == "support")
async def cb_support(cb: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Abrir novo ticket", callback_data="ticket_new")],
        [InlineKeyboardButton(text="📋 Meus tickets", callback_data="ticket_list")],
        [InlineKeyboardButton(text="⬅️ Voltar", callback_data="main_menu")],
    ])
    await cb.message.edit_text(
        "🆘 <b>Suporte CreatorGate</b>\n\n"
        "Abra um ticket para falar com nosso time. "
        "Você receberá uma notificação aqui no bot quando o suporte responder.",
        reply_markup=kb,
    )


@dp.message(Command("suporte"))
async def cmd_support(message: Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Abrir novo ticket", callback_data="ticket_new")],
        [InlineKeyboardButton(text="📋 Meus tickets", callback_data="ticket_list")],
        [InlineKeyboardButton(text="⬅️ Menu", callback_data="main_menu")],
    ])
    await message.answer("🆘 <b>Suporte CreatorGate</b>", reply_markup=kb)


@dp.callback_query(F.data == "ticket_new")
async def cb_ticket_new(cb: CallbackQuery, state: FSMContext):
    from app.services.tickets import CATEGORIES
    kb = [[InlineKeyboardButton(text=lbl, callback_data=f"tcat_{key}")]
          for key, lbl in CATEGORIES.items()]
    kb.append([InlineKeyboardButton(text="⬅️ Cancelar", callback_data="support")])
    await state.set_state(TicketFlow.choosing_category)
    await cb.message.edit_text("📂 <b>Qual a categoria do seu ticket?</b>",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@dp.callback_query(F.data.startswith("tcat_"), TicketFlow.choosing_category)
async def cb_ticket_cat(cb: CallbackQuery, state: FSMContext):
    cat = cb.data.split("_", 1)[1]
    await state.update_data(category=cat)
    await state.set_state(TicketFlow.typing_subject)
    await cb.message.edit_text(
        "📝 Digite o <b>assunto</b> do ticket (resumo curto):"
    )


@dp.message(TicketFlow.typing_subject)
async def msg_ticket_subject(message: Message, state: FSMContext):
    subject = (message.text or "").strip()
    if len(subject) < 3:
        await message.answer("⚠️ Assunto muito curto. Digite novamente:")
        return
    await state.update_data(subject=subject)
    await state.set_state(TicketFlow.typing_message)
    await message.answer(
        "💬 Agora descreva seu problema ou dúvida em detalhes:"
    )


@dp.message(TicketFlow.typing_message)
async def msg_ticket_message(message: Message, state: FSMContext):
    content = (message.text or "").strip()
    if len(content) < 5:
        await message.answer("⚠️ Mensagem muito curta. Digite novamente:")
        return
    data = await state.get_data()
    db = SessionLocal()
    try:
        from app.services.tickets import create_ticket
        user = get_or_create_telegram_user(
            db, str(message.from_user.id), message.from_user.username or "",
            message.from_user.first_name or "",
        )
        t = create_ticket(
            db, subject=data["subject"], category=data["category"],
            priority="normal", opener_user_id=user.id, initial_message=content,
        )
        await message.answer(
            f"✅ <b>Ticket criado!</b>\n\n"
            f"<code>{t.ticket_number}</code> · <b>{t.subject}</b>\n\n"
            f"Você receberá uma notificação aqui no bot assim que o suporte responder.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Meus tickets", callback_data="ticket_list")],
                [InlineKeyboardButton(text="⬅️ Menu", callback_data="main_menu")],
            ]),
        )
    finally:
        db.close()
    await state.clear()


@dp.callback_query(F.data == "ticket_list")
async def cb_ticket_list(cb: CallbackQuery):
    db = SessionLocal()
    try:
        from app.services.tickets import list_tickets, STATUS_LABELS
        user = get_or_create_telegram_user(db, str(cb.from_user.id),
                                           cb.from_user.username or "")
        tickets = list_tickets(db, opener_user_id=user.id, limit=10)
        if not tickets:
            await cb.message.edit_text(
                "📋 Você ainda não abriu nenhum ticket.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📝 Abrir ticket", callback_data="ticket_new")],
                    [InlineKeyboardButton(text="⬅️ Menu", callback_data="main_menu")],
                ]),
            )
            return
        kb = []
        for t in tickets:
            emoji = {"open": "🟢", "answered": "🔵", "pending": "🟡",
                     "closed": "⚪️"}.get(t.status, "•")
            kb.append([InlineKeyboardButton(
                text=f"{emoji} {t.ticket_number} · {t.subject[:30]}",
                callback_data=f"tview_{t.id}")])
        kb.append([InlineKeyboardButton(text="📝 Novo ticket", callback_data="ticket_new")])
        kb.append([InlineKeyboardButton(text="⬅️ Menu", callback_data="main_menu")])
        await cb.message.edit_text(
            "📋 <b>Seus tickets:</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        )
    finally:
        db.close()


@dp.callback_query(F.data.startswith("tview_"))
async def cb_ticket_view(cb: CallbackQuery, state: FSMContext):
    tid = int(cb.data.split("_", 1)[1])
    db = SessionLocal()
    try:
        from app.models import SupportTicket
        from app.services.tickets import STATUS_LABELS, CATEGORIES
        user = get_or_create_telegram_user(db, str(cb.from_user.id),
                                           cb.from_user.username or "")
        t = db.query(SupportTicket).filter(
            SupportTicket.id == tid, SupportTicket.opener_user_id == user.id,
        ).first()
        if not t:
            await cb.answer("Ticket não encontrado", show_alert=True)
            return
        lines = [
            f"📋 <b>{t.ticket_number}</b> — {t.subject}",
            f"📂 {CATEGORIES.get(t.category, t.category)} · 📊 {STATUS_LABELS.get(t.status, t.status)}",
            "",
        ]
        for m in t.messages:
            if m.is_internal_note:
                continue
            who = "🛡 Suporte" if m.sender_type == "staff" else "👤 Você"
            lines.append(f"<b>{who}</b> · {m.created_at.strftime('%d/%m %H:%M')}")
            lines.append(m.content[:600])
            lines.append("")
        kb_rows = []
        if t.status != "closed":
            await state.set_state(TicketFlow.replying)
            await state.update_data(ticket_id=t.id)
            kb_rows.append([InlineKeyboardButton(text="↩️ Cancelar resposta",
                                                 callback_data="ticket_list")])
            lines.append("✍️ <i>Digite uma mensagem para responder a este ticket.</i>")
        kb_rows.append([InlineKeyboardButton(text="⬅️ Voltar", callback_data="ticket_list")])
        await cb.message.edit_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
        )
    finally:
        db.close()


@dp.message(TicketFlow.replying)
async def msg_ticket_reply(message: Message, state: FSMContext):
    content = (message.text or "").strip()
    if len(content) < 2:
        await message.answer("⚠️ Mensagem muito curta.")
        return
    data = await state.get_data()
    tid = data.get("ticket_id")
    if not tid:
        await state.clear()
        return
    db = SessionLocal()
    try:
        from app.services.tickets import add_message
        user = get_or_create_telegram_user(db, str(message.from_user.id),
                                           message.from_user.username or "",
                                           message.from_user.first_name or "")
        sender_name = user.first_name or user.username or f"User #{user.id}"
        try:
            add_message(db, tid, "user", user.id, sender_name, content)
            await message.answer(
                "✅ Resposta enviada! O suporte foi notificado.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📋 Meus tickets", callback_data="ticket_list")],
                    [InlineKeyboardButton(text="⬅️ Menu", callback_data="main_menu")],
                ]),
            )
        except ValueError as e:
            await message.answer(f"⚠️ {e}")
    finally:
        db.close()
    await state.clear()


@dp.callback_query(F.data == "main_menu")
async def cb_main_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_main_menu(cb, cb.from_user.first_name or "")


@dp.callback_query(F.data == "become_seller")
async def cb_become_seller(cb: CallbackQuery, state: FSMContext):
    text = (
        "💰 <b>Quero vender no CreatorGate!</b>\n\n"
        "Você pode se cadastrar de duas formas:\n\n"
        "1️⃣ <b>Aqui pelo bot</b> — clique abaixo, informe nome da loja, bio e crie uma senha.\n"
        "2️⃣ <b>Pelo painel web</b> — acesse <b>" + settings.APP_BASE_URL + "/api/register</b>\n\n"
        "Em ambos, sua loja fica pendente até aprovação do admin."
    )
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Cadastrar pelo bot", callback_data="signup_bot")],
        [InlineKeyboardButton(text="⬅️ Voltar", callback_data="main_menu")],
    ]))


@dp.callback_query(F.data == "signup_bot")
async def cb_signup_bot(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SellerSignup.waiting_store_name)
    await cb.message.edit_text("📝 Envie o <b>nome da sua loja</b>:")


@dp.message(SellerSignup.waiting_store_name)
async def signup_name(message: Message, state: FSMContext):
    await state.update_data(store_name=message.text.strip())
    await state.set_state(SellerSignup.waiting_bio)
    await message.answer("📄 Agora envie uma <b>breve descrição</b> da sua loja:")


@dp.message(SellerSignup.waiting_bio)
async def signup_bio(message: Message, state: FSMContext):
    await state.update_data(bio=message.text.strip())
    await state.set_state(SellerSignup.waiting_password)
    await message.answer(
        "🔐 Agora crie uma <b>senha</b> para acessar o painel web do vendedor.\n\n"
        "Mínimo de <b>8 caracteres</b>. Use uma senha forte!"
    )


@dp.message(SellerSignup.waiting_password)
async def signup_password(message: Message, state: FSMContext):
    pwd = (message.text or "").strip()
    # tenta apagar a mensagem com a senha por segurança
    try:
        await message.delete()
    except Exception:
        pass
    if len(pwd) < 8:
        await message.answer("⚠️ A senha precisa ter pelo menos 8 caracteres. Tente novamente:")
        return
    await state.update_data(password=pwd)
    await state.set_state(SellerSignup.waiting_password_confirm)
    await message.answer("🔁 Confirme a senha digitando novamente:")


@dp.message(SellerSignup.waiting_password_confirm)
async def signup_password_confirm(message: Message, state: FSMContext):
    pwd2 = (message.text or "").strip()
    try:
        await message.delete()
    except Exception:
        pass
    data = await state.get_data()
    if pwd2 != data.get("password"):
        await message.answer("❌ As senhas não coincidem. Digite a senha novamente:")
        await state.set_state(SellerSignup.waiting_password)
        return
    db = SessionLocal()
    try:
        from app.services.sellers import create_seller
        user = get_or_create_telegram_user(db, str(message.from_user.id),
                                           message.from_user.username or "",
                                           message.from_user.first_name or "")
        user.role = "seller"
        db.commit()
        seller = create_seller(
            db, user.id, data["store_name"], data.get("bio", ""),
            password=data["password"],
        )
        await message.answer(
            f"✅ <b>Cadastro recebido!</b>\n\n"
            f"🏪 Loja: <b>{seller.store_name}</b>\n"
            f"🔗 Slug: <code>{seller.slug}</code>\n"
            f"📋 Status: ⏳ pendente de aprovação\n\n"
            f"Após aprovação do admin, você poderá fazer login no painel web em:\n"
            f"<b>{settings.APP_BASE_URL}/api/login</b>\n\n"
            f"Use o slug acima como usuário e a senha que você acabou de criar.",
            reply_markup=main_menu_kb(),
        )
    finally:
        db.close()
    await state.clear()


@dp.callback_query(F.data == "search")
async def cb_search(cb: CallbackQuery):
    db = SessionLocal()
    try:
        prods = db.query(Product).filter(Product.status == "active").limit(20).all()
        await _list_products(cb, prods, "🔎 Catálogo completo")
    finally:
        db.close()


def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Menu", callback_data="main_menu")],
    ])


async def start_bot():
    """Start the bot polling - run in background task."""
    global bot
    if not settings.BOT_TOKEN:
        logger.warning("BOT_TOKEN not set, bot disabled")
        return
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        await dp.start_polling(bot, handle_signals=False)
    except Exception as e:
        logger.exception("Bot polling failed: %s", e)


def get_bot() -> Bot | None:
    return bot


if __name__ == "__main__":
    asyncio.run(start_bot())
