import pytest
from pydantic import ValidationError

from app.config import DEV_JWT_SECRET, Settings

MYSQL_URL = "mysql+pymysql://u:p@db:3306/media_database"
STRONG_SECRET = "a" * 64


def test_development_allows_dev_defaults():
    settings = Settings(_env_file=None, environment="development")
    assert settings.jwt_secret == DEV_JWT_SECRET
    assert not settings.is_production


def test_production_accepts_real_configuration():
    settings = Settings(_env_file=None, environment="production", jwt_secret=STRONG_SECRET, database_url=MYSQL_URL)
    assert settings.is_production


def test_production_rejects_dev_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(_env_file=None, environment="production", database_url=MYSQL_URL)


def test_production_rejects_short_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(_env_file=None, environment="production", jwt_secret="too-short", database_url=MYSQL_URL)


def test_production_rejects_sqlite():
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(_env_file=None, environment="production", jwt_secret=STRONG_SECRET)
