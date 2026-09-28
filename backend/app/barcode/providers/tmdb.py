import httpx

from app.barcode.providers.base import MetadataProvider
from app.barcode.schemas import BarcodeCandidate
from app.config import settings
from app.models.enums import MediaType

TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/multi"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w342"

# Per Appendix A.2's TMDb attribution requirement: any screen that shows TMDb-sourced data must
# display this notice. Enforced at the frontend, not here -- this constant documents the exact
# required wording so it isn't paraphrased incorrectly.
TMDB_ATTRIBUTION_NOTICE = "This product uses the TMDB API but is not endorsed or certified by TMDB."


class TMDbProvider(MetadataProvider):
    """Appendix A.2: title-search only, shared by BLU_RAY/DVD/VHS/VCD -- TMDb has no concept of
    physical format, so candidates are returned unclassified (media_type=None) for the member to
    assign the correct format (3.1's note on anime titles applies here too)."""

    provider_name = "tmdb"
    covers_media_types = [MediaType.BLU_RAY, MediaType.DVD, MediaType.VHS, MediaType.VCD]
    requires_api_key = True
    rate_limit_per_second = 40.0

    def _to_candidate(self, result: dict) -> BarcodeCandidate:
        title = result.get("title") or result.get("name") or ""
        poster_path = result.get("poster_path")
        return BarcodeCandidate(
            source_provider=self.provider_name,
            media_type=None,
            title=title,
            subtitle=result.get("release_date") or result.get("first_air_date"),
            external_id=str(result["id"]) if result.get("id") is not None else None,
            external_url=f"https://www.themoviedb.org/{result.get('media_type', 'movie')}/{result.get('id')}"
            if result.get("id") is not None
            else None,
            cover_image_url=f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else None,
            raw_attributes=result,
        )

    async def search_by_title(self, title: str, media_type: MediaType | None) -> list[BarcodeCandidate]:
        async with httpx.AsyncClient() as client:
            data = await self._get_json(
                client,
                TMDB_SEARCH_URL,
                params={"query": title, "api_key": settings.tmdb_api_key},
            )
        results = [r for r in data.get("results", []) if r.get("media_type") in ("movie", "tv")]
        return [self._to_candidate(r) for r in results]
