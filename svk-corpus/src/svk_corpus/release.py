"""Release writing: two products, one provenance contract.

TWO PRODUCTS, ON PURPOSE
    rag_corpus.jsonl      retrieval-eligible text, optimised for citation
    training_corpus.jsonl text that may update model weights
A source can be good enough to retrieve from and not good enough to train on
(ShareAlike, or unverified OCR of a PD work). Collapsing the two into one file
would lose that distinction exactly where it matters legally, so they stay
separate and both carry the same provenance block.

WHAT IS DELIBERATELY ABSENT FROM EVERY RECORD
No verse numbers we did not read, no chapter names we did not see, no author we
could not verify, no language we did not detect. Unknown values are written as
null or "unknown". A field invented here would be indistinguishable downstream
from a field read out of a catalogue, and this corpus exists to make that
difference auditable.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from svk_corpus.schemas.records import GateState, SourceRecord, validate_release_record

RAG_FILENAME = "rag_corpus.jsonl"
TRAINING_FILENAME = "training_corpus.jsonl"
EXCLUDED_FILENAME = "excluded_sources.jsonl"
RELEASE_MANIFEST = "manifest.json"


@dataclass
class ReleaseStats:
    written: int = 0
    skipped_validation: int = 0
    skipped_empty: int = 0
    skipped_duplicate: int = 0
    bytes: int = 0
    sha256: str = ""


def _or_unknown(value: Any) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.lower() in ("unknown", "n/a", "none", "unmeasured", "unverified"):
        return "unknown"
    return text


def build_citation(source: SourceRecord, locator: dict[str, Any]) -> str:
    """A human-checkable citation. Composed only from recorded fields."""
    parts: list[str] = []
    title = _or_unknown(source.get("title"))
    if title and title != "unknown":
        parts.append(str(title))
    year = _or_unknown(source.get("publication_year"))
    if year and year != "unknown":
        parts.append(f"({year})")
    page = locator.get("page")
    if page:
        parts.append(f"p. {page}")
    section = locator.get("section")
    if section:
        parts.append(f"section: {section}")
    parts.append(f"[{source.source_id}]")
    return ", ".join(parts)


def build_record(
    unit,
    source: SourceRecord,
    gate,
    *,
    artifact_sha256: str = "",
    acquisition_timestamp: str = "",
    pipeline_version: str = "0.1.0",
) -> dict[str, Any]:
    locator = dict(unit.source_locator or {})
    locator.setdefault("page", unit.page)
    locator.setdefault("section", unit.section)
    locator["citation"] = build_citation(source, locator)

    provenance = {
        "source_url": source.get("source_url"),
        "artifact_sha256": artifact_sha256 or None,
        "repository": source.get("repository") or source.get("acquisition_repository"),
        "identifier": source.get("acquisition_identifier") or None,
        "license_evidence_url": source.get("license_evidence_url") or None,
        "acquisition_timestamp": acquisition_timestamp or None,
        "manifest_origin": _manifest_origin(source),
    }

    license_block = {
        "status": gate.state.value,
        "rule_id": gate.rule_id,
        # The full human-readable gate reasoning is written ONCE per source into
        # manifests/license_manifest.csv, addressed by rule_id. Inlining it here
        # would repeat a ~250-byte sentence in every one of ~30k records per
        # product, which grew the release to 236 MB with metadata as 99% of the
        # bytes while saying nothing new. The full text is never discarded; it is
        # stored once at source level.
        "evidence": f"{gate.rule_id} ({gate.confidence}); full reasoning in "
                    f"manifests/license_manifest.csv for source {source.source_id}",
        "confidence": gate.confidence,
        "basis": _or_unknown(source.get("copyright_basis")),
        "license": _or_unknown(source.get("license")),
        "redistribute": _yes_no(source.get("redistribution_permission")),
        "commercial": _yes_no(source.get("commercial_permission")),
        "sharealike": bool(gate.sharealike),
        "noncommercial": bool(gate.noncommercial),
        "verification_required": bool(gate.verification_required),
    }

    quality = dict(unit.quality or {})
    quality["structure_confidence"] = unit.structure_confidence
    quality["ocr_required"] = str(source.get("ocr_required", "")).strip().lower() == "true"

    return {
        "id": unit.unit_id,
        "source_id": unit.source_id,
        "text": unit.text,
        "normalized_text": unit.normalized_text,
        "text_role": unit.text_role,
        "language": _or_unknown(unit.language) or "unknown",
        "script": _or_unknown(unit.script) or "unknown",
        "unit_type": unit.unit_type,
        "parent_id": unit.parent_id or None,
        "document_id": f"{unit.source_id}:doc",
        "section": unit.section,
        "tradition": _or_unknown(source.get("tradition")),
        "sect": _or_unknown(source.get("sect")),
        "subsect": _or_unknown(source.get("subsect")),
        "publication_year": _or_unknown(source.get("publication_year")),
        "author": _or_unknown(source.get("author")),
        "title": _or_unknown(source.get("title")),
        # --- Round 2: language metadata, sect attribution, source relations ---
        # Empty manifest cells collapse to "unknown"; nothing is inferred here.
        "language_family": _or_unknown(source.get("language_family")),
        "language_variant": _or_unknown(source.get("language_variant")),
        "language_confidence": _or_unknown(source.get("language_confidence")),
        "classification_basis": _or_unknown(source.get("classification_basis")),
        "sect_confidence": _or_unknown(source.get("sect_confidence")),
        "sect_basis": _or_unknown(source.get("sect_basis")),
        "relation_type": _or_unknown(source.get("relation_type")),
        "parent_source_id": _or_unknown(source.get("parent_source_id")),
        "source_locator": locator,
        "provenance": provenance,
        "license": license_block,
        "quality": quality,
        "pipeline_version": pipeline_version,
    }


def _manifest_origin(source: SourceRecord) -> str:
    raw = source.get("provenance", "")
    if not raw:
        return "unknown"
    try:
        return json.loads(raw).get("manifest_origin", "unknown")
    except json.JSONDecodeError:
        return "unknown"


def _yes_no(value: str) -> Any:
    text = str(value or "").strip().lower()
    if text in ("yes", "true", "allowed", "permitted", "conditional"):
        return text
    if text in ("no", "false", "not_allowed", "denied"):
        return "not_allowed"
    if not text or text in ("unknown", "unclear", "none"):
        return "unknown"
    return text


class JsonlWriter:
    """Streams records to JSONL, validating every one on the way out."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("w", encoding="utf-8", newline="\n")
        self._digest = hashlib.sha256()
        self.stats = ReleaseStats()
        self.problems: list[dict[str, Any]] = []

    def write(self, record: dict[str, Any]) -> bool:
        problems = validate_release_record(record)
        if problems:
            self.stats.skipped_validation += 1
            self.problems.append({"id": record.get("id", ""), "problems": problems})
            return False
        if not (record.get("normalized_text") or record.get("text") or "").strip():
            self.stats.skipped_empty += 1
            return False
        line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        self._fh.write(line + "\n")
        self._digest.update(line.encode("utf-8"))
        self.stats.written += 1
        return True

    def close(self) -> ReleaseStats:
        self._fh.close()
        self.stats.bytes = self.path.stat().st_size if self.path.is_file() else 0
        self.stats.sha256 = self._digest.hexdigest()
        return self.stats


def write_excluded(path: Path, excluded: Sequence[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for item in excluded:
            fh.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_release_manifest(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                    encoding="utf-8")
    return path


def count_records(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open("r", encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def iter_records(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)
