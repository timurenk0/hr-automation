from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or the root .env."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(min_length=1, repr=False)


# @lru_cache remembers a functions's return value so repeated calls with the same
# arguments can reuse it (basically as tanstack cache)
# since the function takes no arguments, it only need one cache entry. Btw each python process has its own cache. 
# environment changes won't be picked up until you restart the process or call get_settings.cache_clear()
# when cache fills up, it removes the entry that hasn't been used for the longest time. 
# the default capacity is 128 argument combinations

@lru_cache
def get_settings() -> Settings:
    """Load and validate settings once, when first requested."""
    return Settings()
