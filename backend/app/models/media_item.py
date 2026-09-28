from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import ItemSource, MediaType
from app.models.user import utcnow


class MediaItem(Base):
    __tablename__ = "media_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    media_type: Mapped[MediaType] = mapped_column(SAEnum(MediaType, native_enum=False, length=20))
    title: Mapped[str] = mapped_column(String(500))
    subtitle: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # No uniqueness constraint: two distinct owned items may legitimately share a barcode (3.2).
    barcode: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    format: Mapped[str | None] = mapped_column(String(200), nullable=True)
    condition: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    external_ids: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[ItemSource] = mapped_column(SAEnum(ItemSource, native_enum=False, length=10))
    # Nullable: deleting a user nulls this out rather than deleting their items (4.1's rationale).
    added_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
