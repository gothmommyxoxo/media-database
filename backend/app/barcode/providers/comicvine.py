import httpx

from app.barcode.providers.base import MetadataProvider
from app.barcode.schemas import BarcodeCandidate
from app.config import settings
from app.models.enums import MediaType

COMICVINE_URL = "https://comicvine.gamespot.com/api/search/"
USER_AGENT = "MediaDatabaseApp/0.1 (household-media-database; contact@example.invalid)"


class ComicVineProvider(MetadataProvider):
    """Appendix A.7: title/issue search for COMIC_BOOK (single issues) and, per Appendix A.3, as
    the GRAPHIC_NOVEL fallback when its ISBN goes unmatched in Google Books. No barcode-search
    endpoint exists (Appendix A.7), so results are always unclassified between the two -- the
    member confirms which one it is."""

    provider_name = "comicvine"
    covers_media_types = [MediaType.COMIC_BOOK, MediaType.GRAPHIC_NOVEL]
    requires_api_key = True
    rate_limit_per_second = 1.0  # ~200 req/resource/hour

    def _to_candidate(self, result: dict) -> BarcodeCandidate:
        volume = result.get("volume") or {}
        image = result.get("image") or {}
        return BarcodeCandidate(
            source_provider=self.provider_name,
            media_type=None,
            title=result.get("name") or volume.get("name") or "",
            subtitle=volume.get("name") if result.get("name") else None,
            external_id=str(result["id"]) if result.get("id") is not None else None,
            external_url=result.get("site_detail_url"),
            cover_image_url=image.get("medium_url"),
            raw_attributes=result,
        )

    async def search_by_title(self, title: str, media_type: MediaType | None) -> list[BarcodeCandidate]:
        async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}) as client:
            data = await self._get_json(
                client,
                COMICVINE_URL,
                params={
                    "api_key": settings.comicvine_api_key,
                    "format": "json",
                    "query": title,
                    "resources": "issue,volume",
                },
            )
        return [self._to_candidate(r) for r in data.get("results", [])]
