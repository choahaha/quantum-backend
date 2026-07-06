"""
Service-role Supabase client (bypasses RLS).

Used only for reading mission grading specs and recording graded
submissions via the record_submission() SQL function. Never expose this
client's key to responses or logs.
"""

import os
from functools import lru_cache

from supabase import Client, create_client


@lru_cache(maxsize=1)
def get_admin_client() -> Client:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are not configured")
    return create_client(url, key)
