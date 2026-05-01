import os
from dataclasses import dataclass

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True), override=False)


@dataclass(frozen=True)
class Settings:
    # Banco do APP do dev (Genesis usa dblumina, etc) — onde aplica RLS via SESSION_CONTEXT.
    APP_SQL_CONNECTION: str = os.getenv("APP_SQL_CONNECTION", "")

    # Banco do schema platform.* (dbplatform). Usado pelo init-platform CLI e
    # por endpoints de admin/login. NÃO é tocado em request path no v0.1.0 —
    # tudo o que o middleware precisa vem do JWT.
    PLATFORM_SQL_CONNECTION: str = os.getenv("PLATFORM_SQL_CONNECTION", "")

    # Header opcional para master escolher tenant alvo
    PLATFORM_TENANT_HEADER: str = os.getenv("PLATFORM_TENANT_HEADER", "X-Tenant-Id")

    # Slug do produto onde checamos permissões (ex: "genesis", "petra")
    PLATFORM_PRODUCT_SLUG: str = os.getenv("PLATFORM_PRODUCT_SLUG", "")

    PLATFORM_LOG_LEVEL: str = os.getenv("PLATFORM_LOG_LEVEL", "WARNING")


SETTINGS = Settings()
