"""
StyleHub - Application Configuration
Loads settings from .env. DATABASE_MODE toggles SQLite <-> MySQL
with a single environment variable - no code changes needed.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _get_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "StyleHub")
    DEBUG: bool = _get_bool("DEBUG", True)

    # Database mode switch
    DATABASE_MODE: str = os.getenv("DATABASE_MODE", "sqlite").strip().lower()

    # SQLite
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "stylehub.db")

    # MySQL
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: str = os.getenv("MYSQL_PORT", "3306")
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "stylehub_db")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "insecure-dev-key")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:8000")

    @property
    def DATABASE_URL(self) -> str:
        if self.DATABASE_MODE == "mysql":
            return (
                f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
                f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            )
        # default: sqlite - zero setup required
        db_path = (BASE_DIR / self.SQLITE_DB_PATH).as_posix()
        return f"sqlite:///{db_path}"


settings = Settings()
