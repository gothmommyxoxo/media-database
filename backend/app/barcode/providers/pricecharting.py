import httpx

from app.barcode.providers.base import MetadataProvider
from app.barcode.schemas import BarcodeCandidate
from app.config import settings
from app.models.enums import MediaType

PRICECHARTING_URL = "https://www.pricecharting.com/api/product"


class PriceChartingProvider(MetadataProvider):
    """Appendix A.4: optional, paid provider with real direct barcode lookup and strong retro
    coverage. Disabled by default -- resolution.py only registers this provider when
    PRICECHARTING_API_KEY is set (13's rationale); the class itself has no opinion on that."""

    provider_name = "pricecharting"
    covers_media_types = [MediaType.VIDEO_GAME]
    requires_api_key = True
    rate_limit_per_second = None

    def supports_barcode_lookup(self) -> bool:
        return True

    def _to_candidate(self, result: dict) -> BarcodeCandidate:
        return BarcodeCandidate(
            source_provider=self.provider_name,
            media_type=MediaType.VIDEO_GAME,
            title=result.get("product-name", ""),
            subtitle=result.get("console-name"),
            external_id=result.get("id"),
            external_url=f"https://www.pricecharting.com/game/{result['id']}" if result.get("id") else None,
            cover_image_url=None,
            raw_attributes=result,
        )

    async def lookup_by_barcode(self, barcode: str) -> list[BarcodeCandidate]:
        async with httpx.AsyncClient() as client:
            data = await self._get_json(
                client, PRICECHARTING_URL, params={"t": settings.pricecharting_api_key, "upc": barcode}
            )
        if data.get("status") != "success":
            return []
        return [self._to_candidate(data)]

    async def search_by_title(self, title: str, media_type: MediaType | None) -> list[BarcodeCandidate]:
        return []
