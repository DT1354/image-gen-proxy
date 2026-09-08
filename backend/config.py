import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


class Settings:
    # APIMart配置
    APIMART_API_KEY: str = os.environ.get("APIMART_API_KEY", "")
    APIMART_API_BASE: str = "https://api.apimart.ai"

    # 管理员密钥
    ADMIN_KEY: str = os.environ.get("ADMIN_KEY", "")

    # 服务配置
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", "8000"))

    # 图片配置
    IMAGE_DIR: Path = Path(os.environ.get("IMAGE_DIR", "/var/www/image-gen-proxy/images"))
    IMAGE_RETENTION_HOURS: int = int(os.environ.get("IMAGE_RETENTION_HOURS", "24"))

    # 用户限额
    DAILY_LIMIT: int = int(os.environ.get("DAILY_LIMIT", "10"))

    # CORS
    CORS_ORIGINS: list = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")


settings = Settings()
