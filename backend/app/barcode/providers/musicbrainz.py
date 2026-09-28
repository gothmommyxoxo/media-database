import httpx

from app.barcode.music_format import map_music_format
from app.barcode.providers.base import MetadataProvider
from app.barcode.schemas import BarcodeCandidate
from app.models.enums import MediaType

MUSICBRAINZ_URL = "https://musicbrainz.org/ws/2/release/"
USER_AGENT = "MediaDatabaseApp/0.1 (household-media-database; contact@example.invalid)"


class MusicBrainzProvider(MetadataProvider):
    """Appendix A.5: direct barcode search for CD/VINYL/CASSETTE releases."""

    provider_name = "musicbrainz"
    covers_media_types = [MediaType.CD, MediaType.VINYL, MediaType.CASSETTE]
    requires_api_key = False
    rate_limit_per_second = 1.0  # hard limit per MusicBrainz's published policy (6.3)

    def supports_barcode_lookup(self) -> bool:
        return True

    def _to_candidate(self, release: dict) -> BarcodeCandidate:
        media = release.get("media") or [{}]
        format_value = media[0].get("format")
        artists = ", ".join(a.get("name", "") for a in release.get("artist-credit", []))
        return BarcodeCandidate(
            source_provider=self.provider_name,
            media_type=map_music_format(format_value),
            title=release.get("title", ""),
            subtitle=artists or None,
            external_id=release.get("id"),
            external_url=f"https://musicbrainz.org/release/{release['id']}" if release.get("id") else None,
            raw_attributes=release,
        )

    async def lookup_by_barcode(self, barcode: str) -> list[BarcodeCandidate]:
        async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}) as client:
            data = await self._get_json(
                client,
                MUSICBRAINZ_URL,
                params={"query": f"barcode:{barcode}", "fmt": "json"},
            )
        return [self._to_candidate(release) for release in data.get("releases", [])]

    async def search_by_title(self, title: str, media_type: MediaType | None) -> list[BarcodeCandidate]:
        async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}) as client:
            data = await self._get_json(
                client,
                MUSICBRAINZ_URL,
                params={"query": f'release:"{title}"', "fmt": "json"},
            )
        return [self._to_candidate(release) for release in data.get("releases", [])]
