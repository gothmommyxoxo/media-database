from app.auth.security import hash_password
from app.models import ItemSource, MediaItem, MediaType, Role, User


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


def test_admin_can_list_users(client, db_session):
    headers = _admin_headers(client, db_session)
    _create_user(db_session, "bob")

    response = client.get("/api/admin/users", headers=headers)

    assert response.status_code == 200
    usernames = {u["username"] for u in response.json()}
    assert usernames == {"alice", "bob"}


def test_member_cannot_list_users(client, db_session):
    _create_user(db_session, "bob", role=Role.MEMBER)
    headers = _login(client, "bob")

    response = client.get("/api/admin/users", headers=headers)

    assert response.status_code == 403


def test_admin_can_create_user_with_role(client, db_session):
    headers = _admin_headers(client, db_session)

    response = client.post(
        "/api/admin/users",
        json={"username": "carol", "display_name": "Carol", "password": "a password", "role": "ADMIN"},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "carol"
    assert body["role"] == "ADMIN"


def test_create_user_duplicate_username_returns_409(client, db_session):
    headers = _admin_headers(client, db_session)

    response = client.post(
        "/api/admin/users",
        json={"username": "alice", "display_name": "Someone Else", "password": "x", "role": "MEMBER"},
        headers=headers,
    )

    assert response.status_code == 409


def test_admin_can_edit_and_promote_a_user(client, db_session):
    headers = _admin_headers(client, db_session)
    bob = _create_user(db_session, "bob", role=Role.MEMBER)

    response = client.patch(
        f"/api/admin/users/{bob.id}",
        json={"display_name": "Bobby", "role": "ADMIN"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "Bobby"
    assert body["role"] == "ADMIN"


def test_admin_can_reset_a_users_password(client, db_session):
    headers = _admin_headers(client, db_session)
    bob = _create_user(db_session, "bob", password="old password")

    reset = client.post(
        f"/api/admin/users/{bob.id}/reset-password",
        json={"new_password": "new password"},
        headers=headers,
    )
    assert reset.status_code == 204

    old_login = client.post("/api/auth/login", json={"username": "bob", "password": "old password"})
    assert old_login.status_code == 401

    new_login = client.post("/api/auth/login", json={"username": "bob", "password": "new password"})
    assert new_login.status_code == 200


def test_deleting_a_user_nulls_added_by_on_their_items_instead_of_deleting_them(client, db_session):
    headers = _admin_headers(client, db_session)
    bob = _create_user(db_session, "bob")
    item = MediaItem(media_type=MediaType.DVD, title="Brazil", source=ItemSource.MANUAL, added_by=bob.id)
    db_session.add(item)
    db_session.commit()
    item_id = item.id

    response = client.delete(f"/api/admin/users/{bob.id}", headers=headers)

    assert response.status_code == 204
    assert db_session.query(User).filter(User.id == bob.id).first() is None
    surviving_item = db_session.query(MediaItem).filter(MediaItem.id == item_id).first()
    assert surviving_item is not None
    assert surviving_item.added_by is None


def test_cannot_delete_the_only_remaining_admin(client, db_session):
    admin = _create_user(db_session, "alice", role=Role.ADMIN)
    headers = _login(client, "alice")

    response = client.delete(f"/api/admin/users/{admin.id}", headers=headers)

    assert response.status_code == 409
    assert db_session.query(User).filter(User.id == admin.id).first() is not None


def test_cannot_demote_the_only_remaining_admin(client, db_session):
    admin = _create_user(db_session, "alice", role=Role.ADMIN)
    headers = _login(client, "alice")

    response = client.patch(f"/api/admin/users/{admin.id}", json={"role": "MEMBER"}, headers=headers)

    assert response.status_code == 409
    db_session.refresh(admin)
    assert admin.role == Role.ADMIN


def test_demoting_one_of_two_admins_is_allowed(client, db_session):
    headers = _admin_headers(client, db_session, "alice")
    bob = _create_user(db_session, "bob", role=Role.ADMIN)

    response = client.patch(f"/api/admin/users/{bob.id}", json={"role": "MEMBER"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["role"] == "MEMBER"
