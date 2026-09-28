from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.user import utcnow


class BarcodeCache(Base):
    """Accumulated, deduplicated candidates ever resolved for a barcode (Section 3.4)."""

    __tablename__ = "barcode_cache"

    barcode: Mapped[str] = mapped_column(String(32), primary_key=True)
    candidates: Mapped[list] = mapped_column(JSON, default=list)
    last_refreshed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    refresh_count: Mapped[int] = mapped_column(Integer, default=0)
