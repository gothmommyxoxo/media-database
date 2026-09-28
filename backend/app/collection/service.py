from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.attributes.schemas import validate_attributes
from app.models import MediaItem, MediaType


def create_item(db: Session, payload, added_by: int) -> MediaItem:
    attributes = validate_attributes(payload.media_type, payload.attributes)
    item = MediaItem(
        media_type=payload.media_type,
        title=payload.title,
        subtitle=payload.subtitle,
        barcode=payload.barcode,
        format=payload.format,
        condition=payload.condition,
        notes=payload.notes,
        cover_image_url=payload.cover_image_url,
        attributes=attributes,
        external_ids=payload.external_ids,
        source=payload.source,
        added_by=added_by,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_item(db: Session, item_id: int) -> MediaItem | None:
    return db.get(MediaItem, item_id)


def list_items(
    db: Session,
    media_types: list[MediaType] | None = None,
    search: str | None = None,
    added_by: int | None = None,
    sort: str = "title",
) -> tuple[list[MediaItem], int]:
    query = db.query(MediaItem)

    if media_types:
        query = query.filter(MediaItem.media_type.in_(media_types))
    if added_by is not None:
        query = query.filter(MediaItem.added_by == added_by)
    if search:
        like = f"%{search.lower()}%"
        query = query.filter(
            or_(
                MediaItem.title.ilike(like),
                MediaItem.subtitle.ilike(like),
                MediaItem.notes.ilike(like),
            )
        )

    sort_column = {
        "title": MediaItem.title,
        "created_at": MediaItem.created_at,
        "updated_at": MediaItem.updated_at,
    }.get(sort, MediaItem.title)
    query = query.order_by(sort_column)

    total = query.count()
    return query.all(), total


def update_item(db: Session, item: MediaItem, payload) -> MediaItem:
    updates = payload.model_dump(exclude_unset=True)
    if "attributes" in updates and updates["attributes"] is not None:
        updates["attributes"] = validate_attributes(item.media_type, updates["attributes"])
    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item: MediaItem) -> None:
    db.delete(item)
    db.commit()
