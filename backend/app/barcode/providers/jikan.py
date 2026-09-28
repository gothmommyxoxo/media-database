import httpx

from app.barcode.providers.base import MetadataProvider
from app.barcode.schemas import BarcodeCandidate
from app.models.enums import MediaType

JIKAN_URL = "https://api.jikan.moe/v4/manga"


class JikanProvider(MetadataProvider):
    """Appendix A.3: unofficial MyAnimeList API, title-search fallback for MANGA with no usable
    ISBN, alongside AniList. Not used for BOOK or GRAPHIC_NOVEL (13's rationale)."""

    provider_name = "jikan"
    covers_media_types = [MediaType.MANGA]
    requires_api_key = False
    rate_limit_per_second = 1.0

    def _to_candidate(self, item: dict) -> BarcodeCandidate:
        authors = item.get("authors") or []
        return BarcodeCandidate(
            source_provider=self.provider_name,
            media_type=MediaType.MANGA,
            title=item.get("title", ""),
            subtitle=authors[0]["name"] if authors else None,
            external_id=str(item["mal_id"]) if item.get("mal_id") is not None else None,
            external_url=item.get("url"),
            cover_image_url=((item.get("images") or {}).get("jpg") or {}).get("image_url"),
            raw_attributes=item,
        )

    async def search_by_title(self, title: str, media_type: MediaType | None) -> list[BarcodeCandidate]:
        async with httpx.AsyncClient() as client:
            data = await self._get_json(client, JIKAN_URL, params={"q": title, "limit": 10})
        return [self._to_candidate(item) for item in data.get("data", [])]
