"""
Centralized application configuration for DevTrack.
"""

from __future__ import annotations

from functools import lru_cache
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Typed view over environment variables used by the application."""

    def __init__(self) -> None:
        self.app_name = "DevTrack API"
        self.app_version = "1.1.0"
        self.github_token = self._get_required("GITHUB_TOKEN")
        self.github_username = self._get_required("GITHUB_USERNAME")
        self.anthropic_api_key = self._get_required("ANTHROPIC_API_KEY")
        self.database_url = self._get_required("DATABASE_URL")
        self.devtrack_api_key = os.getenv("DEVTRACK_API_KEY")

    @staticmethod
    def _get_required(name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise ValueError(
                f"{name} environment variable is required. "
                "Update your environment or .env file before starting the app."
            )
        return value

    @property
    def api_key_auth_enabled(self) -> bool:
        return bool(self.devtrack_api_key)


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance for app code and dependencies."""
    return Settings()
