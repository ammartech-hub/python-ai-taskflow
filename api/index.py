"""Vercel Serverless Function entry point for FastAPI.

Includes ASGI path translation to guarantee that Vercel rewrites preserve
the original client requested URI (such as '/', '/docs', '/health', '/api/...').
"""

import os
import sys

# Ensure the root project directory is on sys.path so 'app' is importable
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.main import app


class VercelPathMiddleware:
    """ASGI middleware to restore the original client path on Vercel rewrites."""

    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            headers = dict(scope.get("headers", []))
            # Vercel sends the client-facing URI in the 'x-matched-path' header
            matched_path = headers.get(b"x-matched-path", b"").decode("utf-8")

            if matched_path and not matched_path.startswith("/api/index"):
                scope["path"] = matched_path
            elif scope.get("path", "").startswith("/api/index.py"):
                scope["path"] = scope["path"][len("/api/index.py"):] or "/"
            elif scope.get("path", "").startswith("/api/index"):
                scope["path"] = scope["path"][len("/api/index"):] or "/"

        await self.asgi_app(scope, receive, send)


# Expose both app and handler wrapped with the Vercel path translator
handler = VercelPathMiddleware(app)
