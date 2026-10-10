from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GitTogether API"
    database_url: str = "postgresql+psycopg://gittogether:gittogether@localhost:5432/gittogether"

    # Signs login tokens. Must be overridden (env JWT_SECRET) anywhere but local development:
    # Docker Compose reads it from .env, Kubernetes from a Secret.
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60 * 24
    # Send the session cookie only over HTTPS. Off locally (plain http://localhost).
    cookie_secure: bool = False

    max_resume_bytes: int = 5 * 1024 * 1024

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
