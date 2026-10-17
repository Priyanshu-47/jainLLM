"""Experimental generation HTTP app (Task 89) — SEPARATE from the retrieval API.

    GET  /health   generation + retrieval + local-Ollama status
    POST /answer   question -> BM25 evidence -> local model -> cited answer

Hard constraints implemented here:
  * Binds to ``127.0.0.1:8101`` by default (8100 = retrieval API,
    8000 = FanPulse, 11434 = Ollama — none of them are touched).
  * No routes are added to the production retrieval API.
  * No model downloads, no training, no external AI APIs: the provider
    rejects any non-loopback endpoint.
  * Request body capped; structured logs never include full question text.

Requires fastapi + pydantic v2 + uvicorn in the repo ``.venv`` (declared in
``docs/generation_mvp.md``).
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from svk_corpus.generation.answer import AnswerService, ValidationError
from svk_corpus.generation.provider import OllamaProvider
from svk_corpus.generation.schemas import (AnswerRequest, AnswerResponseModel,
                                           GenerationHealthResponseModel)

LOG = logging.getLogger("svk_corpus.generation.api")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8101             # retrieval 8100 / FanPulse 8000 / Ollama 11434
MAX_BODY_BYTES = 16 * 1024      # question-only payloads


class ServiceUnavailable(Exception):
    """Generation service failed to initialize."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("generation service unavailable")


def _query_fingerprint(q: str) -> str:
    """Stable short hash of a question — logs identify queries without
    storing their text."""
    return hashlib.sha256(q.encode("utf-8")).hexdigest()[:12]


def create_generation_app(
    root: Path | None = None,
    service: AnswerService | None = None,
    provider: OllamaProvider | None = None,
    init_errors: list[str] | None = None,
):
    """Build the isolated generation FastAPI app (port 8101).

    ``service`` (and/or ``provider``) may be injected for tests; otherwise
    the service is built at startup via ``AnswerService.from_repo`` (loads
    the corpus + BM25 index once — same policy path as the retrieval API).
    """
    root = Path(root) if root is not None else None
    errors: list[str] = list(init_errors or [])
    state: dict[str, Any] = {"service": service, "errors": errors}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if state["service"] is None and not state["errors"]:
            try:
                if root is None:
                    from svk_corpus.config import find_repo_root
                    app_root = find_repo_root()
                else:
                    app_root = root
                state["service"] = AnswerService.from_repo(
                    app_root,
                    provider=provider,
                    logger=lambda msg: LOG.info("%s", msg),
                )
                LOG.info("[gen-api] service ready mode=%s model=%s",
                         state["service"].retrieval_mode,
                         state["service"].provider.model)
            except Exception as exc:                       # noqa: BLE001
                state["errors"].append(f"generation service init failed: {exc}")
                LOG.error("[gen-api] init failed: %s", exc)
        yield

    app = FastAPI(
        title="Sthānakavāsī generation MVP (experimental)",
        description=(
            "Isolated evidence-grounded generation component. NOT the "
            "production retrieval API; loopback only."
        ),
        version="0.1.0-experimental",
        lifespan=lifespan,
    )

    @app.exception_handler(ServiceUnavailable)
    async def _svc_unavailable(request: Request, exc: ServiceUnavailable):
        return JSONResponse(status_code=503,
                            content={"detail": "generation service unavailable",
                                     "errors": exc.errors})

    @app.middleware("http")
    async def _body_limit(request: Request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
            return JSONResponse(status_code=413,
                                content={"detail": "request body too large"})
        return await call_next(request)

    @app.get("/health", response_model=GenerationHealthResponseModel)
    async def health() -> GenerationHealthResponseModel:
        svc: AnswerService | None = state["service"]
        errors: list[str] = list(state["errors"])
        if svc is None:
            return GenerationHealthResponseModel(
                status="error", component="generation-mvp",
                retrieval_mode="", evidence_k=0, model="", endpoint="",
                ollama={"reachable": False, "model_present": False},
                errors=errors or ["service not initialized"],
            )
        h = svc.health()
        status = "ok" if h["status"] == "ok" and not errors else "degraded"
        return GenerationHealthResponseModel(
            status=status, component="generation-mvp",
            retrieval_mode=h["retrieval_mode"], evidence_k=h["evidence_k"],
            model=h["model"], endpoint=h["endpoint"], ollama=h["ollama"],
            errors=errors,
        )

    @app.post("/answer", response_model=AnswerResponseModel)
    async def answer(req: AnswerRequest, request: Request) -> AnswerResponseModel:
        svc: AnswerService | None = state["service"]
        if svc is None or state["errors"]:
            raise ServiceUnavailable(state["errors"])

        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        t0 = time.perf_counter()
        try:
            res = svc.answer(req.question)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        payload = res.to_dict()
        payload["request_id"] = rid
        LOG.info(
            "[gen-api] request_id=%s q_fp=%s q_len=%d mode=%s abstained=%s "
            "citations=%d error=%s wall_s=%.3f",
            rid, _query_fingerprint(req.question), len(req.question),
            payload["retrieval_mode"], payload["abstained"],
            len(payload["citations"]), payload["error"] or "-",
            time.perf_counter() - t0,
        )
        return AnswerResponseModel(**payload)

    return app


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="svk-generation-mvp",
        description="Run the EXPERIMENTAL generation app on loopback:8101.",
    )
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help=f"bind address (default {DEFAULT_HOST}; keep loopback)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"port (default {DEFAULT_PORT})")
    parser.add_argument("--log-level", default="info",
                        choices=["critical", "error", "warning", "info", "debug"])
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "uvicorn is required (install into .venv; see docs/generation_mvp.md)"
        ) from exc

    app = create_generation_app()
    uvicorn.run(app, host=args.host, port=args.port,
                log_level=args.log_level, access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
