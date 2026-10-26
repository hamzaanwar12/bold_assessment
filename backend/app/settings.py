from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Two connection URLs, deliberately.

    RLS does not apply to a table's owner, so the API must never use the owner
    connection -- the policy would exist and protect nothing. See docs/adr/0002.
    """

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    database_url_owner: str
    database_url_app: str
    test_database_url_owner: str = ""
    test_database_url_app: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
