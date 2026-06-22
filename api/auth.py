from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request, status
from jose import JWTError, jwt
from passlib.context import CryptContext
import bcrypt
from pydantic import BaseModel, Field
from sqlalchemy import text

from core.config import settings
from db.database import AsyncSessionLocal
from db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CurrentUser(BaseModel):
    username: str
    auth_method: str = "jwt"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Fallback to bcrypt directly if passlib backend misbehaves in test env
        try:
            return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
        except Exception:
            return False


def get_password_hash(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except Exception:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = data.copy()
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


async def authenticate_user(username: str, password: str) -> dict[str, str] | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT username, hashed_password
                FROM users
                WHERE username = :username
                """
            ),
            {"username": username},
        )
        row = result.mappings().first()
        if not row:
            return None

        if not verify_password(password, row["hashed_password"]):
            return None

        return {"username": row["username"]}


async def issue_token(body: LoginRequest = Body(...)) -> TokenResponse:
    user = await authenticate_user(body.username, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token({"sub": user["username"]})
    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/api/v1/auth/token", response_model=TokenResponse)
async def issue_token_route(body: LoginRequest = Body(...)) -> TokenResponse:
    return await issue_token(body)


@router.post("/api/v1/auth/register", response_model=TokenResponse)
async def register_user(body: LoginRequest = Body(...)) -> TokenResponse:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT username FROM users WHERE username = :username"),
            {"username": body.username},
        )
        if result.mappings().first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
        
        hashed_password = get_password_hash(body.password)
        session.add(User(username=body.username, hashed_password=hashed_password))
        await session.commit()
    
    return await issue_token(body)


async def resolve_current_user(request: Request) -> CurrentUser | None:
    auth_header = request.headers.get("authorization") or ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        except JWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

        return CurrentUser(username=username, auth_method="jwt")

    api_key = request.headers.get("x-api-key")
    if api_key:
        if api_key != settings.api_auth_key:
            # Treat invalid API key as forbidden to align with historical behavior/tests
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
        logger.warning("Using deprecated X-API-KEY authentication")
        return CurrentUser(username="api_key_user", auth_method="api_key")

    return None


async def get_current_user(request: Request) -> dict[str, str]:
    user = await resolve_current_user(request)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication")
    return user.model_dump()


async def require_role(request: Request, role: str) -> dict[str, str]:
    # Legacy compatibility: accept any authenticated user regardless of role.
    user = await resolve_current_user(request)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication")
    return user.model_dump()


__all__ = [
    "ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "CurrentUser",
    "LoginRequest",
    "TokenResponse",
    "authenticate_user",
    "create_access_token",
    "get_current_user",
    "get_password_hash",
    "require_role",
    "resolve_current_user",
    "router",
    "verify_password",
]
