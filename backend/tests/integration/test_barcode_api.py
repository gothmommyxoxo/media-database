import httpx
import respx

from app.auth.security import hash_password
from app.barcode.providers.musicbrainz import MUSICBRAINZ_URL
from app.models import User
from tests.provider_mocks import load_fixture, mock_all_providers_empty


def _create_user_and_login(client, db_session, username="alice"):
    user = User(username=username, display_name=username.title(), password_hash=hash_password("a password"))
    db_session.add(user)
    db_session.commit()
    login = client.post("/api/auth/login", json={"username": username, "password": "a password"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _mock_providers_for_cd_match():
    mock_all_providers_empty()
    respx.get(MUSICBRAINZ_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("musicbrainz_barcode_single_match.json"))
    )


@respx.mock
def test_resolve_endpoint_requires_auth(client, db_session):
    _mock_providers_for_cd_match()
    response = client.get("/api/barcode/724384960650/resolve")
    assert response.status_code == 401


@respx.mock
def test_resolve_endpoint_returns_candidates(client, db_session):
    headers = _create_user_and_login(client, db_session)
    _mock_providers_for_cd_match()

    response = client.get("/api/barcode/724384960650/resolve", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["requires_manual_entry"] is False
    assert len(body["candidates"]) == 1
    assert body["candidates"][0]["media_type"] == "CD"


@respx.mock
def test_create_from_candidate_persists_scanned_item_with_external_id(client, db_session):
    headers = _create_user_and_login(client, db_session)
    _mock_providers_for_cd_match()

    resolved = client.get("/api/barcode/724384960650/resolve", headers=headers).json()
    candidate = resolved["candidates"][0]

    response = client.post(
        "/api/barcode/items",
        json={"candidate": candidate, "media_type": "CD", "barcode": "724384960650"},
        headers=headers,
    )

    assert response.status_code == 201
    item = response.json()
    assert item["source"] == "SCANNED"
    assert item["title"] == "Discovery"
    assert item["external_ids"] == {"musicbrainz": "09ffa920-becb-4e2f-b511-01aa50fb2cb3"}
    assert item["barcode"] == "724384960650"


@respx.mock
def test_second_scan_of_same_barcode_shows_already_owned(client, db_session):
    headers = _create_user_and_login(client, db_session)
    _mock_providers_for_cd_match()

    resolved = client.get("/api/barcode/724384960650/resolve", headers=headers).json()
    candidate = resolved["candidates"][0]
    client.post(
        "/api/barcode/items",
        json={"candidate": candidate, "media_type": "CD", "barcode": "724384960650"},
        headers=headers,
    )

    second_scan = client.get("/api/barcode/724384960650/resolve", headers=headers)

    assert len(second_scan.json()["owned_matches"]) == 1
