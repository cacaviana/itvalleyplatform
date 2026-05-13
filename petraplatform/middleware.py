import logging
from typing import Any, Callable

from fastapi import Depends, Request

from .auth import decode_jwt
from .config import SETTINGS
from .db import set_session_context
from .exceptions import TenantNotFound
from .tenant_context import TenantContext

_logger = logging.getLogger("petraplatform.middleware")
_warned_no_product = False


def _warn_if_no_product_slug() -> None:
    """
    Aviso 1x no startup: se PLATFORM_PRODUCT_SLUG está vazio, qualquer
    require_permission(...) vira 403. Fail-closed é seguro, mas é fácil de errar.
    """
    global _warned_no_product
    if _warned_no_product:
        return
    if not SETTINGS.PLATFORM_PRODUCT_SLUG:
        _logger.warning(
            "PLATFORM_PRODUCT_SLUG não está setada — todas as chamadas a "
            "require_permission(...) vão retornar 403, exceto para masters. "
            "Defina a env (ex: PLATFORM_PRODUCT_SLUG=genesis) no .env do projeto."
        )
    _warned_no_product = True


def _build_context(claims: dict[str, Any], header_tenant: str | None) -> TenantContext:
    is_master = bool(claims.get("is_master") is True)
    jwt_tenant = claims.get("tenant_id") or ""

    if is_master:
        # Master pode escolher tenant via header. Sem header = sem filtro
        # (RLS faz bypass via SESSION_CONTEXT('is_master')=1).
        tenant_id = header_tenant or jwt_tenant or "master"
    else:
        # Não-master ignora o header — sempre confinado ao próprio tenant
        if not jwt_tenant:
            raise TenantNotFound("Token has no tenant_id claim")
        tenant_id = jwt_tenant

    return TenantContext(
        id=tenant_id,
        user_id=claims.get("sub", ""),
        user_email=claims.get("email"),
        is_master=is_master,
        products=list(claims.get("products") or []),
        permissions=dict(claims.get("permissions") or {}),
        raw_claims=claims,
        current_product=SETTINGS.PLATFORM_PRODUCT_SLUG or None,
    )


async def require_tenant(
    request: Request,
    claims: dict[str, Any] = Depends(decode_jwt),
) -> TenantContext:
    header_tenant = request.headers.get(SETTINGS.PLATFORM_TENANT_HEADER)
    ctx = _build_context(claims, header_tenant)
    set_session_context(tenant_id=ctx.id, is_master=ctx.is_master)
    return ctx


def require_permission(permission: str, product_slug: str | None = None) -> Callable:
    """
    Dependency factory: retorna um Depends que valida a permissão `permission`
    no produto atual (PLATFORM_PRODUCT_SLUG) ou no `product_slug` informado.
    Master sempre passa.
    """
    _warn_if_no_product_slug()

    async def _checker(tenant: TenantContext = Depends(require_tenant)) -> TenantContext:
        tenant.check_permission(permission, product_slug)
        return tenant

    return _checker


def require_product(product_slug: str) -> Callable:
    """
    Dependency factory: garante que o tenant está inscrito no produto.
    """

    async def _checker(tenant: TenantContext = Depends(require_tenant)) -> TenantContext:
        tenant.check_product(product_slug)
        return tenant

    return _checker
