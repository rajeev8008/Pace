import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ExternalProfile, User


router = APIRouter(prefix="/auth", tags=["authentication"])
COOKIE_NAME = "pace_session"
SESSION_SECONDS = 60 * 60 * 24 * 7
OAUTH_STATE_COOKIE = "pace_oauth_state"
OWNER_USER_ID = 1


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


def _setting(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"{name} is not configured")
    return value


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"{_encode(salt)}.{_encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        salt, expected = encoded.split(".", 1)
        digest = hashlib.scrypt(password.encode(), salt=_decode(salt), n=2**14, r=8, p=1)
        return hmac.compare_digest(_encode(digest), expected)
    except (ValueError, TypeError):
        return False


def create_session(user_id: int) -> str:
    now = int(time.time())
    header = _encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _encode(json.dumps({"sub": user_id, "iat": now, "exp": now + SESSION_SECONDS}, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}"
    signature = _encode(hmac.new(_setting("SESSION_SECRET").encode(), signing_input.encode(), hashlib.sha256).digest())
    return f"{signing_input}.{signature}"


def verify_session(token: str) -> int:
    try:
        header, payload, signature = token.split(".")
        metadata = json.loads(_decode(header))
        signing_input = f"{header}.{payload}"
        expected = _encode(hmac.new(_setting("SESSION_SECRET").encode(), signing_input.encode(), hashlib.sha256).digest())
        data = json.loads(_decode(payload))
        if metadata != {"alg": "HS256", "typ": "JWT"} or not hmac.compare_digest(signature, expected) or data["exp"] < time.time() or not isinstance(data.get("sub"), int):
            raise ValueError
        return data["sub"]
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required") from None


def require_auth(
    pace_session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    db: Session = Depends(get_db),
) -> int:
    if not pace_session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    user_id = verify_session(pace_session)
    if user_id != OWNER_USER_ID or not db.get(User, OWNER_USER_ID):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    return OWNER_USER_ID


def _profile(user: User) -> dict[str, str | None]:
    return {"username": user.username, "email": user.email, "display_name": user.display_name}


def _set_session(response: Response, user: User) -> dict[str, str | None]:
    response.set_cookie(
        COOKIE_NAME,
        create_session(user.id),
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="strict",
    )
    return _profile(user)


def _oauth_url(request: Request, provider: str) -> str:
    base = os.getenv("OAUTH_BASE_URL", "").rstrip("/")
    return f"{base}/auth/oauth/{provider}/callback" if base else str(request.url_for("oauth_callback", provider=provider))


def _request_json(url: str, *, data: dict[str, str] | None = None, token: str | None = None) -> dict | list:
    headers = {"Accept": "application/json", "User-Agent": "Pace"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = UrlRequest(url, data=urlencode(data).encode() if data else None, headers=headers)
    try:
        with urlopen(request, timeout=10) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "OAuth provider request failed") from error


def _oauth_owner(db: Session, provider: str, identity: str, email: str, name: str, username: str) -> User:
    user = db.get(User, OWNER_USER_ID)
    if user is not None and user.email and user.email.lower() != email.lower():
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This OAuth account does not match the Pace owner email")
    if user is None:
        clean_username = re.sub(r"[^A-Za-z0-9_.-]", "", username)[:64] or "pace-user"
        user = User(id=OWNER_USER_ID, username=clean_username if len(clean_username) >= 3 else f"{clean_username}pace", email=email.lower(), display_name=name[:100], password_hash=None, created_at=datetime.now(timezone.utc))
        db.add(user)
    setattr(user, "github_id" if provider == "github" else "google_id", identity)
    user.email = user.email or email.lower()
    db.commit(); db.refresh(user)
    return user


@router.get("/oauth/{provider}")
def oauth_start(provider: str, request: Request) -> RedirectResponse:
    if provider not in {"github", "google"}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "OAuth provider not found")
    state = secrets.token_urlsafe(32)
    redirect_uri = _oauth_url(request, provider)
    if provider == "github":
        url = "https://github.com/login/oauth/authorize?" + urlencode({"client_id": _setting("GITHUB_CLIENT_ID"), "redirect_uri": redirect_uri, "scope": "user:email", "state": state})
    else:
        url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({"client_id": _setting("GOOGLE_CLIENT_ID"), "redirect_uri": redirect_uri, "response_type": "code", "scope": "openid email profile", "state": state, "prompt": "select_account"})
    response = RedirectResponse(url)
    response.set_cookie(OAUTH_STATE_COOKIE, state, max_age=600, httponly=True, secure=os.getenv("COOKIE_SECURE", "false").lower() == "true", samesite="lax")
    return response


@router.get("/oauth/{provider}/callback", name="oauth_callback")
def oauth_callback(provider: str, request: Request, code: str, state: str, db: Session = Depends(get_db), pace_oauth_state: str | None = Cookie(default=None, alias=OAUTH_STATE_COOKIE)) -> RedirectResponse:
    if provider not in {"github", "google"} or not pace_oauth_state or not hmac.compare_digest(state, pace_oauth_state):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid OAuth state")
    redirect_uri = _oauth_url(request, provider)
    if provider == "github":
        token_data = _request_json("https://github.com/login/oauth/access_token", data={"client_id": _setting("GITHUB_CLIENT_ID"), "client_secret": _setting("GITHUB_CLIENT_SECRET"), "code": code, "redirect_uri": redirect_uri})
        token = token_data.get("access_token")
        if not token:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "GitHub did not provide an access token")
        profile = _request_json("https://api.github.com/user", token=token)
        emails = _request_json("https://api.github.com/user/emails", token=token)
        verified = next((item["email"] for item in emails if item.get("primary") and item.get("verified")), None)
        if not token or not verified:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "GitHub did not provide a verified email")
        user = _oauth_owner(db, provider, str(profile["id"]), verified, profile.get("name") or profile["login"], profile["login"])
        connection = db.scalar(select(ExternalProfile).where(ExternalProfile.user_id == user.id, ExternalProfile.provider == "GITHUB"))
        if connection is None:
            db.add(ExternalProfile(user_id=user.id, provider="GITHUB", username=profile["login"], profile_url=profile["html_url"]))
        else:
            connection.username, connection.profile_url = profile["login"], profile["html_url"]
        db.commit()
    else:
        token_data = _request_json("https://oauth2.googleapis.com/token", data={"client_id": _setting("GOOGLE_CLIENT_ID"), "client_secret": _setting("GOOGLE_CLIENT_SECRET"), "code": code, "grant_type": "authorization_code", "redirect_uri": redirect_uri})
        token = token_data.get("access_token")
        if not token:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Google did not provide an access token")
        profile = _request_json("https://openidconnect.googleapis.com/v1/userinfo", token=token)
        if not token or not profile.get("email_verified"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Google did not provide a verified email")
        user = _oauth_owner(db, provider, profile["sub"], profile["email"], profile.get("name") or profile["email"].split("@", 1)[0], profile["email"].split("@", 1)[0])
    response = RedirectResponse("/")
    response.delete_cookie(OAUTH_STATE_COOKIE)
    _set_session(response, user)
    return response


@router.get("/oauth-providers")
def oauth_providers() -> dict[str, bool]:
    return {
        "github": bool(os.getenv("GITHUB_CLIENT_ID") and os.getenv("GITHUB_CLIENT_SECRET")),
        "google": bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET")),
    }


@router.post("/login")
def login(credentials: LoginRequest, response: Response, db: Session = Depends(get_db)) -> dict[str, str | None]:
    owner = db.get(User, OWNER_USER_ID)
    if owner is None:
        env_user, env_password = os.getenv("APP_USERNAME", ""), os.getenv("APP_PASSWORD", "")
        if env_user and env_password and hmac.compare_digest(credentials.username, env_user) and hmac.compare_digest(credentials.password, env_password):
            owner = User(id=OWNER_USER_ID, username=env_user, email=None, display_name=env_user, password_hash=hash_password(env_password), created_at=datetime.now(timezone.utc))
            db.add(owner)
            db.commit()
    matches_owner = owner is not None and credentials.username.lower() in {owner.username.lower(), (owner.email or "").lower()}
    if not matches_owner or not owner.password_hash or not verify_password(credentials.password, owner.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    return _set_session(response, owner)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)


@router.get("/me")
def me(user_id: int = Depends(require_auth), db: Session = Depends(get_db)) -> dict[str, str | None]:
    return _profile(db.get(User, user_id))
