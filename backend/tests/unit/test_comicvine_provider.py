import json
from pathlib import Path

import httpx
import pytest
import respx

from app.barcode.providers.comicvine import COMICVINE_URL, ComicVineProvider

FIXTURES = Path(__file__).parent.parent / "fixtures" / "providers"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.asyncio
@respx.mock
async def test_comicvine_title_search_single_match_is_unclassified():
    respx.get(COMICVINE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("comicvine_title_single_match.json"))
    )

    candidates = await ComicVineProvider().search_by_title("Batman #1", media_type=None)

    assert len(candidates) == 1
    assert candidates[0].media_type is None
    assert candidates[0].title == "Batman #1"
    assert candidates[0].subtitle == "Batman"


@pytest.mark.asyncio
@respx.mock
async def test_comicvine_no_match_returns_empty_list():
    respx.get(COMICVINE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("comicvine_title_no_match.json"))
    )

    candidates = await ComicVineProvider().search_by_title("Nonexistent Title", media_type=None)

    assert candidates == []
