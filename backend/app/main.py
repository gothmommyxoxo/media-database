from fastapi import FastAPI

from app.admin.router import router as admin_router
from app.auth.router import router as auth_router
from app.barcode.router import router as barcode_router
from app.collection.router import router as collection_router

app = FastAPI(title="Media Database API")
app.include_router(auth_router)
app.include_router(collection_router)
app.include_router(barcode_router)
app.include_router(admin_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
