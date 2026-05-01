from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "sqlite:///data/p2p.db"
    log_level: str = "INFO"
    tracker_interval_seconds: int = 60
    deep_snapshot_interval_seconds: int = 900


settings = Settings()
