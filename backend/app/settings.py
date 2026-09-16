from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # Relative to the working directory, which is backend/ when the seed command runs.
    database_url: str = "sqlite:///./customer_pulse.db"
