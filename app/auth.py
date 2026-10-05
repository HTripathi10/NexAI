"""JWT-based authentication utilities."""
from datetime import datetime, timedelta
from typing import Optional
import hashlib
from pydantic import ValidationError

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db, get_user_by_username
from app.models import TokenData

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


# ─── Password ─────────────────────────────────────────────────────────────────

def verify_password(plain: str, hashed: str) -> bool:
    # Pre-hash with SHA-256 to bypass bcrypt's 72-byte limit
    pre_hashed = hashlib.sha256(plain.encode('utf-8')).hexdigest()
    return pwd_context.verify(pre_hashed, hashed)


def hash_password(password: str) -> str:
    pre_hashed = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return pwd_context.hash(pre_hashed)


# ─── JWT ──────────────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise credentials_exc
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exc
        token_data = TokenData(username=username)
    except (JWTError, ValidationError):
        raise credentials_exc

    user = await get_user_by_username(db, token_data.username)
    if user is None or not user.is_active:
        raise credentials_exc
    return user
