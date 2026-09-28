import httpx

from app.barcode.providers.base import MetadataProvider
from app.barcode.schemas import BarcodeCandidate
from app.config import settings
from app.models.enums import MediaType

SCANDEX_URL = "https://scandex.gamery.app/api/v2/lookup"

# NOTE: spec research (Appendix A.4) confirmed ScanDex's endpoint, Bearer-token auth, and that it
# exists as a genuine purpose-built game-barcode API, but did not pin down its exact response
# schema from official docs. The shape below is a best-effort guess (a `results` array of
# name/platform/image_url/url) -- verify against ScanDex's actual docs and update this parser
# before depending on it in production. If the shape is wrong, `_get_json`'s JSON parsing or the
# dict lookups below will raise, which the resolution algorithm already treats as a ProviderError
# (6.4) -- so a schema mismatch degrades to "ScanDex contributed nothing" rather than crashing.
class ScanDexProvider(MetadataProvider):
    """Appendix A.4: purpose-built direct barcode lookup for physical video games. Free tier is
    explicitly time-limited ("launch period"), not guaranteed permanent -- see 13's rationale for
    why it's included anyway (the pipeline degrades gracefully without it)."""

    provider_name = "scandex"
    covers_media_types = [MediaType.VIDEO_GAME]
    requires_api_key = True
    rate_limit_per_second = None

    def supports_barcode_lookup(self) -> bool:
        return True

    def _to_candidate(self, result: dict) -> BarcodeCandidate:
        return BarcodeCandidate(
            source_provider=self.provider_name,
            media_type=MediaType.VIDEO_GAME,
            title=result.get("name", ""),
            subtitle=result.get("platform"),
            external_id=result.get("id"),
            external_url=result.get("url"),
            cover_image_url=result.get("image_url"),
            raw_attributes=result,
        )

    async def lookup_by_barcode(self, barcode: str) -> list[BarcodeCandidate]:
        headers = {"Authorization": f"Bearer {settings.scandex_api_key}"}
        async with httpx.AsyncClient(headers=headers) as client:
            data = await self._get_json(client, SCANDEX_URL, params={"value": barcode})
        return [self._to_candidate(r) for r in data.get("results", [])]

    async def search_by_title(self, title: str, media_type: MediaType | None) -> list[BarcodeCandidate]:
        return []
