from fastapi import Header, HTTPException


def require_internal_token(x_internal_token: str | None = Header(default=None)) -> None:
    # Placeholder security hook. Tighten in production.
    if x_internal_token is not None and len(x_internal_token) < 8:
        raise HTTPException(status_code=401, detail="Invalid internal token")
