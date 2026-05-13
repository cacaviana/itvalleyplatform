from typing import Any, Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from itvalleysecurity.config import SETTINGS as SEC_SETTINGS
from itvalleysecurity.core import verify_access
from itvalleysecurity.exceptions import InvalidToken as SecInvalidToken
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from .exceptions import InvalidToken, TokenMissing

_security = HTTPBearer(auto_error=False)


def _extract_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    if SEC_SETTINGS.EV_TOKEN_SOURCE in {"auto", "bearer"} and credentials and credentials.credentials:
        return credentials.credentials
    if SEC_SETTINGS.EV_TOKEN_SOURCE in {"auto", "cookie"}:
        return request.cookies.get(SEC_SETTINGS.EV_COOKIE_ACCESS)
    return None


async def decode_jwt(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
) -> dict[str, Any]:
    token = _extract_token(request, credentials)
    if not token:
        raise TokenMissing()
    try:
        return verify_access(token)
    except SecInvalidToken as e:
        raise InvalidToken(str(e))
    except ExpiredSignatureError:
        raise InvalidToken("Token has expired")
    except InvalidTokenError as e:
        raise InvalidToken(str(e))
