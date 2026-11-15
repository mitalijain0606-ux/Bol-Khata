"""Phone + password auth — stdlib only (pbkdf2 + HMAC tokens)."""
import hashlib
import hmac
import os
import secrets
import time

from app.config import DATA_DIR

SECRET_FILE = DATA_DIR / ".auth_secret"


TOKEN_TTL = 30 * 24 * 3600


def _secret() -> bytes:
    env = os.getenv("AUTH_SECRET", "").strip()
    if env:                       # set on the host so logins survive restarts
        return env.encode()
    if SECRET_FILE.exists():
        return SECRET_FILE.read_bytes()
    s = secrets.token_bytes(32)
    SECRET_FILE.write_bytes(s)
    return s


def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 120_000)
    return salt.hex() + "$" + dk.hex()


def verify_password(pw: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$", 1)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt_hex), 120_000)
    return hmac.compare_digest(dk.hex(), dk_hex)


def make_token(sid: int) -> str:
    exp = int(time.time()) + TOKEN_TTL
    payload = f"{sid}.{exp}"
    sig = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{payload}.{sig}"


def sid_from_token(token: str | None) -> int | None:
    if not token:
        return None
    token = token.replace("Bearer ", "").strip()
    try:
        sid_s, exp_s, sig = token.split(".", 2)
        sid, exp = int(sid_s), int(exp_s)
    except ValueError:
        return None
    expect = hmac.new(_secret(), f"{sid_s}.{exp_s}".encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(sig, expect) or exp < time.time():
        return None
    return sid
