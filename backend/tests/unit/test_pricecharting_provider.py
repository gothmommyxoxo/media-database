import json
from pathlib import Path

import httpx
import pytest
import respx

from app.barcode.providers.pricecharting import PRICECHARTING_URL, PriceChartingProvider
from app.models.enums import MediaType

FIXTURES = Path(__file__).parent.parent / "fixtures" / "providers"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.asyncio
@respx.mock
async def test_pricecharting_single_match():
    respx.get(PRICECHARTING_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("pricecharting_barcode_single_match.json"))
    )

    candidates = await PriceChartingProvider().lookup_by_barcode("045496594454")

    assert len(candidates) == 1
    assert candidates[0].media_type == MediaType.VIDEO_GAME
    assert candidates[0].title == "Super Mario Odyssey"
    assert candidates[0].subtitle == "Nintendo Switch"


@pytest.mark.asyncio
@respx.mock
async def test_pricecharting_no_match_returns_empty_list():
    respx.get(PRICECHARTING_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("pricecharting_barcode_no_match.json"))
    )

    candidates = await PriceChartingProvider().lookup_by_barcode("000000000000")

    assert candidates == []
