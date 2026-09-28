import json
from pathlib import Path

import httpx
import pytest
import respx

from app.barcode.providers.anilist import ANILIST_URL, AniListProvider
from app.barcode.providers.jikan import JIKAN_URL, JikanProvider
from app.models.enums import MediaType

FIXTURES = Path(__file__).parent.parent / "fixtures" / "providers"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.asyncio
@respx.mock
async def test_anilist_title_search_single_match():
    respx.post(ANILIST_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("anilist_title_single_match.json"))
    )

    candidates = await AniListProvider().search_by_title("Berserk", media_type=MediaType.MANGA)

    assert len(candidates) == 1
    assert candidates[0].media_type == MediaType.MANGA
    assert candidates[0].title == "Berserk"
    assert candidates[0].subtitle == "Kentaro Miura"


@pytest.mark.asyncio
@respx.mock
async def test_anilist_no_match_returns_empty_list():
    respx.post(ANILIST_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("anilist_title_no_match.json"))
    )

    candidates = await AniListProvider().search_by_title("Nonexistent Title", media_type=MediaType.MANGA)

    assert candidates == []


@pytest.mark.asyncio
@respx.mock
async def test_jikan_title_search_single_match():
    respx.get(JIKAN_URL).mock(return_value=httpx.Response(200, json=load_fixture("jikan_title_single_match.json")))

    candidates = await JikanProvider().search_by_title("Berserk", media_type=MediaType.MANGA)

    assert len(candidates) == 1
    assert candidates[0].title == "Berserk"
    assert candidates[0].subtitle == "Miura, Kentarou"


@pytest.mark.asyncio
@respx.mock
async def test_jikan_no_match_returns_empty_list():
    respx.get(JIKAN_URL).mock(return_value=httpx.Response(200, json=load_fixture("jikan_title_no_match.json")))

    candidates = await JikanProvider().search_by_title("Nonexistent Title", media_type=MediaType.MANGA)

    assert candidates == []
