import json
from pathlib import Path

import httpx
import pytest
import respx

from app.barcode.providers.discogs import DISCOGS_URL, DiscogsProvider
from app.models.enums import MediaType

FIXTURES = Path(__file__).parent.parent / "fixtures" / "providers"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.asyncio
@respx.mock
async def test_discogs_single_match_maps_vinyl_format():
    respx.get(DISCOGS_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("discogs_barcode_single_match.json"))
    )

    candidates = await DiscogsProvider().lookup_by_barcode("724384960650")

    assert len(candidates) == 1
    assert candidates[0].media_type == MediaType.VINYL
    assert candidates[0].title == "Daft Punk - Discovery"
    assert candidates[0].external_id == "1234567"


@pytest.mark.asyncio
@respx.mock
async def test_discogs_no_match_returns_empty_list():
    respx.get(DISCOGS_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("discogs_barcode_no_match.json"))
    )

    candidates = await DiscogsProvider().lookup_by_barcode("000000000000")

    assert candidates == []
