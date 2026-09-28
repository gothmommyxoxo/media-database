import httpx

from app.barcode.providers.base import MetadataProvider
from app.barcode.schemas import BarcodeCandidate
from app.models.enums import MediaType

UPCITEMDB_URL = "https://api.upcitemdb.com/prod/trial/lookup"


class UPCitemdbProvider(MetadataProvider):
    """Appendix A.1: general UPC/EAN lookup, queried first regardless of media type (5.3 Step 1)."""

    provider_name = "upcitemdb"
    covers_media_types: list[MediaType] = []
    requires_api_key = False
    rate_limit_per_second = 6 / 60  # 6 requests/min burst cap

    def supports_barcode_lookup(self) -> bool:
        return True

    async def lookup_by_barcode(self, barcode: str) -> list[BarcodeCandidate]:
        async with httpx.AsyncClient() as client:
            data = await self._get_json(client, UPCITEMDB_URL, params={"upc": barcode})

        candidates = []
        for item in data.get("items", []):
            candidates.append(
                BarcodeCandidate(
                    source_provider=self.provider_name,
                    media_type=None,
                    title=item.get("title", ""),
                    external_id=item.get("upc") or item.get("ean"),
                    raw_attributes=item,
                )
            )
        return candidates

    async def search_by_title(self, title: str, media_type: MediaType | None) -> list[BarcodeCandidate]:
        # Not used for title search: Section 5.3 Step 4 fans out to category-specific providers,
        # not back to the general UPC lookup providers.
        return []
