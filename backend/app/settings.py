from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # Relative to the working directory, which is backend/ when the seed command runs.
    database_url: str = "sqlite:///./customer_pulse.db"
    # Browser origins allowed to call the API, comma-separated. A browser rule only,
    # not authentication.
    cors_origins: str = "http://localhost:3000"

    def cors_origin_list(self) -> list[str]:
        origins = (origin.strip() for origin in self.cors_origins.split(","))
        return [origin for origin in origins if origin]
