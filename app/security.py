"""Paroļu jaukšana un nejauši marķieri. Tikai standarta bibliotēka."""

from __future__ import annotations

import hashlib
import hmac
import secrets

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1


def _encode(password: str) -> bytes:
    return password.encode("utf-8", "surrogatepass")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(_encode(password), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    candidate = hashlib.scrypt(
        _encode(password), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p)
    )
    return hmac.compare_digest(candidate, bytes.fromhex(digest))


# Izmanto neesošam lietotājam, lai atbildes laiks neatklātu, vai konts eksistē.
DUMMY_HASH = hash_password(secrets.token_hex(16))


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(_encode(token)).hexdigest()
