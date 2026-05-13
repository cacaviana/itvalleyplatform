from dataclasses import dataclass, field
from typing import Any

from .exceptions import PermissionDenied, ProductNotSubscribed


@dataclass
class TenantContext:
    """
    Contexto da request — tudo que a rota precisa saber sobre o tenant
    e o usuário autenticado. Construído pelo middleware a partir do JWT.
    """

    id: str
    user_id: str
    user_email: str | None = None
    is_master: bool = False
    products: list[str] = field(default_factory=list)
    permissions: dict[str, list[str]] = field(default_factory=dict)
    raw_claims: dict[str, Any] = field(default_factory=dict)
    current_product: str | None = None

    def has_product(self, product_slug: str) -> bool:
        if self.is_master:
            return True
        return product_slug in self.products

    def check_product(self, product_slug: str) -> None:
        if not self.has_product(product_slug):
            raise ProductNotSubscribed(product_slug)

    def has_permission(self, permission: str, product_slug: str | None = None) -> bool:
        if self.is_master:
            return True
        slug = product_slug or self.current_product
        if not slug:
            return False
        return permission in self.permissions.get(slug, [])

    def check_permission(self, permission: str, product_slug: str | None = None) -> None:
        if not self.has_permission(permission, product_slug):
            raise PermissionDenied(permission)
