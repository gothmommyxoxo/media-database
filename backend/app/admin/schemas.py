from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.barcode.schemas import BarcodeCandidate
from app.models.enums import ItemSource, MediaType, Role


class CreateUserRequest(BaseModel):
    username: str
    display_name: str
    password: str
    role: Role = Role.MEMBER


class UpdateUserRequest(BaseModel):
    username: str | None = None
    display_name: str | None = None
    role: Role | None = None


class ResetPasswordRequest(BaseModel):
    new_password: str


class AdminItemUpdate(BaseModel):
    """Section 7.4: superset of MediaItemUpdate (collection/schemas.py) -- exposes fields the
    normal member edit form never does."""

    media_type: MediaType | None = None
    title: str | None = None
    subtitle: str | None = None
    barcode: str | None = None
    format: str | None = None
    condition: str | None = None
    notes: str | None = None
    cover_image_url: str | None = None
    attributes: dict | None = None
    external_ids: dict | None = None
    source: ItemSource | None = None
    added_by: int | None = None


class BarcodeCacheResponse(BaseModel):
    barcode: str
    candidates: list[BarcodeCandidate]
    last_refreshed_at: datetime
    refresh_count: int

    model_config = ConfigDict(from_attributes=True)


class BarcodeCachePage(BaseModel):
    items: list[BarcodeCacheResponse]
    total: int
