"""
Supabase JWT verification for authenticated endpoints.

The Supabase project uses asymmetric JWT signing keys, so tokens are
verified against the public keys published at
{SUPABASE_URL}/auth/v1/.well-known/jwks.json. No secret is needed.
"""

import os

import jwt
from fastapi import Header, HTTPException

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")

# PyJWKClient caches the key set and refetches when it sees an unknown kid,
# so a future key rotation in Supabase needs no redeploy.
_jwks_client = (
    jwt.PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json", cache_keys=True)
    if SUPABASE_URL
    else None
)


def _decode(token: str) -> dict:
    signing_key = _jwks_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256", "RS256"],
        audience="authenticated",
        # Tolerate small clock skew between this server and Supabase Auth
        # (a future iat otherwise raises ImmatureSignatureError).
        leeway=30,
    )


def get_current_user_id(authorization: str = Header(default="")) -> str:
    """FastAPI dependency: extract and verify the Supabase access token."""
    if _jwks_client is None:
        raise HTTPException(status_code=500, detail="SUPABASE_URL is not configured")

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
