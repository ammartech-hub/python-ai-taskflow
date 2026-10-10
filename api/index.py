"""Vercel Serverless Function entry point for FastAPI.

Normalizes request paths under Vercel serverless rewrites and provides diagnostics.
"""

import os
import sys
import json
import logging
import urllib.parse

# Ensure the root project directory is on sys.path so 'app' is importable
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.main import app as _fastapi_app

logger = logging.getLogger("vercel_bridge")


class VercelPathMiddleware:
    """ASGI middleware to normalize paths and headers under Vercel serverless rewrites."""

    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            raw_headers = dict(scope.get("headers", []))
            headers_lower = {
                k.decode("utf-8", "ignore").lower(): v.decode("utf-8", "ignore")
                for k, v in raw_headers.items()
            }
            current_path = scope.get("path", "")
            query_string = scope.get("query_string", b"").decode("utf-8", "ignore")

            # Diagnostic endpoint
            if "debug-info" in current_path or "__debug" in query_string or "debug-info" in headers_lower.get("x-matched-path", ""):
                diagnostic = {
                    "scope_path": current_path,
                    "query_string": query_string,
                    "headers": headers_lower,
                }
                body = json.dumps(diagnostic, indent=2).encode("utf-8")
                await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode("utf-8")),
                    ],
                })
                await send({"type": "http.response.body", "body": body})
                return

            # 1. First priority: Explicit rewrite query parameter __path
            if "__path=" in query_string:
                params = urllib.parse.parse_qs(query_string)
                if "__path" in params and params["__path"]:
                    scope["path"] = params["__path"][0]

            # 2. Second priority: Vercel Edge Headers
            elif headers_lower.get("x-matched-path") and not headers_lower["x-matched-path"].startswith("/api/index"):
                scope["path"] = headers_lower["x-matched-path"]

            # 3. Third priority: Strip /api/index.py or /api/index prefix if present
            elif current_path.startswith("/api/index.py"):
                scope["path"] = current_path[len("/api/index.py"):] or "/"
            elif current_path.startswith("/api/index"):
                scope["path"] = current_path[len("/api/index"):] or "/"

        await self.asgi_app(scope, receive, send)


app = VercelPathMiddleware(_fastapi_app)
handler = app
