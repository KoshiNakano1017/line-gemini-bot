from __future__ import annotations

import base64
import hashlib
import hmac


def verify_line_signature(*, channel_secret: str, body: bytes, x_line_signature: str | None) -> bool:
    if not channel_secret:
        return False
    if not x_line_signature:
        return False
    mac = hmac.new(channel_secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode("utf-8")
    return hmac.compare_digest(expected, x_line_signature)
