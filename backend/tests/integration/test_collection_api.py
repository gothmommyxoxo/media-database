from app.auth.security import hash_password
from app.models import User


def _create_user_and_login(client, db_session, username="alice"):
    user = User(username=username, display_name=username.title(), password_hash=hash_password("a password"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    login = client.post("/api/auth/login", json={"username": username, "password": "a password"})
    token = login.json()["access_token"]
    return user, {"Authorization": f"Bearer {token}"}


def test_create_and_get_item(client, db_session):
    _, headers = _create_user_and_login(client, db_session)

    create = client.post(
        "/api/items",
        json={
            "media_type": "CD",
            "title": "Discovery",
            "barcode": "724384960650",
            "attributes": {"artist": "Daft Punk", "release_year": 2001},
        },
        headers=headers,
    )
    assert create.status_code == 201
    item = create.json()
    assert item["source"] == "MANUAL"
    assert item["attributes"]["artist"] == "Daft Punk"

    fetched = client.get(f"/api/items/{item['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Discovery"


def test_create_item_rejects_invalid_attributes_for_media_type(client, db_session):
    _, headers = _create_user_and_login(client, db_session)

    response = client.post(
        "/api/items",
        json={"media_type": "CD", "title": "Bad", "attributes": {"release_year": "not a year"}},
        headers=headers,
    )
    assert response.status_code == 422


def test_list_items_filters_by_media_type_and_search(client, db_session):
    _, headers = _create_user_and_login(client, db_session)
    client.post("/api/items", json={"media_type": "CD", "title": "Discovery"}, headers=headers)
    client.post("/api/items", json={"media_type": "VINYL", "title": "Random Access Memories"}, headers=headers)
    client.post("/api/items", json={"media_type": "MANGA", "title": "Berserk Volume 1"}, headers=headers)

    only_music = client.get("/api/items", params={"media_type": ["CD", "VINYL"]}, headers=headers)
    assert only_music.status_code == 200
    titles = {i["title"] for i in only_music.json()["items"]}
    assert titles == {"Discovery", "Random Access Memories"}

    search = client.get("/api/items", params={"search": "berserk"}, headers=headers)
    assert [i["title"] for i in search.json()["items"]] == ["Berserk Volume 1"]


def test_any_member_can_edit_or_delete_any_item(client, db_session):
    alice, alice_headers = _create_user_and_login(client, db_session, "alice")
    create = client.post("/api/items", json={"media_type": "DVD", "title": "Brazil"}, headers=alice_headers)
    item_id = create.json()["id"]

    bob, bob_headers = _create_user_and_login(client, db_session, "bob")
    edit = client.patch(f"/api/items/{item_id}", json={"notes": "Criterion edition"}, headers=bob_headers)
    assert edit.status_code == 200
    assert edit.json()["notes"] == "Criterion edition"

    delete = client.delete(f"/api/items/{item_id}", headers=bob_headers)
    assert delete.status_code == 204
    assert client.get(f"/api/items/{item_id}", headers=bob_headers).status_code == 404


def test_items_endpoints_require_auth(client, db_session):
    assert client.get("/api/items").status_code == 401
    assert client.post("/api/items", json={"media_type": "CD", "title": "x"}).status_code == 401
