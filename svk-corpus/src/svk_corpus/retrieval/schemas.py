"""Pydantic request/response schemas for the retrieval-only HTTP API (Task 85).

These schemas are a thin, explicit projection of the existing
``RetrievalService`` interface (``svk_corpus.retrieval.service``).  They do
NOT invent fields: every response field maps 1:1 onto a ``ServiceResult`` /
``SearchResponse`` / ``CanonicalResult`` attribute or an operational status
computed from ``RetrievalPolicy`` + ``DenseIndexState``.

Requires ``pydantic`` v2 (installed in the repo ``.venv``; the stdlib pipeline
never imports this module).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Documented bounds — enforced by the schema, surfaced in the OpenAPI docs.
QUERY_MAX_LENGTH = 2000
TOP_K_DEFAULT = 10
TOP_K_MAX = 50
TOP_K_MIN = 1


class SearchRequest(BaseModel):
    """POST /search request body."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "query": "When was the Terapanth founded?",
                    "top_k": 5,
                }
            ]
        },
    )

    query: str = Field(
        ...,
        min_length=1,
        max_length=QUERY_MAX_LENGTH,
        description=(
            f"Non-empty search query, at most {QUERY_MAX_LENGTH} characters. "
            "Whitespace-only input is rejected."
        ),
    )
    top_k: int = Field(
        default=TOP_K_DEFAULT,
        ge=TOP_K_MIN,
        le=TOP_K_MAX,
        description=(
            f"Number of results to return ({TOP_K_MIN}..{TOP_K_MAX}). "
            f"Defaults to {TOP_K_DEFAULT}."
        ),
    )

    @field_validator("query")
    @classmethod
    def _reject_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query must contain non-whitespace characters")
        return v


class MetadataMatchModel(BaseModel):
    """Source-metadata match evidence (present only on source_metadata channels)."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    matched_field: str
    matched_value: str
    matched_token: str
    weight: float
    via_family: bool = False
    family_root: str = ""


class ResultModel(BaseModel):
    """One ranked retrieval result.

    Fields mirror ``ServiceResult`` + the corresponding ``CanonicalResult``
    provenance attributes.  ``text`` is the corpus unit text returned by the
    retrieval service; the API does not truncate or rewrite it.
    """

    model_config = ConfigDict(extra="forbid")

    rank: int
    channel: str
    score: float
    text_id: str
    source_id: str
    title: str
    text: str
    parent_source_id: str = ""
    locator: dict[str, Any] = Field(default_factory=dict)
    religious_scope: str = "UNKNOWN"
    religious_scope_confidence: str = "UNKNOWN"
    knowledge_layer: str = ""
    teacher_or_author: str = ""
    lineage: str = ""
    source_quality: str = ""
    methods: dict[str, int] = Field(default_factory=dict)
    unit_bm25_rank: int | None = None
    unit_bm25_score: float | None = None
    dense_rank: int | None = None
    dense_score: float | None = None
    metadata_match: MetadataMatchModel | None = None


class SearchResponseModel(BaseModel):
    """POST /search response body."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    mode_requested: str
    mode_used: str
    fallback_reason: str | None = None
    latency_s: float
    top_k: int
    n_results: int
    results: list[ResultModel]


class HealthResponseModel(BaseModel):
    """GET /health response body.

    Reports only operational status derived from the loaded
    ``RetrievalPolicy`` / ``DenseIndexState``.  Never includes credentials,
    environment variables, or filesystem paths outside the repo-relative
    policy values.
    """

    model_config = ConfigDict(extra="forbid")

    status: str = Field(
        description="'ok' when the service can answer searches; "
                    "'degraded' when initialized but a configured fallback is "
                    "active; 'error' when initialization failed."
    )
    service: str = "svk-corpus-retrieval"
    mode_configured: str = Field(description="Mode from policy/env actually loaded.")
    mode_default: str = Field(description="Frozen production default (always 'bm25').")
    corpus_loaded: bool
    n_documents: int
    dense_available: bool
    query_encoder_available: bool
    bm25_fallback_active: bool = Field(
        description="True when hybrid was configured but will fall back to "
                    "BM25 because dense/encoder is unavailable and "
                    "fallback_on_dense_failure is enabled."
    )
    strict_dense: bool
    fallback_on_dense_failure: bool
    initialization_errors: list[str] = Field(default_factory=list)
