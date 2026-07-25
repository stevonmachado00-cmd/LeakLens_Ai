from typing import Any, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Compute a canonical absolute path for the SQLite database located under backend/leaklens.db
# This ensures all services use the same file regardless of process working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # backend/ (two levels up: core -> app -> backend)
CANONICAL_DB_PATH = (PROJECT_ROOT / "leaklens.db").resolve()

class Settings(BaseSettings):
    PROJECT_NAME: str = "LeakLens AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # Security
    SECRET_KEY: str = "secret-key-for-development-only"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    # Default to an absolute, canonical SQLite file under the backend directory
    DATABASE_URL: str = f"sqlite:///{CANONICAL_DB_PATH.as_posix()}"
    
    # Uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    SUPPORTED_STATEMENT_EXTENSIONS: List[str] = [".csv"]
    
    # AI
    CHROMA_PATH: str = "./chroma_db"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

    def model_post_init(self, __context: Any) -> None:
        """Reject known insecure secrets when explicitly running in production."""
        if self.ENVIRONMENT.lower() == "production":
            insecure_secrets = {
                "secret-key-for-development-only",
                "your_secret_key_here",
                "dev_secret_key",
            }
            if self.SECRET_KEY in insecure_secrets or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY must be a unique value of at least 32 characters in production"
                )

settings = Settings()
