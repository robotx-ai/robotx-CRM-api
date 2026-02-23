from __future__ import annotations

from fastapi import FastAPI

from app.config import settings
from app.routers.auth import router as auth_router
from app.routers.machine_product_library import router as machine_product_library_router
from app.routers.sales_lead_followups import router as sales_lead_followups_router
from app.routers.sales_leads import router as sales_leads_router
from app.routers.store_management import router as store_management_router

app = FastAPI(
    title="RobotX CRM Machine Product Library API",
    version="1.0.0",
    description=(
        "FastAPI + OpenAPI endpoints for CRUD operations on Supabase table "
        "`machineproductlibrary` based on product-info and product-edit pages."
    ),
)


@app.get("/health", tags=["System"], summary="Health check")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(machine_product_library_router, prefix=settings.api_prefix)
app.include_router(store_management_router, prefix=settings.api_prefix)
app.include_router(sales_leads_router, prefix=settings.api_prefix)
app.include_router(sales_lead_followups_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
