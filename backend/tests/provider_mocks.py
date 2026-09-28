"""Shared respx setup for tests that exercise resolve_barcode end-to-end. Mocks every registered
provider (app.barcode.resolution's GENERAL_BARCODE_PROVIDERS/DIRECT_BARCODE_PROVIDERS/
TITLE_SEARCH_PROVIDERS_BY_GROUP) to return "no match" by default; individual tests override
specific routes afterward via `respx.get(...)`/`respx.post(...)` for their scenario.
"""

import json
from pathlib import Path

import httpx
import respx

from app.barcode.providers.anilist import ANILIST_URL
from app.barcode.providers.comicvine import COMICVINE_URL
from app.barcode.providers.discogs import DISCOGS_URL
from app.barcode.providers.google_books import GOOGLE_BOOKS_URL
from app.barcode.providers.igdb import IGDB_GAMES_URL, TWITCH_OAUTH_URL
from app.barcode.providers.jikan import JIKAN_URL
from app.barcode.providers.musicbrainz import MUSICBRAINZ_URL
from app.barcode.providers.omdb import OMDB_URL
from app.barcode.providers.rawg import RAWG_URL
from app.barcode.providers.scandex import SCANDEX_URL
from app.barcode.providers.tmdb import TMDB_SEARCH_URL
from app.barcode.providers.upc_general import UPCITEMDB_URL

FIXTURES = Path(__file__).parent / "fixtures" / "providers"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def mock_all_providers_empty() -> None:
    respx.get(UPCITEMDB_URL).mock(return_value=httpx.Response(200, json=load_fixture("upcitemdb_lookup_no_match.json")))
    respx.get(MUSICBRAINZ_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("musicbrainz_barcode_no_match.json"))
    )
    respx.get(GOOGLE_BOOKS_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("google_books_isbn_no_match.json"))
    )
    respx.get(DISCOGS_URL).mock(return_value=httpx.Response(200, json=load_fixture("discogs_barcode_no_match.json")))
    respx.get(SCANDEX_URL).mock(return_value=httpx.Response(200, json=load_fixture("scandex_barcode_no_match.json")))

    respx.get(TMDB_SEARCH_URL).mock(return_value=httpx.Response(200, json=load_fixture("tmdb_title_no_match.json")))
    respx.get(OMDB_URL).mock(return_value=httpx.Response(200, json=load_fixture("omdb_title_no_match.json")))
    respx.get(COMICVINE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("comicvine_title_no_match.json"))
    )
    respx.get(RAWG_URL).mock(return_value=httpx.Response(200, json=load_fixture("rawg_title_no_match.json")))
    respx.post(TWITCH_OAUTH_URL).mock(return_value=httpx.Response(200, json=load_fixture("igdb_oauth_token.json")))
    respx.post(IGDB_GAMES_URL).mock(return_value=httpx.Response(200, json=load_fixture("igdb_title_no_match.json")))
    respx.post(ANILIST_URL).mock(return_value=httpx.Response(200, json=load_fixture("anilist_title_no_match.json")))
    respx.get(JIKAN_URL).mock(return_value=httpx.Response(200, json=load_fixture("jikan_title_no_match.json")))
