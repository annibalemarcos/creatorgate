"""CreatorGate FastAPI main app."""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import init_db
from app.seed import seed
from app.scheduler import start_scheduler
from app.routers import auth as auth_router
from app.routers import admin as admin_router
from app.routers import seller as seller_router
from app.routers import public as public_router
from app.routers import staff as staff_router
from app.routers import admin_tickets as admin_tickets_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed()
    start_scheduler()
    # Start telegram bot in background if enabled
    bot_task = None
    if settings.ENABLE_BOT and settings.BOT_TOKEN:
        from app.bot import start_bot
        bot_task = asyncio.create_task(start_bot())
        logger.info("Telegram bot started in background")
    else:
        logger.info("Telegram bot DISABLED (set ENABLE_BOT=true and BOT_TOKEN to enable)")
    yield
    if bot_task:
        bot_task.cancel()


app = FastAPI(title="CreatorGate", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET,
    session_cookie="creatorgate_session",
    max_age=60 * 60 * 24 * 7,
    same_site="lax",
    https_only=False,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/api/static", StaticFiles(directory="app/static"), name="static")
# Public previews (covers etc) – only allow products dir
app.mount("/api/uploads/products", StaticFiles(directory="uploads/products"), name="products_imgs")


# Routers - all prefixed with /api to match Emergent ingress; for local 5812
# you can remove the /api prefix if desired.
app.include_router(public_router.router, prefix="/api")
app.include_router(auth_router.router, prefix="/api")
app.include_router(admin_router.router, prefix="/api")
app.include_router(staff_router.router, prefix="/api")
app.include_router(admin_tickets_router.router, prefix="/api")
app.include_router(seller_router.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "CreatorGate"}


@app.get("/api/download/source")
def download_source():
    """Download the full CreatorGate source code as zip."""
    from fastapi.responses import FileResponse
    zip_path = "/app/creatorgate.zip"
    return FileResponse(zip_path, media_type="application/zip", filename="creatorgate.zip")


@app.get("/api")
def api_root():
    return RedirectResponse("/api/", status_code=303)


@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    # If a redirect is encoded as 303 via auth guards, propagate Location
    if exc.status_code == 303 and exc.headers and "Location" in exc.headers:
        return RedirectResponse(exc.headers["Location"], status_code=303)
    if exc.status_code == 404:
        return JSONResponse({"error": "Not found", "path": str(request.url.path)},
                            status_code=404)
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)
