"""Shared extraction result type."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExtractionResult:
    text: str
    pages: list[str]
    method: str
    status: str                      # OK | EMPTY | FAILED | UNSUPPORTED_FORMAT | UNAVAILABLE_NO_BACKEND
    error: str = ""
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    # Round 2: parallel to `pages` when the source carries separable text
    # layers (e.g. a parallel corpus). Empty for single-layer sources, so
    # every v0.1 call site keeps its behaviour unchanged.
    text_roles: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == "OK" and bool(self.text.strip())

    @property
    def characters(self) -> int:
        return len(self.text)

    @property
    def page_count(self) -> int:
        return len(self.pages)
