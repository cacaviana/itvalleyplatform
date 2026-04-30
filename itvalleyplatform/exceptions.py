from fastapi import HTTPException, status


class TokenMissing(HTTPException):
    def __init__(self, detail: str = "Access token not provided"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidToken(HTTPException):
    def __init__(self, detail: str = "Invalid token"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class TenantNotFound(HTTPException):
    def __init__(self, detail: str = "Tenant not found in token"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ProductNotSubscribed(HTTPException):
    def __init__(self, product: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tenant has no subscription to product '{product}'",
        )


class PermissionDenied(HTTPException):
    def __init__(self, permission: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{permission}' required",
        )
