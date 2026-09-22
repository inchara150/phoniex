"""FastAPI webhook receiver."""
from __future__ import annotations

import json
import logging
import threading

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from phoenix_contracts import FailureEvent
from .events import parse_failure
from .pipeline import FixPipeline
from .security import verify_signature

log = logging.getLogger("phoenix.webhook")


class _Claims:
    """In-memory idempotency guard: one fix attempt per (repo, sha). Swap for Redis if you scale out."""
    def __init__(self) -> None:
        self._s: set[str] = set()
        self._lock = threading.Lock()

    def claim(self, key: str) -> bool:
        with self._lock:
            if key in self._s:
                return False
            self._s.add(key)
            return True

    def release(self, key: str) -> None:
        with self._lock:
            self._s.discard(key)


def create_app(*, secret: str, pipeline: FixPipeline) -> FastAPI:
    if not secret:
        raise ValueError("webhook secret must be set")
    app = FastAPI(title="Phoenix CI/CD webhook")
    claims = _Claims()

    def run(failure: FailureEvent) -> None:
        try:
            if not pipeline.handle(failure).ok:
                claims.release(failure.key)      # allow a retry after skip/fail
        except Exception:
            log.exception("pipeline crashed for %s", failure.key)
            claims.release(failure.key)

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True}

    @app.post("/webhook")
    async def webhook(request: Request, background: BackgroundTasks,
                      x_hub_signature_256: str | None = Header(default=None),
                      x_github_event: str | None = Header(default=None)):
        body = await request.body()                      # raw bytes: HMAC must use these
        if not verify_signature(secret, body, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="invalid signature")
        if x_github_event == "ping":
            return {"status": "pong"}
        try:
            payload = json.loads(body)
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid JSON")
        failure = parse_failure(x_github_event or "", payload)
        if failure is None:
            return {"status": "ignored"}
        if not claims.claim(failure.key):
            return {"status": "duplicate"}
        background.add_task(run, failure)                # GitHub times out at 10s
        return JSONResponse({"status": "accepted", "key": failure.key}, status_code=202)

    return app
