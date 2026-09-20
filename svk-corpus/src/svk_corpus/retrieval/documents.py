"""Corpus loading for retrieval evaluation.

Provenance contract
-------------------
Every RetrievalDocument carries the provenance the project already publishes
per release record, plus the source-level religious-scope fields joined from
`manifests/source_manifest.csv` (the audit layer produced by the Task-3
classification). Retrieval must never drop these: a result without provenance
is exactly the failure mode this project exists to prevent.

Nothing here rewrites or filters the corpus: what the release contains is what
retrieval searches.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator


@dataclass
class RetrievalDocument:
    """One released unit with its provenance intact."""

    text_id: str
    source_id: str
    title: str
    text: str
    language: str
    script: str
    sect: str
    religious_scope: str
    religious_scope_confidence: str
    knowledge_layer: str
    teacher_or_author: str
    lineage: str
    unit_type: str
    section: str
    locator: dict[str, Any] = field(default_factory=dict)
    publication_year: str = ""
    author: str = ""
    parent_source_id: str = ""   # edition_of parent (source manifest)
    source_quality: str = ""     # artifact/OCR fidelity from the manifest

    @property
    def search_text(self) -> str:
        """Field-weighted searchable text for lexical retrieval.

        Units are small slices of a work, so a unit's body often never contains
        the work's title or author — yet those are exactly what users query.
        Indexing provenance fields alongside the body is standard document
        retrieval practice (field boosting); it changes nothing about what the
        corpus contains or how provenance is reported.
        """
        parts = [self.title, self.title, self.title, self.author, self.section, self.text]
        return " ".join(p for p in parts if p)

    @property
    def citation(self) -> str:
        loc = self.locator or {}
        page = loc.get("page")
        base = f"{self.title} ({self.publication_year})" if self.publication_year else self.title
        out = f"{base} [{self.source_id}]"
        if self.section:
            out += f", section: {self.section}"
        if page:
            out += f", page: {page}"
        return out


def load_source_scope(manifest_path: Path) -> dict[str, dict[str, str]]:
    """Read the source manifest's audit fields, keyed by source_id."""
    scope: dict[str, dict[str, str]] = {}
    with open(manifest_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            scope[row.get("source_id", "")] = {
                "religious_scope": row.get("religious_scope", "UNKNOWN"),
                "religious_scope_confidence": row.get("religious_scope_confidence", "UNKNOWN"),
                "knowledge_layer": row.get("knowledge_layer", ""),
                "teacher_or_author": row.get("teacher_or_author", ""),
                "lineage": row.get("lineage", ""),
                "title": row.get("title", ""),
                "author": row.get("author", ""),
                "publication_year": row.get("publication_year", ""),
                "parent_source_id": row.get("parent_source_id", ""),
                "source_quality": row.get("source_quality", ""),
            }
    return scope


def iter_release_documents(rag_jsonl: Path,
                           scope: dict[str, dict[str, str]] | None = None) -> Iterator[RetrievalDocument]:
    """Stream release records into RetrievalDocuments (memory-lean)."""
    scope = scope or {}
    with open(rag_jsonl, encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            src = scope.get(rec.get("source_id", ""), {})
            yield RetrievalDocument(
                text_id=str(rec.get("id") or f"line{line_number}"),
                source_id=rec.get("source_id", ""),
                title=src.get("title") or rec.get("title", ""),
                text=rec.get("normalized_text") or rec.get("text") or "",
                language=rec.get("language", "unknown"),
                script=rec.get("script", "unknown"),
                sect=rec.get("sect", "unknown"),
                religious_scope=src.get("religious_scope", "UNKNOWN"),
                religious_scope_confidence=src.get("religious_scope_confidence", "UNKNOWN"),
                knowledge_layer=src.get("knowledge_layer", ""),
                teacher_or_author=src.get("teacher_or_author", ""),
                lineage=src.get("lineage", ""),
                unit_type=rec.get("unit_type", ""),
                section=str(rec.get("section") or ""),
                locator=rec.get("source_locator") if isinstance(rec.get("source_locator"), dict) else {},
                publication_year=src.get("publication_year", "") or str(rec.get("publication_year") or ""),
                author=src.get("author") or rec.get("author", ""),
                parent_source_id=src.get("parent_source_id", ""),
                source_quality=src.get("source_quality", ""),
            )


def load_corpus(rag_jsonl: Path, manifest_path: Path) -> list[RetrievalDocument]:
    """Materialise the full RAG corpus (145k units fit comfortably)."""
    scope = load_source_scope(manifest_path)
    return list(iter_release_documents(rag_jsonl, scope))
