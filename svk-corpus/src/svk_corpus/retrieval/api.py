"""Retrieval-only FastAPI application (Task 85).

Wraps the existing ``RetrievalService`` (``svk_corpus.retrieval.service``)
behind two endpoints:

    GET  /health   operational status of the retrieval stack
    POST /search   ranked evidence with provenance (NO generation)

Design constraints (Task 85):
  * Production default stays ``bm25``; ``hybrid_rrf20`` is opt-in via
    policy/env and never enabled by this module.
  * No model downloads, no dense-index rebuilds, no answer generation.
  * Dense index is loaded by ``RetrievalService.from_repo`` only when the
    configured mode is hybrid; BM25 mode never touches it.
  * Logs request summaries WITHOUT full query text.
  * Binds to 127.0.0.1 by default; the caller must opt into any other bind.

Requires ``fastapi`` + ``pydantic`` v2 (repo ``.venv``); the stdlib pipeline
never imports this module.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from svk_corpus.config import load_config
from svk_corpus.retrieval.schemas import (HealthResponseModel, ResultModel,
                                          SearchRequest, SearchResponseModel,
                                          MetadataMatchModel)
from svk_corpus.retrieval.service import (DenseIndexUnavailable, RetrievalMode,
                                          RetrievalPolicy, RetrievalService,
                                          ServiceResult, SearchResponse)

LOG = logging.getLogger("svk_corpus.retrieval.api")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8100          # 8000 = FanPulse orchestrator; 11434 = Ollama
MAX_BODY_BYTES = 64 * 1024   # request payload ceiling (query + top_k only)


class ServiceUnavailable(Exception):
    """Raised when the retrieval service failed to initialize."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = list(errors)
        super().__init__("retrieval service unavailable")


# ---------------------------------------------------------------------------
# Policy + service initialization
# ---------------------------------------------------------------------------

def load_retrieval_policy(root: Path) -> RetrievalPolicy:
    """Load the retrieval policy from configs/policy.toml + SVK_RETRIEVAL_* env.

    Mirrors the established configuration mechanism: the TOML ``[retrieval]``
    section is authoritative, environment variables are runtime feature flags
    (invalid ``SVK_RETRIEVAL_MODE`` values are ignored, never silently applied).
    """
    cfg = load_config(root)
    policy = RetrievalPolicy.from_toml_section(cfg.section("retrieval"))
    return policy.with_env_overrides(os.environ)


def _summary_logger():
    """Logger that records request shape, never full query text."""

    def log(msg: str) -> None:
        LOG.info("%s", msg)

    return log


def _query_fingerprint(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()[:12]


def _result_to_model(r: ServiceResult) -> ResultModel:
    mm = None
    if r.metadata_match is not None:
        mm = MetadataMatchModel(**r.metadata_match.__dict__)
    return ResultModel(
        rank=r.rank,
        channel=r.channel,
        score=float(r.score),
        text_id=r.doc.text_id,
        source_id=r.doc.source_id,
        title=r.doc.title,
        text=r.doc.text,
        parent_source_id=r.doc.parent_source_id,
        locator=dict(r.doc.locator or {}),
        religious_scope=r.doc.religious_scope,
        religious_scope_confidence=r.doc.religious_scope_confidence,
        knowledge_layer=r.doc.knowledge_layer,
        teacher_or_author=r.doc.teacher_or_author,
        lineage=r.doc.lineage,
        source_quality=r.doc.source_quality,
        methods=dict(r.methods or {}),
        unit_bm25_rank=r.unit_bm25_rank,
        unit_bm25_score=r.unit_bm25_score,
        dense_rank=r.dense_rank,
        dense_score=r.dense_score,
        metadata_match=mm,
    )


def _search_to_model(resp: SearchResponse, request_id: str) -> SearchResponseModel:
    return SearchResponseModel(
        request_id=request_id,
        mode_requested=resp.mode_requested.value,
        mode_used=resp.mode_used.value,
        fallback_reason=resp.fallback_reason,
        latency_s=round(resp.latency_s, 6),
        top_k=resp.top_k,
        n_results=len(resp.results),
        results=[_result_to_model(r) for r in resp.results],
    )


def _health_state(policy: RetrievalPolicy, service: RetrievalService | None,
                  init_errors: list[str]) -> HealthResponseModel:
    if service is None or init_errors:
        return HealthResponseModel(
            status="error",
            mode_configured=policy.mode.value,
            mode_default=RetrievalMode.BM25.value,
            corpus_loaded=False,
            n_documents=0,
            dense_available=False,
            query_encoder_available=False,
            bm25_fallback_active=False,
            strict_dense=policy.strict_dense,
            fallback_on_dense_failure=policy.fallback_on_dense_failure,
            initialization_errors=list(init_errors),
        )

    stats = service.dense_stats()
    dense_ok = bool(stats.get("loaded"))
    encoder_ok = bool(stats.get("query_encoder_available"))
    hybrid = policy.mode is RetrievalMode.HYBRID_RRF20

    if hybrid and not dense_ok and policy.strict_dense:
        status = "error"
        fallback_active = False
    elif hybrid and (not dense_ok or not encoder_ok) and policy.fallback_on_dense_failure:
        status = "degraded"
        fallback_active = True
    elif hybrid and dense_ok and encoder_ok:
        status = "ok"
        fallback_active = False
    else:
        # bm25 production default: dense/encoder not required.
        status = "ok"
        fallback_active = False

    return HealthResponseModel(
        status=status,
        mode_configured=policy.mode.value,
        mode_default=RetrievalMode.BM25.value,
        corpus_loaded=True,
        n_documents=len(service.docs),
        dense_available=dense_ok,
        query_encoder_available=encoder_ok,
        bm25_fallback_active=fallback_active,
        strict_dense=policy.strict_dense,
        fallback_on_dense_failure=policy.fallback_on_dense_failure,
        initialization_errors=[],
    )


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(
    root: Path | None = None,
    policy: RetrievalPolicy | None = None,
    service: RetrievalService | None = None,
    init_errors: list[str] | None = None,
):
    """Build the FastAPI app.

    Parameters
    ----------
    root : Path, optional
        Repo root; defaults to ``svk_corpus.config.find_repo_root()``.
        Used to load ``configs/policy.toml`` and to wire
        ``RetrievalService.from_repo`` when ``service`` is not injected.
    policy : RetrievalPolicy, optional
        Pre-built policy (tests).  When omitted, loaded from policy.toml + env.
    service : RetrievalService, optional
        Pre-built service (tests).  When omitted, built via ``from_repo`` at
        startup — corpus + BM25 index are loaded once; dense is loaded only
        for hybrid mode.
    init_errors : list[str], optional
        Pre-populated initialization errors (tests).  A non-empty list forces
        ``status="error"`` on /health and 503 on /search.
    """
    root = Path(root) if root is not None else None
    errors: list[str] = list(init_errors or [])

    if policy is None:
        if root is None:
            from svk_corpus.config import find_repo_root
            root = find_repo_root()
        try:
            policy = load_retrieval_policy(root)
        except Exception as exc:
            errors.append(f"policy load failed: {exc}")
            policy = RetrievalPolicy()  # safe bm25 default for /health

    state: dict[str, Any] = {"service": service, "policy": policy, "errors": errors}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if state["service"] is None and not state["errors"]:
            try:
                if root is None:
                    from svk_corpus.config import find_repo_root
                    state_root = find_repo_root()
                else:
                    state_root = root
                state["service"] = RetrievalService.from_repo(
                    policy=state["policy"],
                    root=state_root,
                    dense=None,
                    query_encoder=None,   # never auto-load BGE-M3 at startup
                    logger=_summary_logger(),
                )
                LOG.info(
                    "[api] initialized mode=%s n_docs=%d dense=%s",
                    state["policy"].mode.value,
                    len(state["service"].docs),
                    state["service"].dense is not None,
                )
            except Exception as exc:
                state["errors"].append(f"service init failed: {exc}")
                LOG.error("[api] service init failed: %s", exc)
        yield
        # no background jobs; nothing to tear down beyond the ASGI server

    app = FastAPI(
        title="svk-corpus retrieval API",
        description=(
            "Retrieval-only evidence service over the Sthanakavasi Jain RAG "
            "corpus. Returns ranked passages with provenance. Does NOT "
            "generate answers and does NOT run any language model."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.exception_handler(ServiceUnavailable)
    async def _handle_unavailable(request: Request, exc: ServiceUnavailable):
        return JSONResponse(
            status_code=503,
            content={"detail": "retrieval service unavailable",
                     "initialization_errors": exc.errors},
        )

    @app.exception_handler(DenseIndexUnavailable)
    async def _handle_dense_unavailable(request: Request,
                                        exc: DenseIndexUnavailable):
        # strict_dense=True and hybrid artifacts missing: fail closed with an
        # explicit reason; never silently substitute BM25 results.
        return JSONResponse(
            status_code=503,
            content={"detail": "dense retrieval unavailable (strict_dense)",
                     "reason": str(exc)},
        )

    # ---- payload ceiling --------------------------------------------------
    @app.middleware("http")
    async def _body_limit(request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > MAX_BODY_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": f"request body exceeds {MAX_BODY_BYTES} bytes"},
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400, content={"detail": "invalid content-length"}
                )
        return await call_next(request)

    # ---- endpoints --------------------------------------------------------
    @app.get("/health", response_model=HealthResponseModel)
    async def health() -> HealthResponseModel:
        return _health_state(state["policy"], state["service"], state["errors"])

    @app.post("/search", response_model=SearchResponseModel)
    async def search(req: SearchRequest, request: Request) -> SearchResponseModel:
        svc: RetrievalService | None = state["service"]
        if svc is None or state["errors"]:
            raise ServiceUnavailable(state["errors"])

        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        t0 = time.perf_counter()
        try:
            resp = svc.search(req.query, top_k=req.top_k)
        except Exception as exc:
            LOG.error(
                "[api] request_id=%s search failed mode=%s: %s",
                rid, state["policy"].mode.value, exc,
            )
            raise
        model = _search_to_model(resp, rid)
        # Structured log: request shape only — never the raw query text.
        LOG.info(
            "[api] request_id=%s q_fp=%s q_len=%d top_k=%d mode_req=%s "
            "mode_used=%s fallback=%s n_results=%d wall_s=%.4f",
            rid, _query_fingerprint(req.query), len(req.query), req.top_k,
            model.mode_requested, model.mode_used, model.fallback_reason,
            model.n_results, time.perf_counter() - t0,
        )
        return model

    return app


# ---------------------------------------------------------------------------
# Entry point:  python -m svk_corpus.retrieval.api
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="svk-retrieval-api",
        description="Run the retrieval-only HTTP API on loopback.",
    )
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help=f"bind address (default {DEFAULT_HOST}; keep "
                             "loopback unless you know what you are doing)")
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
            "uvicorn is required to serve the API (install into .venv; "
            "see docs/retrieval_api.md)"
        ) from exc

    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port,
                log_level=args.log_level, access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
