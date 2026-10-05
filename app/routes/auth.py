"""Auth routes: register + login."""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password, verify_password, create_access_token
from app.config import get_settings
from app.database import get_db, get_user_by_username, create_user
from app.models import Token, UserCreate, UserCreated, LoginRequest

settings = get_settings()
router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserCreated)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_username(db, user_in.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken.")
    hashed = hash_password(user_in.password)
    user = await create_user(db, user_in.username, hashed)
    return {"id": user.id, "username": user.username, "message": "User created successfully."}


@router.post("/token", response_model=Token)
async def login(
    form_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_username(db, form_data.username)
    if not user or not user.is_active or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    expire = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    token = create_access_token({"sub": user.username}, expire)
    return Token(
        access_token=token,
        token_type="bearer",
        expires_in=int(expire.total_seconds()),
    )
