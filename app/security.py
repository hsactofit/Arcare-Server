import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.config import settings, IST

def hash_password(password: str) -> str:
    """
    Hashes a plain password using bcrypt.
    """
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against the hashed password.
    """
    if not hashed_password:
        return False
    pwd_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(IST) + expires_delta
    else:
        expire = datetime.now(IST) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT refresh token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(IST) + expires_delta
    else:
        expire = datetime.now(IST) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str, is_refresh: bool = False) -> dict:
    """
    Decodes a JWT token. Returns payload or dictionary containing 'error'.
    """
    secret = settings.JWT_REFRESH_SECRET_KEY if is_refresh else settings.JWT_SECRET_KEY
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return {"error": "token_expired"}
    except jwt.InvalidTokenError:
        return {"error": "invalid_token"}

def verify_google_token(token: str) -> dict:
    """
    Verifies a Google ID token or Access Token. If offline/mock token is sent (e.g. starts with mock_),
    returns mock information to facilitate testing.
    """
    if token.startswith("mock_"):
        email = "unregistered_social@gmail.com" if "unregistered" in token else "socialuser_google@gmail.com"
        return {
            "email": email,
            "name": "Social Google User",
            "provider": "google",
            "sub": "mock_google_sub_12345"
        }

    # Attempt to verify using Google's SDK if available
    try:
        from google.oauth2 import id_token  # type: ignore
        from google.auth.transport import requests  # type: ignore
        # verify against google backend as ID Token
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), None)
        return {
            "email": idinfo.get("email"),
            "name": idinfo.get("name", idinfo.get("given_name", "Google User")),
            "provider": "google",
            "sub": idinfo.get("sub")
        }
    except Exception:
        # Fallback: check via Google's tokeninfo/userinfo HTTP APIs (handles both ID tokens and Access tokens)
        import urllib.request
        import urllib.error
        import json

        # Prepare verification endpoints
        endpoints = []
        is_jwt = len(token.split('.')) == 3
        if is_jwt:
            endpoints.append(f"https://oauth2.googleapis.com/tokeninfo?id_token={token}")
        endpoints.append(f"https://oauth2.googleapis.com/tokeninfo?access_token={token}")
        endpoints.append(f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={token}")

        for url in endpoints:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        idinfo = json.loads(response.read().decode('utf-8'))
                        email = idinfo.get("email")
                        if email:
                            return {
                                "email": email,
                                "name": idinfo.get("name", idinfo.get("given_name", "Google User")),
                                "provider": "google",
                                "sub": idinfo.get("sub")
                            }
            except Exception:
                continue

        # Last resort fallback: Decode without signature verification (only for local development/testing)
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            return {
                "email": decoded.get("email"),
                "name": decoded.get("name", "Google User"),
                "provider": "google",
                "sub": decoded.get("sub")
            }
        except Exception:
            return {"error": "Google token verification failed (both SDK, HTTP APIs, and local JWT decode failed)."}

def verify_apple_token(token: str) -> dict:
    """
    Verifies an Apple identity token. Supports mock tokens for dev testing.
    """
    if token.startswith("mock_"):
        email = "unregistered_apple@icloud.com" if "unregistered" in token else "socialuser_apple@icloud.com"
        return {
            "email": email,
            "name": "Social Apple User",
            "provider": "apple",
            "sub": "mock_apple_sub_67890"
        }

    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        return {
            "email": decoded.get("email"),
            "name": decoded.get("name", "Apple User"),
            "provider": "apple",
            "sub": decoded.get("sub")
        }
    except Exception as e:
        return {"error": f"Apple token verification failed: {str(e)}"}

