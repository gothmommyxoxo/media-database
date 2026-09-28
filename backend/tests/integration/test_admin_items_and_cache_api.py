from datetime import datetime, timezone

from app.auth.security import hash_password
from app.models import BarcodeCache, ItemSource, MediaItem, MediaType, Role, User


def _create_user(db_session, username, password="a password", role=Role.MEMBER):
    user = User(username=username, display_name=username.title(), password_hash=hash_password(password), role=role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _login(client, username, password="a password"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _admin_headers(client, db_session, username="alice"):
    _create_user(db_session, username, role=Role.ADMIN)
    return _login(client, username)


def test_admin_can_edit_fields_the_member_form_does_not_expose(client, db_session):
    headers = _admin_headers(client, db_session)
    bob = _create_user(db_session, "bob")
    item = MediaItem(media_type=MediaType.DVD, title="Brazil", source=ItemSource.MANUAL, added_by=bob.id)
    db_session.add(item)
    db_session.commit()

    response = client.patch(
        f"/api/admin/items/{item.id}",
        json={"source": "SCANNED", "external_ids": {"tmdb": "68"}, "added_by": None},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "SCANNED"
    assert body["external_ids"] == {"tmdb": "68"}
    assert body["added_by"] is None


def test_member_cannot_use_admin_item_editor(client, db_session):
    bob = _create_user(db_session, "bob")
    headers = _login(client, "bob")
    item = MediaItem(media_type=MediaType.DVD, title="Brazil", source=ItemSource.MANUAL, added_by=bob.id)
    db_session.add(item)
    db_session.commit()

    response = client.patch(f"/api/admin/items/{item.id}", json={"title": "hijack"}, headers=headers)

    assert response.status_code == 403


def test_changing_media_type_revalidates_attributes_against_new_schema(client, db_session):
    headers = _admin_headers(client, db_session)
    item = MediaItem(
        media_type=MediaType.CD,
        title="Discovery",
        source=ItemSource.MANUAL,
        attributes={"artist": "Daft Punk", "release_year": 2001},
    )
    db_session.add(item)
    db_session.commit()

    # VINYL shares CD's MusicAttributes schema (6's rationale), so this should succeed cleanly.
    response = client.patch(
        f"/api/admin/items/{item.id}",
        json={"media_type": "VINYL"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["media_type"] == "VINYL"
    assert response.json()["attributes"] == {"artist": "Daft Punk", "release_year": 2001}


def test_changing_media_type_rejects_incompatible_attributes(client, db_session):
    headers = _admin_headers(client, db_session)
    item = MediaItem(
        media_type=MediaType.CD,
        title="Discovery",
        source=ItemSource.MANUAL,
        attributes={"release_year": "not a year"},
    )
    db_session.add(item)
    db_session.commit()

    response = client.patch(
        f"/api/admin/items/{item.id}",
        json={"media_type": "VINYL"},
        headers=headers,
    )

    assert response.status_code == 422


def test_admin_can_list_and_purge_barcode_cache(client, db_session):
    headers = _admin_headers(client, db_session)
    db_session.add(
        BarcodeCache(
            barcode="724384960650",
            candidates=[
                {
                    "source_provider": "musicbrainz",
                    "media_type": "CD",
                    "title": "Discovery",
                    "subtitle": None,
                    "external_id": "abc",
                    "external_url": None,
                    "cover_image_url": None,
                    "raw_attributes": {},
                }
            ],
            last_refreshed_at=datetime.now(timezone.utc),
            refresh_count=1,
        )
    )
    db_session.commit()

    listed = client.get("/api/admin/barcode-cache", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    fetched = client.get("/api/admin/barcode-cache/724384960650", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["candidates"][0]["title"] == "Discovery"

    deleted = client.delete("/api/admin/barcode-cache/724384960650", headers=headers)
    assert deleted.status_code == 204

    missing = client.get("/api/admin/barcode-cache/724384960650", headers=headers)
    assert missing.status_code == 404


def test_purging_barcode_cache_does_not_touch_media_items(client, db_session):
    headers = _admin_headers(client, db_session)
    item = MediaItem(
        media_type=MediaType.CD, title="Discovery", barcode="724384960650", source=ItemSource.SCANNED
    )
    db_session.add(item)
    db_session.add(
        BarcodeCache(
            barcode="724384960650",
            candidates=[],
            last_refreshed_at=datetime.now(timezone.utc),
            refresh_count=1,
        )
    )
    db_session.commit()
    item_id = item.id

    client.delete("/api/admin/barcode-cache/724384960650", headers=headers)

    assert db_session.query(MediaItem).filter(MediaItem.id == item_id).first() is not None


def test_member_cannot_access_barcode_cache_admin_endpoints(client, db_session):
    _create_user(db_session, "bob")
    headers = _login(client, "bob")

    assert client.get("/api/admin/barcode-cache", headers=headers).status_code == 403
    assert client.get("/api/admin/barcode-cache/000", headers=headers).status_code == 403
    assert client.delete("/api/admin/barcode-cache/000", headers=headers).status_code == 403
