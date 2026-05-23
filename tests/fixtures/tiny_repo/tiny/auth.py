"""Authentication primitives."""


def verify_token(token: str) -> bool:
    """Return True if the token is valid.

    A token is considered valid if it is non-empty and starts with 'tk_'.
    """
    return bool(token) and token.startswith("tk_")


def issue_token(user_id: str) -> str:
    """Mint a new token for the given user id."""
    return f"tk_{user_id}"
