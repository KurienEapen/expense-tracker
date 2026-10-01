from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "AdultMoney"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/expense_tracker.db"
    SQLITE_WAL_MODE: bool = True
    
    # Security: Ingest replay protection tolerance in seconds (5 minutes)
    TIMESTAMP_SKEW_TOLERANCE_SECONDS: int = 300
    
    # Master server secret or default device secret for initial bootstrap
    BOOTSTRAP_DEVICE_ID: str = "pixel-companion-01"
    BOOTSTRAP_DEVICE_SECRET: str = "dev_secret_change_in_production_32bytes"
    
    # Telegram Alerting (configured in Phase 5)
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # Google Places API Key (Optional for high-accuracy commercial venue lookup)
    GOOGLE_PLACES_API_KEY: Optional[str] = None

settings = Settings()
