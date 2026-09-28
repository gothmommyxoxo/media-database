from app.auth.security import hash_password
from app.models import User


def _create_user(db_session, username="alice", password="correct horse battery staple"):
    user = User(username=username, display_name=username.title(), password_hash=hash_password(password))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_login_with_valid_credentials_returns_token_pair(client, db_session):
    _create_user(db_session, "alice", "correct horse battery staple")

    response = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "correct horse battery staple"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert response.cookies.get("refresh_token") is not None


def test_login_with_wrong_password_returns_generic_401(client, db_session):
    _create_user(db_session, "alice", "correct horse battery staple")

    response = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})

    assert response.status_code == 401
    assert "invalid username or password" in response.json()["detail"].lower()


def test_login_with_unknown_username_returns_same_generic_401(client, db_session):
    response = client.post("/api/auth/login", json={"username": "ghost", "password": "whatever"})

    assert response.status_code == 401
    assert "invalid username or password" in response.json()["detail"].lower()


def test_refresh_issues_new_access_token(client, db_session):
    _create_user(db_session, "alice", "correct horse battery staple")
    login = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "correct horse battery staple"},
    )
    old_access_token = login.json()["access_token"]

    response = client.post("/api/auth/refresh")

    assert response.status_code == 200
    assert response.json()["access_token"] != old_access_token


def test_logout_revokes_refresh_token(client, db_session):
    _create_user(db_session, "alice", "correct horse battery staple")
    client.post("/api/auth/login", json={"username": "alice", "password": "correct horse battery staple"})

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 204

    refresh_after_logout = client.post("/api/auth/refresh")
    assert refresh_after_logout.status_code == 401


def test_me_returns_current_user_profile_including_role(client, db_session):
    _create_user(db_session, "alice", "correct horse battery staple")
    login = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "correct horse battery staple"},
    )
    access_token = login.json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "alice"
    assert body["role"] == "MEMBER"


def test_me_without_auth_is_rejected(client, db_session):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
