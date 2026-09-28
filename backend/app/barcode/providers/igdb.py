from datetime import datetime, timedelta, timezone

import httpx

from app.barcode.providers.base import MetadataProvider
from app.barcode.schemas import BarcodeCandidate
from app.config import settings
from app.models.enums import MediaType

TWITCH_OAUTH_URL = "https://id.twitch.tv/oauth2/token"
IGDB_GAMES_URL = "https://api.igdb.com/v4/games"


class IGDBProvider(MetadataProvider):
    """Appendix A.4: title-search-only video game catalog, authenticated via a Twitch developer
    app-access OAuth token (free). The token is cached in-instance and refreshed once expired,
    since IGDBProvider is a long-lived singleton in resolution.py's provider registry."""

    provider_name = "igdb"
    covers_media_types = [MediaType.VIDEO_GAME]
    requires_api_key = True
    rate_limit_per_second = 4.0

    def __init__(self) -> None:
        self._token: str | None = None
        self._token_expires_at: datetime | None = None

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        if self._token and self._token_expires_at and datetime.now(timezone.utc) < self._token_expires_at:
            return self._token

        data = await self._post_json(
            client,
            TWITCH_OAUTH_URL,
            params={
                "client_id": settings.igdb_client_id,
                "client_secret": settings.igdb_client_secret,
                "grant_type": "client_credentials",
            },
        )
        self._token = data["access_token"]
        # Refresh a minute early rather than exactly at expiry.
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"] - 60)
        return self._token

    def _to_candidate(self, result: dict) -> BarcodeCandidate:
        platforms = result.get("platforms") or []
        platform_names = ", ".join(p.get("name", "") for p in platforms)
        cover_url = (result.get("cover") or {}).get("url")
        return BarcodeCandidate(
            source_provider=self.provider_name,
            media_type=MediaType.VIDEO_GAME,
            title=result.get("name", ""),
            subtitle=platform_names or None,
            external_id=str(result["id"]) if result.get("id") is not None else None,
            external_url=result.get("url"),
            cover_image_url=f"https:{cover_url}" if cover_url else None,
            raw_attributes=result,
        )

    async def search_by_title(self, title: str, media_type: MediaType | None) -> list[BarcodeCandidate]:
        escaped_title = title.replace('"', '\\"')
        async with httpx.AsyncClient() as client:
            token = await self._get_token(client)
            headers = {
                "Client-ID": settings.igdb_client_id,
                "Authorization": f"Bearer {token}",
            }
            data = await self._post_json(
                client,
                IGDB_GAMES_URL,
                headers=headers,
                content=f'search "{escaped_title}"; fields name,url,cover.url,platforms.name; limit 10;',
            )
        return [self._to_candidate(r) for r in data]
