from contextlib import asynccontextmanager
import logging
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.services.cache import create_redis_client, set_redis_client
from redis import RedisError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
PRODUCTION_FRONTEND_ORIGIN = "https://pos-systwm.vercel.app"


def get_allowed_frontend_origins(configured_origins: str) -> list[str]:
    # Keep the deployed application origin enabled even if Render has an old
    # FRONTEND_ORIGINS override that accidentally omits it.
    origins = {
        origin.strip().rstrip("/")
        for origin in configured_origins.split(",")
        if origin.strip()
    }
    origins.add(PRODUCTION_FRONTEND_ORIGIN)
    return sorted(origins)


@asynccontextmanager
async def lifespan(application: FastAPI):
    client = create_redis_client()
    set_redis_client(client)
    if client is not None:
        try:
            client.ping()
            logger.info("redis_startup_connected")
        except RedisError:
            # Redis is an optional accelerator; keep the API available without it.
            logger.warning("redis_startup_unavailable fallback=database", exc_info=True)
    else:
        logger.warning("redis_not_configured fallback=database")
    application.state.redis_cache = client
    try:
        yield
    finally:
        set_redis_client(None)
        if client is not None:
            client.close()
from app.routers import (
    audit_logs,
    auth,
    business,
    categories,
    customers,
    dashboard,
    expenses,
    inventory,
    payments,
    products,
    purchases,
    purchase_orders,
    reports,
    sales,
    suppliers,
    users,
)

app = FastAPI(
    title="POS & Inventory Management API",
    version="1.0.0",
    description="Multi-tenant SaaS foundation for business operations.",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def redact_secret_validation_inputs(_request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        item = dict(error)
        location = {str(part).lower() for part in item.get("loc", ())}
        if location & {"password", "new_password", "current_password", "otp", "challenge_token", "access_token"}:
            item["input"] = "[redacted]"
        errors.append(item)
    return JSONResponse(status_code=422, content=jsonable_encoder({"detail": errors}))

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_frontend_origins(settings.frontend_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(business.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(suppliers.router)
app.include_router(inventory.router)
app.include_router(customers.router)
app.include_router(purchases.router)
app.include_router(purchase_orders.router)
app.include_router(sales.router)
app.include_router(payments.router)
app.include_router(expenses.router)
app.include_router(audit_logs.router)
app.include_router(dashboard.router)
app.include_router(reports.router)


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
