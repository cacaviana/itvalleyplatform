"""
itvalleyplatform — multi-tenant SDK plug-and-play.

Lazy: importar `itvalleyplatform` (ou rodar a CLI) NÃO força o carregamento
do middleware/JWT. Só puxa quando o app realmente faz
`from itvalleyplatform import require_tenant`. Isso permite que a CLI
`itvalleyplatform generate-rls` rode em qualquer diretório, sem .env.
"""

__version__ = "0.1.0"

__all__ = [
    "TenantContext",
    "require_tenant",
    "require_permission",
    "require_product",
    "InvalidToken",
    "PermissionDenied",
    "ProductNotSubscribed",
    "TenantNotFound",
    "TokenMissing",
]


def __getattr__(name: str):
    if name == "TenantContext":
        from .tenant_context import TenantContext

        return TenantContext
    if name in {"require_tenant", "require_permission", "require_product"}:
        from . import middleware

        return getattr(middleware, name)
    if name in {
        "InvalidToken",
        "PermissionDenied",
        "ProductNotSubscribed",
        "TenantNotFound",
        "TokenMissing",
    }:
        from . import exceptions

        return getattr(exceptions, name)
    raise AttributeError(f"module 'itvalleyplatform' has no attribute {name!r}")
