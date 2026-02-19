"""
auth.py – request authentication for the companion MCP server.

Policy
------
Protected routes require ONE of the following headers to carry a valid secret:
  x-api-key        (primary – used by external callers)
  x-internal-key   (fallback – used by internal services / launchd jobs)

The expected secret is read from env vars in priority order:
  MCP_API_KEY      (preferred name)
  INTERNAL_API_KEY (alias / legacy name)

If neither env var is set the server starts but every protected call returns
503 with a clear configuration message, so misconfiguration is obvious.

/health is always unauthenticated (Render needs it for health-checks).
"""

import logging
import os
from typing import Optional

from fastapi import Header, HTTPException, status

log = logging.getLogger("companion.auth")

# ---------------------------------------------------------------------------
# Read expected key from environment at import time (consistent for the life
# of the process; no per-request env reads).
# ---------------------------------------------------------------------------
_EXPECTED_KEY: Optional[str] = os.environ.get("MCP_API_KEY") or os.environ.get(
    "INTERNAL_API_KEY"
)

if _EXPECTED_KEY:
    log.info("Auth: key loaded from env (length=%d).", len(_EXPECTED_KEY))
else:
    log.warning(
        "Auth: neither MCP_API_KEY nor INTERNAL_API_KEY is set. "
        "All protected routes will return 503 until this is fixed."
    )


def require_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="x-api-key"),
    x_internal_key: Optional[str] = Header(default=None, alias="x-internal-key"),
) -> str:
    """
    FastAPI dependency – inject into any route that must be authenticated.

    Accepts x-api-key OR x-internal-key; first non-None value is validated.
    Returns the validated key string on success.
    Raises HTTPException on failure.
    """
    if _EXPECTED_KEY is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Server misconfiguration: set MCP_API_KEY or INTERNAL_API_KEY "
                "in Render environment variables."
            ),
        )

    provided = x_api_key or x_internal_key

    if provided is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing auth header. Supply x-api-key or x-internal-key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if provided != _EXPECTED_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )

    return provided
