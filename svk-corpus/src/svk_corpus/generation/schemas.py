"""Pydantic schemas for the experimental generation HTTP app (Task 89).

Thin projection of ``AnswerResult`` (``svk_corpus.generation.answer``); no
invented fields.  Requires ``pydantic`` v2 (repo ``.venv``; the stdlib
pipeline never imports this module).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

QUESTION_MAX_LENGTH = 2000      # mirrors the retrieval API bound


class AnswerRequest(BaseModel):
    """POST /answer request body."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"question": "How is ahimsa defined by Farquhar?"}]
        },
    )

    question: str = Field(
        ...,
        min_length=1,
        max_length=QUESTION_MAX_LENGTH,
        description=(f"Non-empty question, at most {QUESTION_MAX_LENGTH} "
                     "characters. Whitespace-only input is rejected."),
    )

    @field_validator("question")
    @classmethod
    def _reject_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must contain non-whitespace characters")
        return v


class EvidenceModel(BaseModel):
    """One retrieved passage with full provenance (citability contract)."""

    evidence_id: str
    text_id: str
    source_id: str
    title: str
    text: str
    citation: str
    score: float
    rank: int
    channel: str
    sect: str = ""
    religious_scope: str = ""
    knowledge_layer: str = ""
    teacher_or_author: str = ""


class AnswerResponseModel(BaseModel):
    """POST /answer response: cited answer or explicit abstention."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    question: str
    answer: str
    abstained: bool
    abstention_reason: str
    citations: list[str]
    invalid_citations: list[str]
    citations_valid: bool
    citation_map: dict[str, dict[str, str]]
    evidence: list[EvidenceModel]
    model: str
    retrieval_mode: str
    retrieval_latency_s: float
    generation_latency_s: float
    total_latency_s: float
    eval_count: int | None = None
    error: str = ""
    warnings: list[str] = Field(default_factory=list)


class GenerationHealthResponseModel(BaseModel):
    """GET /health for the experimental generation app."""

    model_config = ConfigDict(extra="forbid")

    status: str                    # ok | degraded | error
    component: str                 # always "generation-mvp"
    retrieval_mode: str
    evidence_k: int
    model: str
    endpoint: str
    ollama: dict[str, Any]
    errors: list[str] = Field(default_factory=list)
