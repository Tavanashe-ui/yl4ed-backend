# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "YL4ED Membership System"
    API_V1_STR: str = "/api/v1"
    
    # Database Settings
    POSTGRES_SERVER: str
    POSTGRES_PORT: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"

settings = Settings() 