"""Phone + password auth — stdlib only (pbkdf2 + HMAC tokens)."""
import hashlib
import hmac
import secrets

from app.config import DATA_DIR

SECRET_FILE = DATA_DIR / ".auth_secret"


def _secret() -> bytes:
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
    payload = str(sid).encode()
    sig = hmac.new(_secret(), payload, hashlib.sha256).hexdigest()[:32]
    return f"{sid}.{sig}"


def sid_from_token(token: str | None) -> int | None:
    if not token:
        return None
    token = token.replace("Bearer ", "").strip()
    try:
        sid_s, sig = token.split(".", 1)
        sid = int(sid_s)
    except ValueError:
        return None
    expect = hmac.new(_secret(), sid_s.encode(), hashlib.sha256).hexdigest()[:32]
    return sid if hmac.compare_digest(sig, expect) else None
