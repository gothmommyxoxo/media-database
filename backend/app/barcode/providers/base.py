from abc import ABC, abstractmethod

import httpx

from app.barcode.schemas import BarcodeCandidate
from app.config import settings
from app.models.enums import MediaType


class ProviderError(Exception):
    """Raised for any provider failure (timeout, rate limit, auth, malformed response).

    Section 5.2/6.4: the resolution algorithm catches this per-provider so one failure never
    blocks the others from contributing candidates.
    """


class MetadataProvider(ABC):
    provider_name: str
    covers_media_types: list[MediaType]
    requires_api_key: bool
    rate_limit_per_second: float | None

    def supports_barcode_lookup(self) -> bool:
        return False

    async def lookup_by_barcode(self, barcode: str) -> list[BarcodeCandidate]:
        raise NotImplementedError

    @abstractmethod
    async def search_by_title(self, title: str, media_type: MediaType | None) -> list[BarcodeCandidate]:
        raise NotImplementedError

    async def _get_json(self, client: httpx.AsyncClient, url: str, **kwargs) -> dict:
        try:
            response = await client.get(url, timeout=settings.provider_timeout_ms / 1000, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise ProviderError(f"{self.provider_name}: {exc}") from exc

    async def _post_json(self, client: httpx.AsyncClient, url: str, **kwargs) -> dict:
        try:
            response = await client.post(url, timeout=settings.provider_timeout_ms / 1000, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise ProviderError(f"{self.provider_name}: {exc}") from exc
