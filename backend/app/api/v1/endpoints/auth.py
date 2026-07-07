from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.security import create_access_token, verify_password
from app.schemas.auth import TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])
_limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Obtain a JWT access token",
    description=(
        "Exchange username + password for a Bearer token. "
        "Credentials are configured via API_USERNAME and API_PASSWORD env vars."
    ),
)
@_limiter.limit("10/minute")
async def login(request: Request, form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    settings = get_settings()

    credentials_ok = form.username == settings.API_USERNAME and verify_password(
        form.password, _hashed_admin_password()
    )
    if not credentials_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=form.username)
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def _hashed_admin_password() -> str:
    """Lazily hash the admin password on first call and cache it in-process."""
    global _cached_hash
    if _cached_hash is None:
        from app.core.security import hash_password

        _cached_hash = hash_password(get_settings().API_PASSWORD)
    return _cached_hash


_cached_hash: str | None = None
