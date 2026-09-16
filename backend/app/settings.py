from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # Relative to the working directory, which is backend/ when the seed command runs.
    database_url: str = "sqlite:///./customer_pulse.db"
    # Browser origins allowed to call the API, comma-separated. A browser rule only,
    # not authentication.
    cors_origins: str = "http://localhost:3000"
    # No default key. The Gemini provider refuses to start without one.
    gemini_api_key: SecretStr | None = None
    # The only place a model id is named.
    gemini_model: str = "gemini-3.8-flash"

    def cors_origin_list(self) -> list[str]:
        origins = (origin.strip() for origin in self.cors_origins.split(","))
        return [origin for origin in origins if origin]
