from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
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
    reports,
    sales,
    suppliers,
    users,
)

app = FastAPI(
    title="POS & Inventory Management API",
    version="1.0.0",
    description="Multi-tenant SaaS foundation for business operations.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.frontend_origins.split(",")],
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
app.include_router(sales.router)
app.include_router(payments.router)
app.include_router(expenses.router)
app.include_router(audit_logs.router)
app.include_router(dashboard.router)
app.include_router(reports.router)


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
