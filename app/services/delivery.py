"""Delivery service - sends product to buyer after payment."""
from sqlalchemy.orm import Session
from app.models import Order, Product
from app.services.orders import mark_delivered


async def deliver_order(db: Session, order_id: int, bot=None) -> dict:
    """Returns dict with delivery info: type, content. If bot is provided, sends via Telegram."""
    order = db.query(Order).get(order_id)
    if not order or order.status not in ("paid",):
        return {"ok": False, "reason": "Order not in paid state"}

    product = db.query(Product).get(order.product_id)
    if not product:
        return {"ok": False, "reason": "Product not found"}

    delivery = {"type": product.delivery_type}

    if product.delivery_type == "texto":
        delivery["content"] = product.content_text
    elif product.delivery_type == "link":
        delivery["content"] = product.private_link
    elif product.delivery_type == "arquivo":
        delivery["content"] = product.file_path
    elif product.delivery_type == "grupo_telegram":
        delivery["content"] = product.telegram_chat_id or product.private_link

    # Send via Telegram bot if available
    if bot and order.buyer and order.buyer.telegram_id:
        try:
            chat_id = int(order.buyer.telegram_id)
            text = f"✅ Pedido #{order.id} confirmado!\n\n📦 {product.name}\n\n"
            if product.delivery_type == "texto":
                text += f"📝 Conteúdo:\n\n{product.content_text}"
                await bot.send_message(chat_id, text)
            elif product.delivery_type == "link":
                text += f"🔗 Acesso: {product.private_link}"
                await bot.send_message(chat_id, text)
            elif product.delivery_type == "grupo_telegram":
                text += f"👥 Grupo: {product.telegram_chat_id or product.private_link}"
                await bot.send_message(chat_id, text)
            elif product.delivery_type == "arquivo":
                from pathlib import Path
                if product.file_path and Path(product.file_path).exists():
                    from aiogram.types import FSInputFile
                    await bot.send_message(chat_id, text)
                    await bot.send_document(chat_id, FSInputFile(product.file_path))
                else:
                    await bot.send_message(chat_id, text + "Entre em contato com o vendedor para receber o arquivo.")
            delivery["sent"] = True
        except Exception as e:
            delivery["error"] = str(e)
            delivery["sent"] = False

    mark_delivered(db, order_id)
    return {"ok": True, **delivery}
