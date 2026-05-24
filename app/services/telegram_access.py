"""Telegram access helper - permissions / deep link parsing."""


def parse_start_payload(payload: str) -> dict:
    """Parse /start payload like 'product_123' or 'seller_creator-gate-1'."""
    if not payload:
        return {"type": "default"}
    if payload.startswith("product_"):
        try:
            return {"type": "product", "id": int(payload[8:])}
        except ValueError:
            return {"type": "default"}
    if payload.startswith("seller_"):
        return {"type": "seller", "slug": payload[7:]}
    return {"type": "default"}


def build_product_deep_link(bot_username: str, product_id: int) -> str:
    return f"https://t.me/{bot_username}?start=product_{product_id}"


def build_seller_deep_link(bot_username: str, slug: str) -> str:
    return f"https://t.me/{bot_username}?start=seller_{slug}"
