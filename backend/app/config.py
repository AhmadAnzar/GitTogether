from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GitTogether API"
    database_url: str = "postgresql+psycopg://gittogether:gittogether@localhost:5432/gittogether"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
