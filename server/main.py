"""
main.py – Companion MCP server.

Routes
------
GET  /health          – unauthenticated; Render health-check target.
POST /mcp/intent      – authenticated; accepts a JSON MCP intent payload.
POST /mcp             – authenticated; generic MCP dispatch.

Port
----
Reads $PORT env var (Render injects this).  Defaults to 8000 for local dev.

Auth
----
See auth.py.  Pass x-api-key or x-internal-key on protected routes.

Run locally
-----------
  pip install -r server/requirements.txt
  MCP_API_KEY=dev-secret PORT=8000 uvicorn server.main:app --reload

Render start command
--------------------
  uvicorn server.main:app --host 0.0.0.0 --port $PORT
"""

import datetime
import logging
import os
from typing import Any, Dict

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from server.auth import require_api_key

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("companion.server")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
VERSION = "1.0.0"

app = FastAPI(
    title="Companion MCP Server",
    version=VERSION,
    docs_url=None,   # disable Swagger UI in prod; enable locally if desired
    redoc_url=None,
)


# ---------------------------------------------------------------------------
# /health  – no auth, always reachable by Render health-checker.
# ---------------------------------------------------------------------------
@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "service": "companion_mcp_server",
            "version": VERSION,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }
    )


# ---------------------------------------------------------------------------
# /mcp/intent  – authenticated MCP intent handler.
# ---------------------------------------------------------------------------
@app.post("/mcp/intent")
async def mcp_intent(
    request: Request,
    _key: str = Depends(require_api_key),
) -> JSONResponse:
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON body"}, status_code=400)

    intent = payload.get("intent") or payload.get("method") or "unknown"
    log.info("mcp/intent received: intent=%r params=%r", intent, payload.get("params"))

    # Placeholder – replace with real intent dispatch logic.
    return JSONResponse(
        {
            "ok": True,
            "intent": intent,
            "result": "dry-run acknowledged",
        }
    )


# ---------------------------------------------------------------------------
# /mcp  – authenticated generic MCP endpoint.
# ---------------------------------------------------------------------------
@app.post("/mcp")
async def mcp(
    request: Request,
    _key: str = Depends(require_api_key),
) -> JSONResponse:
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON body"}, status_code=400)

    method = payload.get("method", "unknown")
    log.info("mcp received: method=%r", method)

    if method == "tools/list":
        return JSONResponse(
            {
                "ok": True,
                "tools": [
                    {"name": "notion_sync", "description": "Sync Notion databases."},
                ],
            }
        )

    return JSONResponse({"ok": True, "method": method, "result": "acknowledged"})


# ---------------------------------------------------------------------------
# Startup log so Render logs show the server came up cleanly.
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup() -> None:
    port = os.environ.get("PORT", "8000")
    log.info("Companion MCP server v%s starting on port %s.", VERSION, port)


# ---------------------------------------------------------------------------
# Entry-point for direct execution: python -m server.main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("server.main:app", host="0.0.0.0", port=port, reload=False)
