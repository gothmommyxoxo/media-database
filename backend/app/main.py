from fastapi import FastAPI

from app.admin.router import router as admin_router
from app.auth.router import router as auth_router
from app.barcode.router import router as barcode_router
from app.collection.router import router as collection_router
from app.config import settings

# The interactive API docs are a dev convenience; don't advertise the full API surface publicly.
_docs_kwargs = {"docs_url": None, "redoc_url": None, "openapi_url": None} if settings.is_production else {}

app = FastAPI(title="Media Database API", **_docs_kwargs)
app.include_router(auth_router)
app.include_router(collection_router)
app.include_router(barcode_router)
app.include_router(admin_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
