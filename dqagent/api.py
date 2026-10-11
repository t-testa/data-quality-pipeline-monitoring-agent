import asyncio
import secrets
import sqlite3
import threading
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from dqagent.contracts import Question
from dqagent.diagnostics import diagnose
from dqagent.evidence import EvidenceTools, ToolInput
from dqagent.logging_utils import install_redaction
from dqagent.settings import Settings
from dqagent.store import Store


class RequestBounds:
    """ASGI body limit also handles chunked requests without trusting Content-Length."""

    def __init__(self, app):
        self.app = app

    body_timeout = 10

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        body = bytearray()
        try:
            async with asyncio.timeout(self.body_timeout):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > 8192:
                        return await JSONResponse({"detail": "Request too large"}, 413)(scope, receive, send)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            return await JSONResponse({"detail": "Request body timeout"}, 408)(scope, receive, send)
        chunks = [{"type": "http.request", "body": bytes(body), "more_body": False}]
        index = 0

        async def replay():
            nonlocal index
            if index < len(chunks):
                item = chunks[index]
                index += 1
                return item
            return await receive()

        await self.app(scope, replay, send)


def create_app(settings=None):
    settings = settings or Settings()
    settings.require_auth()
    install_redaction(settings)
    store = Store(settings.data_dir)
    tools = EvidenceTools(store)
    app = FastAPI(
        title="Data Quality & Pipeline Monitoring",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(RequestBounds)
    auth = HTTPBearer(auto_error=False)
    lock, calls = threading.Lock(), {"read": [], "diagnose": []}

    def principal(credentials: HTTPAuthorizationCredentials | None = Depends(auth)):
        token = (credentials.credentials if credentials else "").encode("utf-8")
        if secrets.compare_digest(token, settings.diagnostic_token.get_secret_value().encode("utf-8")):
            role = "diagnose"
        elif secrets.compare_digest(token, settings.api_token.get_secret_value().encode("utf-8")):
            role = "read"
        else:
            raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
        now = time.monotonic()
        with lock:
            calls[role] = [t for t in calls[role] if now - t < 60]
            if len(calls[role]) >= 120:
                raise HTTPException(429, "Request limit exceeded")
            calls[role].append(now)
        return role

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'",
                "Referrer-Policy": "no-referrer",
            }
        )
        return response

    @app.exception_handler(Exception)
    async def sanitized_error(request, exc):
        return JSONResponse({"detail": "Internal operation failed"}, 500)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/ready")
    def readiness():
        try:
            with store.db() as db:
                db.execute("SELECT id FROM runs LIMIT 1").fetchone()
            return {"status": "ready"}
        except sqlite3.Error:
            return JSONResponse({"status": "unavailable"}, 503)

    static = Path(__file__).parent / "static"

    @app.get("/")
    def dashboard():
        return FileResponse(static / "index.html")

    @app.get("/app.js")
    def javascript():
        return FileResponse(static / "app.js", media_type="text/javascript")

    @app.get("/style.css")
    def css():
        return FileResponse(static / "style.css", media_type="text/css")

    @app.get("/api/openapi.json", dependencies=[Depends(principal)])
    def schema():
        return app.openapi()

    @app.get("/api/overview", dependencies=[Depends(principal)])
    def overview():
        return store.overview()

    @app.get("/api/pipelines", dependencies=[Depends(principal)])
    def pipelines():
        return store.pipelines()

    @app.get("/api/runs", dependencies=[Depends(principal)])
    def runs(
        pipeline: str | None = Query(None, pattern=r"^[A-Za-z0-9_-]{1,80}$"),
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0, le=100000),
    ):
        return store.runs(pipeline, limit, offset)

    @app.get("/api/runs/{run_id}", dependencies=[Depends(principal)])
    def run(run_id: str):
        try:
            return tools.call("get_incident_details", {"run_id": run_id, "limit": 100}, True)["data"]
        except ValueError as exc:
            raise HTTPException(404, "Run not found") from exc

    @app.post("/api/tools/{name}", dependencies=[Depends(principal)])
    def tool(name: str, args: ToolInput):
        try:
            return tools.call(name, args.model_dump(), True)
        except ValueError as exc:
            raise HTTPException(400, "Invalid tool or scope") from exc

    @app.post("/api/diagnose")
    def investigation(question: Question, role=Depends(principal)):
        if question.use_ai and role != "diagnose":
            raise HTTPException(403, "AI access requires diagnostic role")
        try:
            return diagnose(store, settings, question)
        except ValueError as exc:
            raise HTTPException(404, "Run not found in requested pipeline") from exc

    return app
