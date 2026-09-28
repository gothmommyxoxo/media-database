from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ItemSource, MediaType


class MediaItemCreate(BaseModel):
    media_type: MediaType
    title: str
    subtitle: str | None = None
    barcode: str | None = None
    format: str | None = None
    condition: str | None = None
    notes: str | None = None
    cover_image_url: str | None = None
    attributes: dict = {}
    external_ids: dict = {}
    source: ItemSource = ItemSource.MANUAL


class MediaItemUpdate(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    barcode: str | None = None
    format: str | None = None
    condition: str | None = None
    notes: str | None = None
    cover_image_url: str | None = None
    attributes: dict | None = None
    external_ids: dict | None = None


class MediaItemResponse(BaseModel):
    id: int
    media_type: MediaType
    title: str
    subtitle: str | None
    barcode: str | None
    format: str | None
    condition: str | None
    notes: str | None
    cover_image_url: str | None
    attributes: dict
    external_ids: dict
    source: ItemSource
    added_by: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MediaItemPage(BaseModel):
    items: list[MediaItemResponse]
    total: int
