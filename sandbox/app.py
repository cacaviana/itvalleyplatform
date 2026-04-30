"""
Sandbox local pra testar itvalleyplatform na mão (curl).

  cd sandbox
  set -a; . ./.env; set +a
  ../.venv/bin/uvicorn app:app --reload --port 8765

Login fake (gera JWT com tenant_id e claims):
  curl -X POST localhost:8765/login \\
    -H 'Content-Type: application/json' \\
    -d '{"sub":"user-1","email":"u@a.com","tenant_id":"clinica-abc",
         "products":["genesis"],"permissions":{"genesis":["leads"]}}'

Rota protegida:
  curl localhost:8765/leads -H "Authorization: Bearer $TOKEN"
"""
from fastapi import Depends, FastAPI, Response
from itvalleysecurity.core import issue_pair
from pydantic import BaseModel

from itvalleyplatform import TenantContext, require_permission, require_tenant

app = FastAPI(title="itvalleyplatform sandbox")


class LoginBody(BaseModel):
    sub: str
    email: str | None = None
    tenant_id: str | None = None
    is_master: bool = False
    products: list[str] = []
    permissions: dict[str, list[str]] = {}


@app.post("/login")
def login(body: LoginBody, response: Response):
    extra: dict = {
        "tenant_id": body.tenant_id,
        "products": body.products,
        "permissions": body.permissions,
    }
    if body.is_master:
        extra["is_master"] = True
    return issue_pair(sub=body.sub, email=body.email, **extra)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/me")
def me(tenant: TenantContext = Depends(require_tenant)):
    return {
        "tenant_id": tenant.id,
        "user_id": tenant.user_id,
        "is_master": tenant.is_master,
        "products": tenant.products,
        "current_product": tenant.current_product,
    }


@app.get("/leads")
def list_leads(tenant: TenantContext = Depends(require_permission("leads"))):
    # No mundo real, a query SQL filtra sozinha via RLS+SESSION_CONTEXT.
    # Aqui só ecoamos o tenant pra provar isolamento.
    return {"tenant_id": tenant.id, "leads": [f"{tenant.id}-lead-1"]}
