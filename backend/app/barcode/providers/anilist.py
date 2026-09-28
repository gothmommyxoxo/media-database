import httpx

from app.barcode.providers.base import MetadataProvider
from app.barcode.schemas import BarcodeCandidate
from app.models.enums import MediaType

ANILIST_URL = "https://graphql.anilist.co"

SEARCH_QUERY = """
query ($search: String) {
  Page(perPage: 10) {
    media(search: $search, type: MANGA) {
      id
      format
      siteUrl
      title { romaji english }
      coverImage { large }
      staff(perPage: 1) { edges { node { name { full } } } }
    }
  }
}
"""


class AniListProvider(MetadataProvider):
    """Appendix A.3: title-search fallback for MANGA volumes with no usable ISBN. Not used for
    BOOK or GRAPHIC_NOVEL (13's rationale)."""

    provider_name = "anilist"
    covers_media_types = [MediaType.MANGA]
    requires_api_key = False
    rate_limit_per_second = 1.5  # 90 req/min

    def _to_candidate(self, media: dict) -> BarcodeCandidate:
        title = media.get("title", {})
        staff_edges = (media.get("staff") or {}).get("edges") or []
        author = staff_edges[0]["node"]["name"]["full"] if staff_edges else None
        return BarcodeCandidate(
            source_provider=self.provider_name,
            media_type=MediaType.MANGA,
            title=title.get("english") or title.get("romaji") or "",
            subtitle=author,
            external_id=str(media["id"]) if media.get("id") is not None else None,
            external_url=media.get("siteUrl"),
            cover_image_url=(media.get("coverImage") or {}).get("large"),
            raw_attributes=media,
        )

    async def search_by_title(self, title: str, media_type: MediaType | None) -> list[BarcodeCandidate]:
        async with httpx.AsyncClient() as client:
            data = await self._post_json(
                client,
                ANILIST_URL,
                json={"query": SEARCH_QUERY, "variables": {"search": title}},
            )
        media_list = (((data.get("data") or {}).get("Page") or {}).get("media")) or []
        return [self._to_candidate(m) for m in media_list]
