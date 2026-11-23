import hmac
import ipaddress
import os
import secrets
from urllib.parse import urlsplit, parse_qs

ALLOWED_ORIGINS = {"null", "file://", "http://localhost:3000", "http://127.0.0.1:3000"}


def backend_token() -> str:
    return os.environ.get("WOLFTRACK_AUTH_TOKEN") or secrets.token_urlsafe(32)


def is_loopback_host(host: str) -> bool:
    try:
        hostname = urlsplit(f"//{host}").hostname or ""
    except ValueError:
        return False
    if hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


class BackendSecurityMiddleware:
    def __init__(self, app, token: str):
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"}:
            return await self.app(scope, receive, send)

        headers = {
            key.lower().decode("latin1"): value.decode("latin1")
            for key, value in scope.get("headers", [])
        }
        host = headers.get("host")
        if not host or (not is_loopback_host(host) and os.environ.get("WOLFTRACK_ALLOW_REMOTE_BINDING") != "true"):
            return await self._reject(scope, send, 403, "Invalid Host header")

        origin = headers.get("origin")
        if scope["type"] == "websocket" and origin is not None and origin not in ALLOWED_ORIGINS:
            return await self._reject(scope, send, 403, "Origin not allowed")

        path = scope.get("path", "")
        if path.startswith("/api/") or path == "/ws/stream":
            query = parse_qs(scope.get("query_string", b"").decode())
            if scope["type"] == "websocket":
                supplied = (query.get("token") or [""])[0]
            else:
                supplied = headers.get("authorization", "").removeprefix("Bearer ")
            if not hmac.compare_digest(supplied, self.token):
                return await self._reject(scope, send, 401, "Unauthorized")

        return await self.app(scope, receive, send)

    async def _reject(self, scope, send, status: int, detail: str):
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 4403 if status == 403 else 4401, "reason": detail})
        else:
            body = (f'{{"detail":"{detail}"}}').encode()
            await send({"type": "http.response.start", "status": status, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
            await send({"type": "http.response.body", "body": body})
