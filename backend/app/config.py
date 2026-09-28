from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-secret-change-me"
MIN_PRODUCTION_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # "production" turns the dev conveniences below into hard requirements (Section 11.2:
    # DATABASE_URL and JWT_SECRET have no defaults in a real deployment).
    environment: Literal["development", "production"] = "development"

    database_url: str = "sqlite:///./dev.db"
    jwt_secret: str = DEV_JWT_SECRET
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    cache_ttl_days: int = 30
    provider_timeout_ms: int = 4000

    google_books_api_key: str = ""
    tmdb_api_key: str = ""
    omdb_api_key: str = ""
    igdb_client_id: str = ""
    igdb_client_secret: str = ""
    rawg_api_key: str = ""
    discogs_token: str = ""
    comicvine_api_key: str = ""
    scandex_api_key: str = ""
    pricecharting_api_key: str = ""
    upcitemdb_mode: str = "trial"
    barcodespider_api_key: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def _require_real_secrets_in_production(self) -> "Settings":
        if not self.is_production:
            return self
        problems = []
        if self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < MIN_PRODUCTION_JWT_SECRET_LENGTH:
            problems.append(
                f"JWT_SECRET must be set to a random value of at least {MIN_PRODUCTION_JWT_SECRET_LENGTH} "
                "characters (e.g. `openssl rand -hex 32`)"
            )
        if self.database_url.startswith("sqlite"):
            problems.append("DATABASE_URL must point at MySQL, not SQLite")
        if problems:
            raise ValueError("invalid production configuration: " + "; ".join(problems))
        return self


settings = Settings()
