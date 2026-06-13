from pathlib import Path
from pydantic_settings import BaseSettings


PROJECT_ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    APP_NAME: str = "Speech Intelligence Platform"

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "speech_db"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432

    UPLOAD_DIR: str = "uploads"
    OUTPUT_DIR: str = "outputs"
    TEMP_DIR: str = "temp"
    WHISPER_MODEL: str = "base.en"
    MFA_EXECUTABLE: str = "mfa"
    
    # 1. Explicitly register the Gemini Key field as optional
    # This prevents the 'extra_forbidden' validation crash on container start
    GEMINI_API_KEY: str = ""

    # 2. Pydantic V2 settings configuration format
    # Using 'ignore' for extra variables ensures that if your team adds other environment 
    # variables down the road, the container won't crash on startup.
    model_config = {
        "env_file": ".env",
        "extra": "ignore",
        "case_sensitive": False
    }


settings = Settings()


def project_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate