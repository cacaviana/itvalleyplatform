import os
from dataclasses import dataclass

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True), override=False)


@dataclass(frozen=True)
class Settings:
    PLATFORM_SQL_CONNECTION: str = os.getenv("PLATFORM_SQL_CONNECTION", "")
    PLATFORM_TENANT_HEADER: str = os.getenv("PLATFORM_TENANT_HEADER", "X-Tenant-Id")
    PLATFORM_PRODUCT_SLUG: str = os.getenv("PLATFORM_PRODUCT_SLUG", "")
    PLATFORM_LOG_LEVEL: str = os.getenv("PLATFORM_LOG_LEVEL", "WARNING")


SETTINGS = Settings()
