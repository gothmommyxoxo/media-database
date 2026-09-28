from pydantic import BaseModel

from app.models.enums import MediaType


class BarcodeCandidate(BaseModel):
    source_provider: str
    media_type: MediaType | None = None
    title: str
    subtitle: str | None = None
    external_id: str | None = None
    external_url: str | None = None
    cover_image_url: str | None = None
    raw_attributes: dict = {}


class ResolutionResult(BaseModel):
    candidates: list[BarcodeCandidate]
    owned_matches: list[dict]
    requires_manual_entry: bool
