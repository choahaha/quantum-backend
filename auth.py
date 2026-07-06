"""
Supabase JWT verification for authenticated endpoints.

The Supabase project uses legacy HS256 signing, so tokens are verified
locally with the project's JWT secret (Dashboard > Settings > API > JWT).
If the project ever migrates to asymmetric signing keys, replace
_decode() with a PyJWKClient against
{SUPABASE_URL}/auth/v1/.well-known/jwks.json.
"""

import os

import jwt
from fastapi import Header, HTTPException

SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")


def _decode(token: str) -> dict:
    return jwt.decode(
        token,
        SUPABASE_JWT_SECRET,
        algorithms=["HS256"],
        audience="authenticated",
    )


def get_current_user_id(authorization: str = Header(default="")) -> str:
    """FastAPI dependency: extract and verify the Supabase access token."""
    if not SUPABASE_JWT_SECRET:
        raise HTTPException(status_code=500, detail="SUPABASE_JWT_SECRET is not configured")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization[len("Bearer "):].strip()
    try:
        claims = _decode(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token has no subject")
    return user_id
