from sqlalchemy.orm import Session

from app.attributes.schemas import validate_attributes
from app.auth.security import hash_password
from app.auth.service import DuplicateUsernameError
from app.models import BarcodeCache, MediaItem, Role, User


class LastAdminError(Exception):
    """Raised when an action would leave the household with zero ADMIN accounts (4.1)."""


def _admin_count(db: Session) -> int:
    return db.query(User).filter(User.role == Role.ADMIN).count()


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.username).all()


def create_user(db: Session, username: str, display_name: str, password: str, role: Role) -> User:
    if db.query(User).filter(User.username == username).first() is not None:
        raise DuplicateUsernameError(username)

    user = User(username=username, display_name=display_name, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    user: User,
    username: str | None = None,
    display_name: str | None = None,
    role: Role | None = None,
) -> User:
    if username is not None and username != user.username:
        if db.query(User).filter(User.username == username).first() is not None:
            raise DuplicateUsernameError(username)
        user.username = username

    if role is not None and role != user.role:
        if user.role == Role.ADMIN and role == Role.MEMBER and _admin_count(db) <= 1:
            raise LastAdminError("cannot demote the only remaining admin")
        user.role = role

    if display_name is not None:
        user.display_name = display_name

    db.commit()
    db.refresh(user)
    return user


def reset_password(db: Session, user: User, new_password: str) -> None:
    user.password_hash = hash_password(new_password)
    db.commit()


def delete_user(db: Session, user: User) -> None:
    if user.role == Role.ADMIN and _admin_count(db) <= 1:
        raise LastAdminError("cannot delete the only remaining admin")

    # The collection belongs to the household, not to whoever added an item (13's rationale) --
    # deleting an account nulls its attribution rather than deleting the items it added.
    db.query(MediaItem).filter(MediaItem.added_by == user.id).update({MediaItem.added_by: None})
    db.delete(user)
    db.commit()


def update_item_admin(db: Session, item: MediaItem, payload) -> MediaItem:
    updates = payload.model_dump(exclude_unset=True)
    new_media_type = updates.get("media_type", item.media_type)

    if "attributes" in updates and updates["attributes"] is not None:
        updates["attributes"] = validate_attributes(new_media_type, updates["attributes"])
    elif "media_type" in updates:
        # media_type changed but attributes weren't explicitly given -- re-validate the existing
        # attributes against the new type's schema so the record never ends up in a shape the
        # application itself couldn't have produced (7.4/13's rationale).
        updates["attributes"] = validate_attributes(new_media_type, item.attributes)

    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def list_barcode_cache(db: Session, page: int = 1, page_size: int = 50) -> tuple[list[BarcodeCache], int]:
    query = db.query(BarcodeCache).order_by(BarcodeCache.last_refreshed_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_barcode_cache(db: Session, barcode: str) -> BarcodeCache | None:
    return db.get(BarcodeCache, barcode)


def delete_barcode_cache(db: Session, entry: BarcodeCache) -> None:
    # Purging a cache entry never touches MediaItem (7.4) -- it only forces the next scan of
    # that barcode to re-resolve from scratch (5.3) instead of serving stale/bad candidates.
    db.delete(entry)
    db.commit()
