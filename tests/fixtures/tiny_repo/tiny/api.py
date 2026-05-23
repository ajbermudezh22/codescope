"""HTTP-shaped helpers that lean on auth."""

from tiny.auth import verify_token


def authorize_request(token: str) -> dict:
    """Authorize an incoming request; returns a status dict."""
    if verify_token(token):
        return {"ok": True}
    return {"ok": False, "reason": "invalid_token"}
