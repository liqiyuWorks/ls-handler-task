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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 7 * 24 * 60  # 7 天，到期需重新登录

    @property
    def MONGO_URL(self) -> str:
        encoded_password = quote_plus(self.MONGO_PASSWORD)
        return f"mongodb://{self.MONGO_USER}:{encoded_password}@{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_DB}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Gemini 图片生成配置 (基于 api.apiyi.com)
    GEMINI_API_KEY: str = "sk-YJwZH23oS4ouiRiD905bE5DaC7084cC080E936884aBfB358"
    GEMINI_API_URL: str = "https://api.apiyi.com/v1beta/models/gemini-3-pro-image-preview:generateContent"
    GEMINI_TIMEOUT: int = 120
    # 用于从 models_price_map 查询价格的模型名，需与表内 model 字段一致
    GEMINI_IMAGE_MODEL: str = "gemini-3-pro-image-preview"

    # 以下为兜底：当 models_price_map 无对应记录时使用
    GEMINI_PRICING: dict = {"1K": 0.05, "2K": 0.05, "4K": 0.05}
    USD_TO_CNY: float = 7.2

    # VEO 视频生成配置 (api.apiyi.com)，与图片生成共用 GEMINI_API_KEY
    VEO_API_KEY: str = ""  # 可选，未配置时使用 GEMINI_API_KEY
    VEO_BASE_URL: str = "https://api.apiyi.com"
    VEO_MODEL_TEXT: str = "veo-3.1"
    VEO_MODEL_IMAGE: str = "veo-3.1-landscape-fl"
    VEO_TIMEOUT: int = 120

    # 视频/静态资源对外访问根 URL，用于返回可预览的完整视频链接
    # 本地测试: http://localhost:8000 ；Docker 部署: http://api.lsopc.cn
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # 互亿无线 短信验证码（ihuyi）
    IHUYI_ACCOUNT: str = "C47365157"
    IHUYI_PASSWORD: str = "8dca2f2b194ff1e99af892c85ea34e0f"
    IHUYI_SMS_HOST: str = "api.ihuyi.com"
    IHUYI_SMS_URI: str = "/sms/Submit.json"
    # 验证码有效期（秒）
    SMS_CODE_EXPIRE_SECONDS: int = 300


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
