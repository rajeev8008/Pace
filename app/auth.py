import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel


router = APIRouter(prefix="/auth", tags=["authentication"])
COOKIE_NAME = "dayflow_session"
SESSION_SECONDS = 60 * 60 * 24 * 7


class LoginRequest(BaseModel):
    username: str
    password: str


def _setting(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"{name} is not configured")
    return value


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_session(username: str) -> str:
    payload = _encode(json.dumps({"sub": username, "exp": int(time.time()) + SESSION_SECONDS}, separators=(",", ":")).encode())
    signature = _encode(hmac.new(_setting("SESSION_SECRET").encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def verify_session(token: str) -> str:
    try:
        payload, signature = token.split(".", 1)
        expected = _encode(hmac.new(_setting("SESSION_SECRET").encode(), payload.encode(), hashlib.sha256).digest())
        data = json.loads(_decode(payload))
        if not hmac.compare_digest(signature, expected) or data["exp"] < time.time():
            raise ValueError
        return str(data["sub"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required") from None


def require_auth(dayflow_session: str | None = Cookie(default=None, alias=COOKIE_NAME)) -> str:
    if not dayflow_session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    username = verify_session(dayflow_session)
    if not hmac.compare_digest(username, _setting("APP_USERNAME")):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    return username


@router.post("/login")
def login(credentials: LoginRequest, response: Response) -> dict[str, str]:
    valid_user = hmac.compare_digest(credentials.username, _setting("APP_USERNAME"))
    valid_password = hmac.compare_digest(credentials.password, _setting("APP_PASSWORD"))
    if not (valid_user and valid_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    response.set_cookie(
        COOKIE_NAME,
        create_session(credentials.username),
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="strict",
    )
    return {"username": credentials.username}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)


@router.get("/me")
def me(username: str = Depends(require_auth)) -> dict[str, str]:
    return {"username": username}
