from app.models.enums import MediaType

# Section 6.2.1: MusicBrainz/Discogs return one format string per release; only these three map
# onto a MediaType. Anything else (Digital Media, SACD, ...) is surfaced unclassified.
MUSIC_FORMAT_MAP: dict[str, MediaType] = {
    "CD": MediaType.CD,
    "Vinyl": MediaType.VINYL,
    "Cassette": MediaType.CASSETTE,
}


def map_music_format(format_value: str | None) -> MediaType | None:
    if format_value is None:
        return None
    return MUSIC_FORMAT_MAP.get(format_value)
