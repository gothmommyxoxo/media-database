import json
from pathlib import Path

import httpx
import pytest
import respx

from app.barcode.providers.omdb import OMDB_URL, OMDbProvider
from app.barcode.providers.tmdb import TMDB_SEARCH_URL, TMDbProvider

FIXTURES = Path(__file__).parent.parent / "fixtures" / "providers"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.asyncio
@respx.mock
async def test_tmdb_title_search_single_match_is_unclassified():
    respx.get(TMDB_SEARCH_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("tmdb_title_single_match.json"))
    )

    candidates = await TMDbProvider().search_by_title("Brazil", media_type=None)

    assert len(candidates) == 1
    assert candidates[0].media_type is None
    assert candidates[0].title == "Brazil"


@pytest.mark.asyncio
@respx.mock
async def test_tmdb_no_match_returns_empty_list():
    respx.get(TMDB_SEARCH_URL).mock(return_value=httpx.Response(200, json=load_fixture("tmdb_title_no_match.json")))

    candidates = await TMDbProvider().search_by_title("Nonexistent Title", media_type=None)

    assert candidates == []


@pytest.mark.asyncio
@respx.mock
async def test_omdb_title_search_single_match():
    respx.get(OMDB_URL).mock(return_value=httpx.Response(200, json=load_fixture("omdb_title_single_match.json")))

    candidates = await OMDbProvider().search_by_title("Brazil", media_type=None)

    assert len(candidates) == 1
    assert candidates[0].external_id == "tt0088846"


@pytest.mark.asyncio
@respx.mock
async def test_omdb_no_match_returns_empty_list():
    respx.get(OMDB_URL).mock(return_value=httpx.Response(200, json=load_fixture("omdb_title_no_match.json")))

    candidates = await OMDbProvider().search_by_title("Nonexistent Title", media_type=None)

    assert candidates == []
