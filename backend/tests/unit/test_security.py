from datetime import timedelta

import pytest

from app.auth.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_does_not_store_plaintext():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_access_token_round_trips_subject():
    token = create_access_token(subject="42", expires_delta=timedelta(minutes=15))
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["type"] == "access"


def test_expired_token_fails_to_decode():
    token = create_access_token(subject="42", expires_delta=timedelta(minutes=-1))
    with pytest.raises(Exception):
        decode_token(token)
