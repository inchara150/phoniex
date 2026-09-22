"""GitHub webhook HMAC verification (X-Hub-Signature-256)."""
from __future__ import annotations

import hashlib
import hmac


def sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify_signature(secret: str, body: bytes, header: str | None) -> bool:
    """Constant-time check of the raw request body against GitHub's signature."""
    if not secret or not header or not header.startswith("sha256="):
        return False
    return hmac.compare_digest(sign(secret, body), header)
