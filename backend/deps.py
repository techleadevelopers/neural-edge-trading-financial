import os
from fastapi import Header, HTTPException, status
from services.utils import AUTH_TOKEN


def verify_token(authorization: str = Header(default=None)):
    """
    Protecao simples via header Authorization: Bearer <token>.
    Se AUTH_TOKEN nao estiver configurado, nao bloqueia chamadas.
    """
    if not AUTH_TOKEN:
        return
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token.strip() != AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
