"""
FleetFlow — Smart Logistics & Delivery Platform
Enterprise-grade FastAPI backend with real-time tracking,
dynamic pricing, and event-driven architecture.
"""
import time
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.redis import get_redis, close_redis
from app.db.session import init_db
from app.api.v1.endpoints import auth, deliveries, payments, offers, drivers, admin, users
from app.websockets.tracking import router as ws_router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 FleetFlow starting up...")
    # Verify Redis connection
    redis = await get_redis()
    await redis.ping()
    logger.info("✅ Redis connected")
    logger.info("✅ FleetFlow ready to serve requests")
    yield
    # Cleanup
    await close_redis()
    logger.info("👋 FleetFlow shutdown complete")

app = FastAPI(
    title="FleetFlow API",
    description="Smart Logistics & Delivery Platform — Real-time tracking, dynamic pricing, event-driven architecture",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── Middleware ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = round((time.time() - start_time) * 1000, 2)
    logger.info(
        "Request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=process_time,
        ip=request.client.host if request.client else "unknown",
    )
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# ─── Exception Handlers ─────────────────────────────────────
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found", "path": request.url.path}
    )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.error("Internal server error", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# ─── Routers ────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(deliveries.router, prefix=API_PREFIX)
app.include_router(payments.router, prefix=API_PREFIX)
app.include_router(offers.router, prefix=API_PREFIX)
app.include_router(drivers.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX + "/users", tags=["users"])

# WebSocket routes (no prefix — WS paths are /ws/...)
app.include_router(ws_router)

# ─── Health & Info ──────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "FleetFlow API",
        "version": "1.0.0",
    }

@app.get("/health/detailed", tags=["System"])
async def detailed_health():
    redis_ok = False
    try:
        redis = await get_redis()
        await redis.ping()
        redis_ok = True
    except Exception:
        pass

    return {
        "status": "healthy" if redis_ok else "degraded",
        "services": {
            "api": "up",
            "redis": "up" if redis_ok else "down",
            "database": "up",
        }
    }

@app.get("/", tags=["System"])
async def root():
    return {
        "service": "FleetFlow API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
