from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.admin import service
from app.admin.schemas import (
    AdminItemUpdate,
    BarcodeCachePage,
    BarcodeCacheResponse,
    CreateUserRequest,
    ResetPasswordRequest,
    UpdateUserRequest,
)
from app.auth.dependencies import get_current_admin
from app.auth.schemas import UserResponse
from app.auth.service import DuplicateUsernameError
from app.collection.schemas import MediaItemResponse
from app.collection.service import get_item
from app.db import get_db
from app.models import User

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return user


@router.get("/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> list[User]:
    return service.list_users(db)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> User:
    try:
        return service.create_user(db, payload.username, payload.display_name, payload.password, payload.role)
    except DuplicateUsernameError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username already exists")


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UpdateUserRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> User:
    user = _get_user_or_404(db, user_id)
    try:
        return service.update_user(
            db, user, username=payload.username, display_name=payload.display_name, role=payload.role
        )
    except DuplicateUsernameError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username already exists")
    except service.LastAdminError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/users/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    user_id: int,
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> None:
    user = _get_user_or_404(db, user_id)
    service.reset_password(db, user, payload.new_password)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> None:
    user = _get_user_or_404(db, user_id)
    try:
        service.delete_user(db, user)
    except service.LastAdminError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.patch("/items/{item_id}", response_model=MediaItemResponse)
def update_item_admin(
    item_id: int,
    payload: AdminItemUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> MediaItemResponse:
    item = get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="item not found")
    try:
        return service.update_item_admin(db, item, payload)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.errors())


@router.get("/barcode-cache", response_model=BarcodeCachePage)
def list_barcode_cache(
    page: int = 1,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> BarcodeCachePage:
    items, total = service.list_barcode_cache(db, page=page)
    return BarcodeCachePage(items=items, total=total)


@router.get("/barcode-cache/{barcode}", response_model=BarcodeCacheResponse)
def get_barcode_cache(
    barcode: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> BarcodeCacheResponse:
    entry = service.get_barcode_cache(db, barcode)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no cache entry for this barcode")
    return entry


@router.delete("/barcode-cache/{barcode}", status_code=status.HTTP_204_NO_CONTENT)
def delete_barcode_cache(
    barcode: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> None:
    entry = service.get_barcode_cache(db, barcode)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no cache entry for this barcode")
    service.delete_barcode_cache(db, entry)
