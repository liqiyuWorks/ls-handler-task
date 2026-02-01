# -*- coding: utf-8 -*-
"""应用配置"""

from urllib.parse import quote_plus
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用设置"""

    APP_TITLE: str = "Dynamic XPath Parser API"
    APP_DESC: str = "API to extract data from dynamic webpages using XPath and Playwright."
    APP_VERSION: str = "1.0.0"

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Playwright
    PLAYWRIGHT_HEADLESS: bool = True
    NAVIGATE_TIMEOUT: int = 30000
    SELECTOR_TIMEOUT: int = 10000

    # MongoDB
    MONGO_HOST: str = "153.35.13.226"
    MONGO_PORT: int = 27017
    MONGO_DB: str = "lsopc"
    MONGO_USER: str = "lsopc"
    MONGO_PASSWORD: str = "Lsopc#0817"

    # JWT Security
    SECRET_KEY: str = "your-secret-key-keep-it-secret"  # 在生产环境应该从环境变量读取
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @property
    def MONGO_URL(self) -> str:
        encoded_password = quote_plus(self.MONGO_PASSWORD)
        return f"mongodb://{self.MONGO_USER}:{encoded_password}@{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_DB}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()

# Legacy aliases for compatibility if needed, but perfer settings.XXX
APP_TITLE = settings.APP_TITLE
APP_DESC = settings.APP_DESC
APP_VERSION = settings.APP_VERSION
HOST = settings.HOST
PORT = settings.PORT
PLAYWRIGHT_HEADLESS = settings.PLAYWRIGHT_HEADLESS
NAVIGATE_TIMEOUT = settings.NAVIGATE_TIMEOUT
SELECTOR_TIMEOUT = settings.SELECTOR_TIMEOUT
