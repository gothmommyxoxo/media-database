import httpx
import pytest
import respx

from app.barcode.providers.comicvine import COMICVINE_URL
from app.barcode.providers.tmdb import TMDB_SEARCH_URL
from app.barcode.providers.upc_general import UPCITEMDB_URL
from app.barcode.resolution import resolve_barcode
from tests.provider_mocks import load_fixture, mock_all_providers_empty


@pytest.mark.asyncio
@respx.mock
async def test_movie_category_hint_triggers_tmdb_title_search(db_session):
    mock_all_providers_empty()
    respx.get(UPCITEMDB_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "code": "OK",
                "total": 1,
                "items": [{"upc": "025192107822", "title": "Brazil", "category": "Movies & TV > Blu-ray"}],
            },
        )
    )
    respx.get(TMDB_SEARCH_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("tmdb_title_single_match.json"))
    )

    result = await resolve_barcode(db_session, "025192107822")

    sources = {c.source_provider for c in result.candidates}
    assert "tmdb" in sources
    assert result.requires_manual_entry is False


@pytest.mark.asyncio
@respx.mock
async def test_comic_category_hint_triggers_comicvine_title_search(db_session):
    mock_all_providers_empty()
    respx.get(UPCITEMDB_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "code": "OK",
                "total": 1,
                "items": [{"upc": "761941300085", "title": "Batman #1", "category": "Media > Books > Comics"}],
            },
        )
    )
    respx.get(COMICVINE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("comicvine_title_single_match.json"))
    )

    result = await resolve_barcode(db_session, "761941300085")

    sources = {c.source_provider for c in result.candidates}
    assert "comicvine" in sources


@pytest.mark.asyncio
@respx.mock
async def test_step4_is_skipped_when_something_already_classified(db_session):
    """A CD barcode that MusicBrainz already classified should never reach TMDb/ComicVine/etc.,
    even if UPCitemdb's raw category happens to look plausible for another group too."""
    mock_all_providers_empty()
    respx.get(UPCITEMDB_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "code": "OK",
                "total": 1,
                "items": [{"upc": "724384960650", "title": "Discovery", "category": "Media > Music CDs"}],
            },
        )
    )
    respx.get("https://musicbrainz.org/ws/2/release/").mock(
        return_value=httpx.Response(200, json=load_fixture("musicbrainz_barcode_single_match.json"))
    )
    tmdb_route = respx.get(TMDB_SEARCH_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("tmdb_title_single_match.json"))
    )

    result = await resolve_barcode(db_session, "724384960650")

    assert tmdb_route.call_count == 0
    assert any(c.media_type == "CD" for c in result.candidates)
