from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.barcode import resolution
from app.barcode.schemas import BarcodeCandidate, ResolutionResult
from app.collection.schemas import MediaItemResponse
from app.collection.service import create_item as create_media_item
from app.db import get_db
from app.models.enums import ItemSource, MediaType
from app.models.user import User

router = APIRouter(prefix="/api/barcode", tags=["barcode"])


class CreateFromCandidateRequest(BaseModel):
    candidate: BarcodeCandidate
    media_type: MediaType
    barcode: str
    overrides: dict = {}


class _ItemCreatePayload(BaseModel):
    """Internal shape handed to collection.service.create_item (5.3, 8)."""

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
    source: ItemSource = ItemSource.SCANNED


@router.get("/{barcode}/resolve", response_model=ResolutionResult)
async def resolve(
    barcode: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ResolutionResult:
    return await resolution.resolve_barcode(db, barcode)


@router.post("/items", response_model=MediaItemResponse, status_code=201)
def create_from_candidate(
    payload: CreateFromCandidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MediaItemResponse:
    candidate = payload.candidate
    overrides = payload.overrides

    external_ids = {}
    if candidate.external_id:
        external_ids[candidate.source_provider] = candidate.external_id

    create_payload = _ItemCreatePayload(
        media_type=payload.media_type,
        title=overrides.get("title", candidate.title),
        subtitle=overrides.get("subtitle", candidate.subtitle),
        barcode=payload.barcode,
        format=overrides.get("format"),
        condition=overrides.get("condition"),
        notes=overrides.get("notes"),
        cover_image_url=overrides.get("cover_image_url", candidate.cover_image_url),
        attributes=overrides.get("attributes", {}),
        external_ids=external_ids,
        source=ItemSource.SCANNED,
    )
    return create_media_item(db, create_payload, added_by=current_user.id)
