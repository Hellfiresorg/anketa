from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://voice_survey:password@localhost:5432/voice_survey"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Groq
    GROQ_API_KEY: str = ""

    # Audio storage
    AUDIO_ROOT: str = "/var/voice-survey/audio"
    MAX_AUDIO_SIZE_MB: int = 25
    MAX_AUDIO_DURATION_SEC: int = 300
    DISK_SPACE_MIN_BYTES: int = 1_073_741_824  # 1 GB

    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"

    # Sentry (optional)
    SENTRY_DSN: str = ""

    # App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # CORS origins (comma-separated)
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def max_audio_size_bytes(self) -> int:
        return self.MAX_AUDIO_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
