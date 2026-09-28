from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    jwt_secret: str = "dev-secret-change-me"
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


settings = Settings()
