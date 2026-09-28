from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

from app.barcode.providers.google_books import GOOGLE_BOOKS_URL
from app.barcode.providers.musicbrainz import MUSICBRAINZ_URL
from app.barcode.providers.upc_general import UPCITEMDB_URL
from app.barcode.resolution import resolve_barcode
from app.models import BarcodeCache, ItemSource, MediaItem, MediaType, User
from tests.provider_mocks import load_fixture, mock_all_providers_empty


@pytest.mark.asyncio
@respx.mock
async def test_zero_candidates_and_zero_owned_requires_manual_entry(db_session):
    mock_all_providers_empty()

    result = await resolve_barcode(db_session, "000000000000")

    assert result.candidates == []
    assert result.owned_matches == []
    assert result.requires_manual_entry is True


@pytest.mark.asyncio
@respx.mock
async def test_returns_owned_matches_and_candidates_together(db_session):
    user = User(username="alice", display_name="Alice", password_hash="x")
    db_session.add(user)
    db_session.commit()
    owned = MediaItem(
        media_type=MediaType.CD,
        title="Discovery",
        barcode="724384960650",
        source=ItemSource.MANUAL,
        added_by=user.id,
    )
    db_session.add(owned)
    db_session.commit()

    mock_all_providers_empty()
    respx.get(MUSICBRAINZ_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("musicbrainz_barcode_single_match.json"))
    )

    result = await resolve_barcode(db_session, "724384960650")

    assert result.requires_manual_entry is False
    assert len(result.owned_matches) == 1
    assert result.owned_matches[0]["id"] == owned.id
    assert len(result.candidates) == 1
    assert result.candidates[0].media_type == "CD"


@pytest.mark.asyncio
@respx.mock
async def test_one_provider_failure_does_not_block_others(db_session):
    mock_all_providers_empty()
    respx.get(MUSICBRAINZ_URL).mock(return_value=httpx.Response(500))
    respx.get(GOOGLE_BOOKS_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("google_books_isbn_single_match.json"))
    )

    result = await resolve_barcode(db_session, "9781593070209")

    assert result.requires_manual_entry is False
    assert len(result.candidates) == 1
    assert result.candidates[0].source_provider == "google_books"


@pytest.mark.asyncio
@respx.mock
async def test_cache_served_within_ttl_skips_provider_calls(db_session):
    barcode = "724384960650"
    cached_candidate = {
        "source_provider": "musicbrainz",
        "media_type": "CD",
        "title": "Discovery",
        "subtitle": "Daft Punk",
        "external_id": "09ffa920-becb-4e2f-b511-01aa50fb2cb3",
        "external_url": None,
        "cover_image_url": None,
        "raw_attributes": {},
    }
    db_session.add(
        BarcodeCache(
            barcode=barcode,
            candidates=[cached_candidate],
            last_refreshed_at=datetime.now(timezone.utc) - timedelta(days=1),
            refresh_count=1,
        )
    )
    db_session.commit()

    mb_route = respx.get(MUSICBRAINZ_URL).mock(return_value=httpx.Response(500))
    gb_route = respx.get(GOOGLE_BOOKS_URL).mock(return_value=httpx.Response(500))
    upc_route = respx.get(UPCITEMDB_URL).mock(return_value=httpx.Response(500))

    result = await resolve_barcode(db_session, barcode)

    assert result.candidates[0].title == "Discovery"
    assert mb_route.call_count == 0
    assert gb_route.call_count == 0
    assert upc_route.call_count == 0


@pytest.mark.asyncio
@respx.mock
async def test_reused_barcode_retains_historical_candidates_across_media_types(db_session):
    barcode = "724384960650"
    old_candidate = {
        "source_provider": "some_other_provider",
        "media_type": "VIDEO_GAME",
        "title": "An unrelated game that collided on this barcode",
        "subtitle": None,
        "external_id": "old-1",
        "external_url": None,
        "cover_image_url": None,
        "raw_attributes": {},
    }
    db_session.add(
        BarcodeCache(
            barcode=barcode,
            candidates=[old_candidate],
            last_refreshed_at=datetime.now(timezone.utc) - timedelta(days=999),  # stale, forces refresh
            refresh_count=1,
        )
    )
    db_session.commit()

    mock_all_providers_empty()
    respx.get(MUSICBRAINZ_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("musicbrainz_barcode_single_match.json"))
    )

    result = await resolve_barcode(db_session, barcode)

    media_types = {c.media_type for c in result.candidates}
    assert media_types == {"VIDEO_GAME", "CD"}
