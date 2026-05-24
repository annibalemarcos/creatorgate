"""CreatorGate configuration loaded from environment variables."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:5812")
    ALLOW_ADULT_CONTENT: bool = os.getenv("ALLOW_ADULT_CONTENT", "true").lower() == "true"
    PLATFORM_COMMISSION_PERCENT: float = float(os.getenv("PLATFORM_COMMISSION_PERCENT", "15"))
    SESSION_SECRET: str = os.getenv("SESSION_SECRET", "dev-secret-change-me")
    PIX_KEY_DEFAULT: str = os.getenv("PIX_KEY_DEFAULT", "")
    PIX_INSTRUCTIONS: str = os.getenv("PIX_INSTRUCTIONS", "Envie o valor exato e confirme com o suporte")
    ENABLE_BOT: bool = os.getenv("ENABLE_BOT", "false").lower() == "true"

    BASE_DIR: Path = BASE_DIR
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    PROTECTED_DIR: Path = BASE_DIR / "uploads" / "protected"
    PREVIEW_DIR: Path = BASE_DIR / "uploads" / "previews"
    PRODUCT_IMG_DIR: Path = BASE_DIR / "uploads" / "products"
    DATA_DIR: Path = BASE_DIR / "data"

    ALLOWED_EXTENSIONS: set = {
        ".pdf", ".zip", ".rar", ".txt", ".md", ".doc", ".docx",
        ".jpg", ".jpeg", ".png", ".gif", ".webp",
        ".mp3", ".wav", ".ogg", ".m4a",
        ".mp4", ".mov", ".avi", ".webm",
    }
    MAX_UPLOAD_MB: int = 50


settings = Settings()

# Ensure directories exist
for d in (settings.UPLOAD_DIR, settings.PROTECTED_DIR, settings.PREVIEW_DIR,
          settings.PRODUCT_IMG_DIR, settings.DATA_DIR):
    d.mkdir(parents=True, exist_ok=True)
