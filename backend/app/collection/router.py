from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.collection import service
from app.collection.schemas import MediaItemCreate, MediaItemPage, MediaItemResponse, MediaItemUpdate
from app.db import get_db
from app.models import MediaType, User

router = APIRouter(prefix="/api/items", tags=["collection"])


def _get_item_or_404(db: Session, item_id: int):
    item = service.get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="item not found")
    return item


@router.get("", response_model=MediaItemPage)
def list_items(
    media_type: list[MediaType] | None = Query(default=None),
    search: str | None = Query(default=None),
    added_by: int | None = Query(default=None),
    sort: str = Query(default="title"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> MediaItemPage:
    items, total = service.list_items(db, media_types=media_type, search=search, added_by=added_by, sort=sort)
    return MediaItemPage(items=items, total=total)


@router.post("", response_model=MediaItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: MediaItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MediaItemResponse:
    try:
        return service.create_item(db, payload, added_by=current_user.id)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.errors())


@router.get("/{item_id}", response_model=MediaItemResponse)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> MediaItemResponse:
    return _get_item_or_404(db, item_id)


@router.patch("/{item_id}", response_model=MediaItemResponse)
def update_item(
    item_id: int,
    payload: MediaItemUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> MediaItemResponse:
    item = _get_item_or_404(db, item_id)
    try:
        return service.update_item(db, item, payload)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.errors())


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> None:
    item = _get_item_or_404(db, item_id)
    service.delete_item(db, item)
