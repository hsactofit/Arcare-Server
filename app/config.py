from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "Arcar Wellness Backend"
    API_PREFIX: str = "/api"
    DATABASE_URL: str = "postgresql://postgres:postgres_password_123@localhost:5433/my_database"

    # Security settings
    JWT_SECRET_KEY: str = "supersecretkeyforarcarwellnessaccess12345"
    JWT_REFRESH_SECRET_KEY: str = "supersecretrefreshkeyforarcarwellness67890"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    class Config:

        env_file = ".env"
        case_sensitive = True

settings = Settings()

from datetime import timezone, timedelta, datetime
IST = timezone(timedelta(hours=5, minutes=30))

def get_now_naive():
    return datetime.now(IST).replace(tzinfo=None)


