from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Mateo ConsultOps Themes"
    app_env: str = "development"
    secret_key: str = "change-me"
    database_url: str = "sqlite:///./app.db"
    base_url: str = "http://localhost:8000"
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from_email: str = "no-reply@mateoconsultops.local"
    download_link_ttl_seconds: int = 7200
    download_link_max_downloads: int = 5
    consultops_contacts_api_url: str = "https://consultops.mateoconsultinginc.com/api/integrations/contacts"
    consultops_base_url: str = ""
    integration_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
