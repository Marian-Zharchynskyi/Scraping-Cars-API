from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class AppSettings(BaseSettings):
    DB_CONNECTION_STRING: str = Field(alias="DB_CONNECTION_STRING", min_length=1)

    model_config = SettingsConfigDict(env_file=".env")


settings = AppSettings.model_validate({})
