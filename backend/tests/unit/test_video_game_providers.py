import json
from pathlib import Path

import httpx
import pytest
import respx

from app.barcode.providers.igdb import IGDB_GAMES_URL, TWITCH_OAUTH_URL, IGDBProvider
from app.barcode.providers.rawg import RAWG_URL, RAWGProvider
from app.barcode.providers.scandex import SCANDEX_URL, ScanDexProvider
from app.models.enums import MediaType

FIXTURES = Path(__file__).parent.parent / "fixtures" / "providers"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.asyncio
@respx.mock
async def test_scandex_barcode_single_match():
    respx.get(SCANDEX_URL).mock(return_value=httpx.Response(200, json=load_fixture("scandex_barcode_single_match.json")))

    candidates = await ScanDexProvider().lookup_by_barcode("045496594454")

    assert len(candidates) == 1
    assert candidates[0].media_type == MediaType.VIDEO_GAME
    assert candidates[0].title == "Super Mario Odyssey"
    assert candidates[0].subtitle == "Nintendo Switch"


@pytest.mark.asyncio
@respx.mock
async def test_scandex_no_match_returns_empty_list():
    respx.get(SCANDEX_URL).mock(return_value=httpx.Response(200, json=load_fixture("scandex_barcode_no_match.json")))

    candidates = await ScanDexProvider().lookup_by_barcode("000000000000")

    assert candidates == []


@pytest.mark.asyncio
@respx.mock
async def test_rawg_title_search_single_match():
    respx.get(RAWG_URL).mock(return_value=httpx.Response(200, json=load_fixture("rawg_title_single_match.json")))

    candidates = await RAWGProvider().search_by_title("Grand Theft Auto V", media_type=MediaType.VIDEO_GAME)

    assert len(candidates) == 1
    assert candidates[0].media_type == MediaType.VIDEO_GAME
    assert "PlayStation 4" in candidates[0].subtitle


@pytest.mark.asyncio
@respx.mock
async def test_rawg_no_match_returns_empty_list():
    respx.get(RAWG_URL).mock(return_value=httpx.Response(200, json=load_fixture("rawg_title_no_match.json")))

    candidates = await RAWGProvider().search_by_title("Nonexistent Title", media_type=MediaType.VIDEO_GAME)

    assert candidates == []


@pytest.mark.asyncio
@respx.mock
async def test_igdb_fetches_oauth_token_then_searches():
    token_route = respx.post(TWITCH_OAUTH_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("igdb_oauth_token.json"))
    )
    respx.post(IGDB_GAMES_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("igdb_title_single_match.json"))
    )

    provider = IGDBProvider()
    candidates = await provider.search_by_title("The Witcher 3", media_type=MediaType.VIDEO_GAME)

    assert token_route.call_count == 1
    assert len(candidates) == 1
    assert candidates[0].title == "The Witcher 3: Wild Hunt"
    assert candidates[0].cover_image_url.startswith("https://")


@pytest.mark.asyncio
@respx.mock
async def test_igdb_reuses_cached_token_across_calls():
    token_route = respx.post(TWITCH_OAUTH_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("igdb_oauth_token.json"))
    )
    respx.post(IGDB_GAMES_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("igdb_title_single_match.json"))
    )

    provider = IGDBProvider()
    await provider.search_by_title("The Witcher 3", media_type=MediaType.VIDEO_GAME)
    await provider.search_by_title("The Witcher 3", media_type=MediaType.VIDEO_GAME)

    assert token_route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_igdb_no_match_returns_empty_list():
    respx.post(TWITCH_OAUTH_URL).mock(return_value=httpx.Response(200, json=load_fixture("igdb_oauth_token.json")))
    respx.post(IGDB_GAMES_URL).mock(return_value=httpx.Response(200, json=load_fixture("igdb_title_no_match.json")))

    candidates = await IGDBProvider().search_by_title("Nonexistent Title", media_type=MediaType.VIDEO_GAME)

    assert candidates == []
