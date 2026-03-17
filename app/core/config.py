from pathlib import Path
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings
from functools import lru_cache

# .env en la carpeta backend (junto a app/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    # Sin fallback a SQLite: solo BD del .env (Azure SQL o DATABASE_URL explícita).
    DATABASE_URL: str = ""
    # Azure SQL: si están definidas, se construye DATABASE_URL para mssql+pyodbc
    AZURE_SQL_SERVER: str | None = None  # ej: tu-servidor.database.windows.net
    AZURE_SQL_DATABASE: str | None = None  # ej: PortalSeguimientos
    AZURE_SQL_USER: str | None = None
    AZURE_SQL_PASSWORD: str | None = None
    AZURE_SQL_DRIVER: str = "ODBC Driver 17 for SQL Server"  # o "ODBC Driver 18 for SQL Server"
    SECRET_KEY: str = "change-me-in-production-minimum-32-characters"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    FRONTEND_URL: str = "http://localhost:5173"

    class Config:
        env_file = str(_ENV_FILE) if _ENV_FILE.exists() else ".env"
        case_sensitive = True

    def get_database_url(self) -> str:
        """Solo la BD del .env: Azure SQL (AZURE_SQL_*) o DATABASE_URL. Sin fallback a SQLite."""
        if all([self.AZURE_SQL_SERVER, self.AZURE_SQL_DATABASE, self.AZURE_SQL_USER, self.AZURE_SQL_PASSWORD]):
            user = quote_plus(self.AZURE_SQL_USER)
            password = quote_plus(self.AZURE_SQL_PASSWORD)
            driver = quote_plus(self.AZURE_SQL_DRIVER)
            return (
                f"mssql+pyodbc://{user}:{password}@{self.AZURE_SQL_SERVER}:1433/{self.AZURE_SQL_DATABASE}"
                f"?driver={driver}&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30"
            )
        if self.DATABASE_URL and not self.DATABASE_URL.strip().startswith("sqlite"):
            return self.DATABASE_URL.strip()
        raise ValueError(
            "Configura AZURE_SQL_SERVER, AZURE_SQL_DATABASE, AZURE_SQL_USER y AZURE_SQL_PASSWORD en .env, "
            "o DATABASE_URL con una URL de base de datos (no SQLite)."
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
