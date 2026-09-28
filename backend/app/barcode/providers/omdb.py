import httpx

from app.barcode.providers.base import MetadataProvider
from app.barcode.schemas import BarcodeCandidate
from app.config import settings
from app.models.enums import MediaType

OMDB_URL = "https://www.omdbapi.com/"


class OMDbProvider(MetadataProvider):
    """Appendix A.2: title-search only, shared by BLU_RAY/DVD/VHS/VCD, same as TMDb -- OMDb has
    no physical-format concept either, so candidates are unclassified (media_type=None)."""

    provider_name = "omdb"
    covers_media_types = [MediaType.BLU_RAY, MediaType.DVD, MediaType.VHS, MediaType.VCD]
    requires_api_key = True
    rate_limit_per_second = None  # 1,000 req/day cap, no documented per-second limit

    def _to_candidate(self, result: dict) -> BarcodeCandidate:
        poster = result.get("Poster")
        return BarcodeCandidate(
            source_provider=self.provider_name,
            media_type=None,
            title=result.get("Title", ""),
            subtitle=result.get("Year"),
            external_id=result.get("imdbID"),
            external_url=f"https://www.imdb.com/title/{result['imdbID']}/" if result.get("imdbID") else None,
            cover_image_url=poster if poster and poster != "N/A" else None,
            raw_attributes=result,
        )

    async def search_by_title(self, title: str, media_type: MediaType | None) -> list[BarcodeCandidate]:
        async with httpx.AsyncClient() as client:
            data = await self._get_json(client, OMDB_URL, params={"apikey": settings.omdb_api_key, "s": title})
        if data.get("Response") != "True":
            return []
        return [self._to_candidate(r) for r in data.get("Search", [])]
