import httpx

from app.barcode.music_format import map_music_format
from app.barcode.providers.base import MetadataProvider
from app.barcode.schemas import BarcodeCandidate
from app.config import settings
from app.models.enums import MediaType

DISCOGS_URL = "https://api.discogs.com/database/search"
USER_AGENT = "MediaDatabaseApp/0.1 (household-media-database; contact@example.invalid)"


def _map_format_list(formats: list[str]) -> MediaType | None:
    for value in formats:
        mapped = map_music_format(value)
        if mapped:
            return mapped
    return None


class DiscogsProvider(MetadataProvider):
    """Appendix A.5: direct barcode search for CD/VINYL/CASSETTE releases, complementing
    MusicBrainz. Works unauthenticated at a lower rate limit; a token raises the limit (6.3)."""

    provider_name = "discogs"
    covers_media_types = [MediaType.CD, MediaType.VINYL, MediaType.CASSETTE]
    requires_api_key = False
    rate_limit_per_second = 1.0  # 60/min authenticated, 25/min unauthenticated

    def supports_barcode_lookup(self) -> bool:
        return True

    def _to_candidate(self, result: dict) -> BarcodeCandidate:
        return BarcodeCandidate(
            source_provider=self.provider_name,
            media_type=_map_format_list(result.get("format") or []),
            title=result.get("title", ""),
            subtitle=", ".join(result.get("label") or []) or None,
            external_id=str(result.get("id")) if result.get("id") is not None else None,
            external_url=result.get("resource_url"),
            cover_image_url=result.get("cover_image"),
            raw_attributes=result,
        )

    def _params(self, **extra) -> dict:
        params = {**extra}
        if settings.discogs_token:
            params["token"] = settings.discogs_token
        return params

    async def lookup_by_barcode(self, barcode: str) -> list[BarcodeCandidate]:
        async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}) as client:
            data = await self._get_json(
                client, DISCOGS_URL, params=self._params(barcode=barcode, type="release")
            )
        return [self._to_candidate(r) for r in data.get("results", [])]

    async def search_by_title(self, title: str, media_type: MediaType | None) -> list[BarcodeCandidate]:
        async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}) as client:
            data = await self._get_json(client, DISCOGS_URL, params=self._params(q=title, type="release"))
        return [self._to_candidate(r) for r in data.get("results", [])]
