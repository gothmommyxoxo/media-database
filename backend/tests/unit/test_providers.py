import json
from pathlib import Path

import httpx
import pytest
import respx

from app.barcode.providers.base import ProviderError
from app.barcode.providers.google_books import GOOGLE_BOOKS_URL, GoogleBooksProvider
from app.barcode.providers.musicbrainz import MUSICBRAINZ_URL, MusicBrainzProvider
from app.barcode.providers.upc_general import UPCITEMDB_URL, UPCitemdbProvider
from app.models.enums import MediaType

FIXTURES = Path(__file__).parent.parent / "fixtures" / "providers"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.asyncio
@respx.mock
async def test_musicbrainz_single_match_maps_cd_format():
    respx.get(MUSICBRAINZ_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("musicbrainz_barcode_single_match.json"))
    )

    candidates = await MusicBrainzProvider().lookup_by_barcode("724384960650")

    assert len(candidates) == 1
    assert candidates[0].media_type == MediaType.CD
    assert candidates[0].title == "Discovery"
    assert candidates[0].subtitle == "Daft Punk"
    assert candidates[0].external_id == "09ffa920-becb-4e2f-b511-01aa50fb2cb3"


@pytest.mark.asyncio
@respx.mock
async def test_musicbrainz_multi_format_match_maps_each_release_independently():
    respx.get(MUSICBRAINZ_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("musicbrainz_barcode_multi_format_match.json"))
    )

    candidates = await MusicBrainzProvider().lookup_by_barcode("724384960650")

    media_types = {c.media_type for c in candidates}
    assert media_types == {MediaType.CD, MediaType.VINYL}


@pytest.mark.asyncio
@respx.mock
async def test_musicbrainz_unmapped_format_yields_none_media_type():
    respx.get(MUSICBRAINZ_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("musicbrainz_barcode_unmapped_format.json"))
    )

    candidates = await MusicBrainzProvider().lookup_by_barcode("724384960651")

    assert candidates[0].media_type is None


@pytest.mark.asyncio
@respx.mock
async def test_musicbrainz_no_match_returns_empty_list():
    respx.get(MUSICBRAINZ_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("musicbrainz_barcode_no_match.json"))
    )

    candidates = await MusicBrainzProvider().lookup_by_barcode("000000000000")

    assert candidates == []


@pytest.mark.asyncio
@respx.mock
async def test_musicbrainz_rate_limited_raises_provider_error():
    respx.get(MUSICBRAINZ_URL).mock(return_value=httpx.Response(429, json={"error": "rate limited"}))

    with pytest.raises(ProviderError):
        await MusicBrainzProvider().lookup_by_barcode("724384960650")


@pytest.mark.asyncio
@respx.mock
async def test_google_books_isbn_match():
    respx.get(GOOGLE_BOOKS_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("google_books_isbn_single_match.json"))
    )

    candidates = await GoogleBooksProvider().lookup_by_barcode("9781593070209")

    assert len(candidates) == 1
    assert candidates[0].media_type is None  # ISBN alone can't distinguish MANGA/BOOK/GRAPHIC_NOVEL
    assert candidates[0].title == "Berserk, Vol. 1"
    assert candidates[0].subtitle == "Kentaro Miura"


@pytest.mark.asyncio
@respx.mock
async def test_google_books_no_match_returns_empty_list():
    respx.get(GOOGLE_BOOKS_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("google_books_isbn_no_match.json"))
    )

    candidates = await GoogleBooksProvider().lookup_by_barcode("0000000000000")

    assert candidates == []


@pytest.mark.asyncio
@respx.mock
async def test_upcitemdb_single_match():
    respx.get(UPCITEMDB_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("upcitemdb_lookup_single_match.json"))
    )

    candidates = await UPCitemdbProvider().lookup_by_barcode("724384960650")

    assert len(candidates) == 1
    assert candidates[0].media_type is None
    assert candidates[0].title == "Discovery - Daft Punk"


@pytest.mark.asyncio
@respx.mock
async def test_upcitemdb_no_match_returns_empty_list():
    respx.get(UPCITEMDB_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("upcitemdb_lookup_no_match.json"))
    )

    candidates = await UPCitemdbProvider().lookup_by_barcode("000000000000")

    assert candidates == []
