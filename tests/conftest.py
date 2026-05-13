import os

# JWT_SECRET_KEY tem que ser >=32 chars, senão itvalleysecurity explode no import.
os.environ.setdefault(
    "JWT_SECRET_KEY", "test_secret_key_with_more_than_32_chars_xyzxyz"
)
os.environ.setdefault("JWT_ISSUER", "ITValley")
os.environ.setdefault("EV_TOKEN_SOURCE", "bearer")
os.environ.setdefault("EV_SUB_POLICY", "any")
os.environ.setdefault("PLATFORM_PRODUCT_SLUG", "genesis")
# PLATFORM_SQL_CONNECTION fica vazio: middleware vai logar warning e seguir.

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from itvalleysecurity.core import issue_pair

from petraplatform import (
    TenantContext,
    require_permission,
    require_tenant,
)


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()

    @app.get("/me")
    def me(tenant: TenantContext = Depends(require_tenant)):
        return {
            "tenant_id": tenant.id,
            "user_id": tenant.user_id,
            "is_master": tenant.is_master,
            "products": tenant.products,
        }

    @app.get("/leads")
    def list_leads(
        tenant: TenantContext = Depends(require_permission("leads")),
    ):
        return {"tenant_id": tenant.id, "leads": ["a", "b"]}

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def make_token(
    *,
    sub: str = "user-001",
    email: str = "user@example.com",
    tenant_id: str | None = "clinica-abc",
    is_master: bool = False,
    products: list[str] | None = None,
    permissions: dict[str, list[str]] | None = None,
) -> str:
    extra: dict = {}
    if tenant_id is not None:
        extra["tenant_id"] = tenant_id
    if is_master:
        extra["is_master"] = True
    if products is not None:
        extra["products"] = products
    if permissions is not None:
        extra["permissions"] = permissions
    pair = issue_pair(sub=sub, email=email, **extra)
    return pair["access_token"]


@pytest.fixture
def make_token_fn():
    return make_token
