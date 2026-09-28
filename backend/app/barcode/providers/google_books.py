import httpx

from app.barcode.providers.base import MetadataProvider
from app.barcode.schemas import BarcodeCandidate
from app.config import settings
from app.models.enums import MediaType

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"


class GoogleBooksProvider(MetadataProvider):
    """Appendix A.3: ISBN-based lookup shared by MANGA, BOOK, and GRAPHIC_NOVEL.

    A single ISBN cannot tell manga, a novel, and a graphic novel apart, so candidates are
    returned with media_type=None; the member classifies the item when selecting it (3.1).
    """

    provider_name = "google_books"
    covers_media_types = [MediaType.MANGA, MediaType.BOOK, MediaType.GRAPHIC_NOVEL]
    requires_api_key = False
    rate_limit_per_second = 1.0

    def supports_barcode_lookup(self) -> bool:
        return True

    def _params(self, query: str) -> dict:
        params = {"q": query}
        if settings.google_books_api_key:
            params["key"] = settings.google_books_api_key
        return params

    def _to_candidate(self, item: dict) -> BarcodeCandidate:
        info = item.get("volumeInfo", {})
        authors = info.get("authors") or []
        return BarcodeCandidate(
            source_provider=self.provider_name,
            media_type=None,
            title=info.get("title", ""),
            subtitle=", ".join(authors) or None,
            external_id=item.get("id"),
            external_url=info.get("infoLink"),
            cover_image_url=(info.get("imageLinks") or {}).get("thumbnail"),
            raw_attributes=info,
        )

    async def lookup_by_barcode(self, barcode: str) -> list[BarcodeCandidate]:
        async with httpx.AsyncClient() as client:
            data = await self._get_json(client, GOOGLE_BOOKS_URL, params=self._params(f"isbn:{barcode}"))
        return [self._to_candidate(item) for item in data.get("items", [])]

    async def search_by_title(self, title: str, media_type: MediaType | None) -> list[BarcodeCandidate]:
        async with httpx.AsyncClient() as client:
            data = await self._get_json(client, GOOGLE_BOOKS_URL, params=self._params(title))
        return [self._to_candidate(item) for item in data.get("items", [])]
