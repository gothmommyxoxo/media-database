import httpx

from app.barcode.providers.base import MetadataProvider
from app.barcode.schemas import BarcodeCandidate
from app.config import settings
from app.models.enums import MediaType

RAWG_URL = "https://api.rawg.io/api/games"


class RAWGProvider(MetadataProvider):
    """Appendix A.4: title-search-only video game catalog, alongside IGDB."""

    provider_name = "rawg"
    covers_media_types = [MediaType.VIDEO_GAME]
    requires_api_key = True
    rate_limit_per_second = None  # 20,000 req/month cap

    def _to_candidate(self, result: dict) -> BarcodeCandidate:
        platforms = result.get("platforms") or []
        platform_names = ", ".join(p["platform"]["name"] for p in platforms if p.get("platform"))
        return BarcodeCandidate(
            source_provider=self.provider_name,
            media_type=MediaType.VIDEO_GAME,
            title=result.get("name", ""),
            subtitle=platform_names or None,
            external_id=str(result["id"]) if result.get("id") is not None else None,
            external_url=f"https://rawg.io/games/{result['id']}" if result.get("id") is not None else None,
            cover_image_url=result.get("background_image"),
            raw_attributes=result,
        )

    async def search_by_title(self, title: str, media_type: MediaType | None) -> list[BarcodeCandidate]:
        async with httpx.AsyncClient() as client:
            data = await self._get_json(client, RAWG_URL, params={"key": settings.rawg_api_key, "search": title})
        return [self._to_candidate(r) for r in data.get("results", [])]
