from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.barcode.category_routing import plausible_groups_for
from app.barcode.dedup import deduplicate
from app.barcode.normalization import normalize_barcode
from app.barcode.providers.anilist import AniListProvider
from app.barcode.providers.base import MetadataProvider, ProviderError
from app.barcode.providers.comicvine import ComicVineProvider
from app.barcode.providers.discogs import DiscogsProvider
from app.barcode.providers.google_books import GoogleBooksProvider
from app.barcode.providers.igdb import IGDBProvider
from app.barcode.providers.jikan import JikanProvider
from app.barcode.providers.musicbrainz import MusicBrainzProvider
from app.barcode.providers.omdb import OMDbProvider
from app.barcode.providers.pricecharting import PriceChartingProvider
from app.barcode.providers.rawg import RAWGProvider
from app.barcode.providers.scandex import ScanDexProvider
from app.barcode.providers.tmdb import TMDbProvider
from app.barcode.providers.upc_general import UPCitemdbProvider
from app.barcode.schemas import BarcodeCandidate, ResolutionResult
from app.collection.schemas import MediaItemResponse
from app.config import settings
from app.models import BarcodeCache, MediaItem

# Appendix A.1: queried first, unconditionally, for every barcode (Section 5.3 Step 1).
GENERAL_BARCODE_PROVIDERS: list[MetadataProvider] = [UPCitemdbProvider()]

# Providers that support direct barcode search, queried unconditionally (Section 5.3 Step 2).
# GoogleBooksProvider being in this list already satisfies Step 3's "always query Google Books
# directly for ISBN-13 barcodes" -- it is not gated by media type, so every barcode reaches it.
DIRECT_BARCODE_PROVIDERS: list[MetadataProvider] = [
    MusicBrainzProvider(),
    GoogleBooksProvider(),
    DiscogsProvider(),
    ScanDexProvider(),
]
# PriceCharting is the one provider the spec singles out as disabled-by-default (13's rationale,
# Appendix A.4): it is only ever registered -- let alone called -- when a paid key is configured.
if settings.pricecharting_api_key:
    DIRECT_BARCODE_PROVIDERS.append(PriceChartingProvider())

# Section 5.3 Step 4: title-search providers tried when nothing classified the item yet, keyed by
# the category-hint groups from app.barcode.category_routing.
TITLE_SEARCH_PROVIDERS_BY_GROUP: dict[str, list[MetadataProvider]] = {
    "movies": [TMDbProvider(), OMDbProvider()],
    "video_games": [IGDBProvider(), RAWGProvider()],
    "comics": [ComicVineProvider()],  # also GRAPHIC_NOVEL's ISBN-miss fallback, Appendix A.3
    "books": [AniListProvider(), JikanProvider()],  # MANGA fallback only, not BOOK (13's rationale)
}


def _as_utc(dt: datetime) -> datetime:
    """SQLite (used in this sandbox in place of MySQL, see tests/conftest.py) does not round-trip
    timezone info, so naive datetimes read back from the DB are assumed to be UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


async def fetch_fresh_candidates(barcode: str) -> list[BarcodeCandidate]:
    results: list[BarcodeCandidate] = []

    # Step 1: general UPC/EAN lookup, kept separately since Step 4 needs its raw title/category.
    step1_results: list[BarcodeCandidate] = []
    for provider in GENERAL_BARCODE_PROVIDERS:
        try:
            provider_results = await provider.lookup_by_barcode(barcode)
            step1_results.extend(provider_results)
            results.extend(provider_results)
        except ProviderError:
            continue  # Section 6.4: one provider's failure never blocks the others

    # Step 2 (and, since GoogleBooksProvider is in this list, Step 3): direct barcode search.
    for provider in DIRECT_BARCODE_PROVIDERS:
        try:
            results.extend(await provider.lookup_by_barcode(barcode))
        except ProviderError:
            continue

    # Step 4: nothing classified the item yet -- use Step 1's raw title/category to try
    # category-plausible title-search providers.
    if step1_results and not any(c.media_type is not None for c in results):
        raw_title = step1_results[0].title
        category_hint = step1_results[0].raw_attributes.get("category")
        for group in plausible_groups_for(category_hint):
            for provider in TITLE_SEARCH_PROVIDERS_BY_GROUP.get(group, []):
                try:
                    results.extend(await provider.search_by_title(raw_title, media_type=None))
                except ProviderError:
                    continue

    return deduplicate(results)


def _upsert_cache(db: Session, barcode: str, candidates: list[BarcodeCandidate], cached: BarcodeCache | None) -> None:
    if cached is None:
        cached = BarcodeCache(barcode=barcode, refresh_count=0)
        db.add(cached)
    cached.candidates = [c.model_dump(mode="json") for c in candidates]
    cached.last_refreshed_at = datetime.now(timezone.utc)
    cached.refresh_count = (cached.refresh_count or 0) + 1
    db.commit()


async def resolve_barcode(db: Session, barcode: str) -> ResolutionResult:
    normalized = normalize_barcode(barcode)
    cache_ttl = timedelta(days=settings.cache_ttl_days)

    cached = db.get(BarcodeCache, normalized)
    if cached is not None and _as_utc(cached.last_refreshed_at) > datetime.now(timezone.utc) - cache_ttl:
        candidates = [BarcodeCandidate(**c) for c in cached.candidates]
    else:
        fresh = await fetch_fresh_candidates(normalized)
        existing = [BarcodeCandidate(**c) for c in cached.candidates] if cached is not None else []
        # Historical candidates persist across different media types too (3.4's accumulation guarantee).
        candidates = deduplicate(existing + fresh)
        _upsert_cache(db, normalized, candidates, cached)

    owned_matches = db.query(MediaItem).filter(MediaItem.barcode == normalized).all()

    return ResolutionResult(
        candidates=candidates,
        owned_matches=[MediaItemResponse.model_validate(item).model_dump(mode="json") for item in owned_matches],
        requires_manual_entry=not candidates and not owned_matches,
    )
