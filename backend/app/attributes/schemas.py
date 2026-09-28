"""Pydantic mirrors of the Appendix B attribute RECORDs. All fields are optional since both
manual entry and partial provider data must be accepted (Appendix B)."""

from pydantic import BaseModel

from app.models.enums import MediaType


class MangaAttributes(BaseModel):
    series_title: str | None = None
    volume: int | None = None
    isbn: str | None = None
    publisher: str | None = None
    author: str | None = None


class BookAttributes(BaseModel):
    author: str | None = None
    isbn: str | None = None
    publisher: str | None = None
    series_title: str | None = None
    edition: str | None = None


class ComicBookAttributes(BaseModel):
    series_title: str | None = None
    issue_number: str | None = None
    publisher: str | None = None
    writer: str | None = None
    artist: str | None = None
    variant_cover: str | None = None


class GraphicNovelAttributes(BaseModel):
    series_title: str | None = None
    volume: int | None = None
    isbn: str | None = None
    publisher: str | None = None
    writer: str | None = None
    artist: str | None = None
    collects_issues: str | None = None


class VideoGameAttributes(BaseModel):
    platform: str | None = None
    region: str | None = None
    developer: str | None = None
    publisher: str | None = None
    genre: str | None = None


class VideoReleaseAttributes(BaseModel):
    """Shared by BLU_RAY, DVD, VHS, VCD, LASERDISC."""

    director: str | None = None
    runtime_minutes: int | None = None
    region_code: str | None = None
    special_edition: str | None = None
    is_anime: bool | None = None


class MusicAttributes(BaseModel):
    """Shared by CD, VINYL, CASSETTE."""

    artist: str | None = None
    label: str | None = None
    release_year: int | None = None
    track_count: int | None = None


ATTRIBUTE_SCHEMA_BY_MEDIA_TYPE: dict[MediaType, type[BaseModel]] = {
    MediaType.MANGA: MangaAttributes,
    MediaType.BOOK: BookAttributes,
    MediaType.COMIC_BOOK: ComicBookAttributes,
    MediaType.GRAPHIC_NOVEL: GraphicNovelAttributes,
    MediaType.VIDEO_GAME: VideoGameAttributes,
    MediaType.BLU_RAY: VideoReleaseAttributes,
    MediaType.DVD: VideoReleaseAttributes,
    MediaType.VHS: VideoReleaseAttributes,
    MediaType.VCD: VideoReleaseAttributes,
    MediaType.LASERDISC: VideoReleaseAttributes,
    MediaType.CD: MusicAttributes,
    MediaType.VINYL: MusicAttributes,
    MediaType.CASSETTE: MusicAttributes,
}


def validate_attributes(media_type: MediaType, attributes: dict) -> dict:
    """Validates and normalizes an attributes dict against its MediaType's schema (3.2)."""
    schema = ATTRIBUTE_SCHEMA_BY_MEDIA_TYPE[media_type]
    return schema.model_validate(attributes).model_dump(exclude_none=True)
