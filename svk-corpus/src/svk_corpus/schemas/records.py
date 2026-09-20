"""Core data model and manifest schemas.

Every field name here is contract: writers, readers and validators all import
these tuples so that the manifest cannot silently drift.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# SOURCE MANIFEST
#
# The first 28 fields are the field list requested for this milestone, in order.
# Fields after the marker are extensions the pipeline needs in order to keep the
# licence gate deterministic and the provenance auditable.
# ---------------------------------------------------------------------------
SOURCE_MANIFEST_FIELDS: tuple[str, ...] = (
    # --- requested field set -------------------------------------------------
    "source_id",
    "title",
    "author",
    "publisher",
    "publication_year",
    "tradition",
    "sect",
    "subsect",
    "language",
    "script",
    "source_url",
    "download_url",
    "repository",
    "source_format",
    "license",
    "license_evidence_url",
    "copyright_basis",
    "training_permission",
    "redistribution_permission",
    "commercial_permission",
    "license_confidence",
    "source_status",
    "acquisition_status",
    "ocr_required",
    "translation_status",
    "commentary_status",
    # --- Round 2: language metadata layer -----------------------------------
    # Precision is never fabricated: language_variant stays "unknown" unless a
    # source states it, and classification_basis records WHAT the label rests on.
    "language_family",
    "language_variant",
    "language_confidence",
    "classification_basis",
    "transliteration_system",
    # --- Round 2: explicit sect attribution ---------------------------------
    "sect_confidence",
    "sect_basis",
    # --- Round 2: source relationships --------------------------------------
    "relation_type",
    "parent_source_id",
    # --- Round 2: religious-scope audit layer --------------------------------
    # Kept strictly separate from the licence decision: religious_scope says what
    # a source IS, training_permission says what we may DO with it.
    "religious_scope",
    "religious_scope_confidence",
    "religious_scope_basis",
    "knowledge_layer",
    "teacher_or_author",
    "lineage",
    "provenance",
    "notes",
    # --- extensions ----------------------------------------------------------
    "text_name",
    "text_category",
    "author_death_year",
    "uploader_asserted",
    "ia_rights_statement",
    "verification_required",
    "curation_status",
    "acquisition_repository",
    "acquisition_identifier",
    "approx_token_count",
    "human_verified",
    "source_quality",
    "provenance_quality",
    "duplicate_risk",
    "sectarian_confidence",
    "recommended_use",
)

ARTIFACT_MANIFEST_FIELDS: tuple[str, ...] = (
    "artifact_id",
    "source_id",
    "artifact_type",
    "filename",
    "sha256",
    "bytes",
    "mime_type",
    "download_timestamp",
    "extraction_method",
    "ocr_method",
    "normalization_version",
    "source_url",
    "status",
    "error",
)

LICENSE_MANIFEST_FIELDS: tuple[str, ...] = (
    "source_id",
    "decision",
    "rule_id",
    "reason",
    "evidence",
    "confidence",
    "requirements",
    "requirements_met",
    "noncommercial",
    "sharealike",
    "verification_required",
    "evaluated_at",
)


class GateState(str, Enum):
    TRAINING_ALLOWED = "TRAINING_ALLOWED"
    RAG_ALLOWED = "RAG_ALLOWED"
    WITH_CONDITIONS = "WITH_CONDITIONS"
    NEEDS_PERMISSION = "NEEDS_PERMISSION"
    NOT_ALLOWED = "NOT_ALLOWED"
    UNKNOWN = "UNKNOWN"


@dataclass
class GateDecision:
    source_id: str
    state: GateState
    rule_id: str
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)
    confidence: str = "low"
    requirements: list[str] = field(default_factory=list)
    requirements_met: bool = False
    noncommercial: bool = False
    sharealike: bool = False
    verification_required: bool = False
    evaluated_at: str = ""

    def to_row(self) -> dict[str, str]:
        return {
            "source_id": self.source_id,
            "decision": self.state.value,
            "rule_id": self.rule_id,
            "reason": self.reason,
            "evidence": json.dumps(self.evidence, ensure_ascii=False, sort_keys=True),
            "confidence": self.confidence,
            "requirements": json.dumps(self.requirements, ensure_ascii=False),
            "requirements_met": str(self.requirements_met).lower(),
            "noncommercial": str(self.noncommercial).lower(),
            "sharealike": str(self.sharealike).lower(),
            "verification_required": str(self.verification_required).lower(),
            "evaluated_at": self.evaluated_at,
        }

    @property
    def releasable(self) -> bool:
        """Whether this decision permits inclusion in ANY released corpus."""
        if self.state in (GateState.NEEDS_PERMISSION, GateState.NOT_ALLOWED, GateState.UNKNOWN):
            return False
        if self.state is GateState.WITH_CONDITIONS:
            return self.requirements_met
        return True


@dataclass
class SourceRecord:
    values: dict[str, str]

    @property
    def source_id(self) -> str:
        return self.values.get("source_id", "")

    def __getitem__(self, key: str) -> str:
        return self.values.get(key, "")

    def get(self, key: str, default: str = "") -> str:
        return self.values.get(key) or default

    def as_row(self) -> dict[str, str]:
        return {k: self.values.get(k, "") for k in SOURCE_MANIFEST_FIELDS}


@dataclass
class ArtifactRecord:
    values: dict[str, str]

    @property
    def artifact_id(self) -> str:
        return self.values.get("artifact_id", "")

    def as_row(self) -> dict[str, str]:
        return {k: self.values.get(k, "") for k in ARTIFACT_MANIFEST_FIELDS}

    @staticmethod
    def new_id(source_id: str, artifact_type: str, sha256: str) -> str:
        digest = hashlib.sha256(f"{source_id}|{artifact_type}|{sha256}".encode()).hexdigest()
        return f"art_{digest[:16]}"


# ---------------------------------------------------------------------------
# TEXT UNITS
# ---------------------------------------------------------------------------
UNIT_TYPES = ("document", "section", "verse", "sutta", "paragraph", "sentence", "chunk")


@dataclass
class TextUnit:
    unit_id: str
    source_id: str
    parent_id: str
    unit_type: str
    text: str
    normalized_text: str
    language: str
    script: str
    page: int | None
    section: str | None
    source_locator: dict[str, Any]
    text_role: str
    structure_confidence: str
    detected_label: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# ---------------------------------------------------------------------------
# RELEASE RECORD CONTRACT
# ---------------------------------------------------------------------------
RELEASE_REQUIRED_FIELDS: tuple[str, ...] = (
    "id",
    "source_id",
    "text",
    "normalized_text",
    "text_role",
    "language",
    "script",
    "unit_type",
    "source_locator",
    "provenance",
    "license",
    "quality",
    "pipeline_version",
)


class SchemaError(ValueError):
    pass


def validate_release_record(record: dict[str, Any]) -> list[str]:
    """Return a list of validation problems. Empty list means valid.

    Deliberately strict: a record without provenance or without a licence block
    must never reach a release file.
    """
    problems: list[str] = []
    for name in RELEASE_REQUIRED_FIELDS:
        if name not in record:
            problems.append(f"missing field: {name}")
    if problems:
        return problems

    if not isinstance(record["provenance"], dict):
        problems.append("provenance must be an object")
    else:
        prov = record["provenance"]
        for key in ("source_url", "artifact_sha256", "repository"):
            if not prov.get(key):
                problems.append(f"provenance.{key} is empty")
    if not isinstance(record["license"], dict):
        problems.append("license must be an object")
    else:
        if not record["license"].get("status"):
            problems.append("license.status is empty")
        if not record["license"].get("evidence"):
            problems.append("license.evidence is empty")
    if record["text_role"] not in ("ORIGINAL", "TRANSCRIPTION", "TRANSLATION",
                                   "COMMENTARY", "ANNOTATION", "OCR", "AI_GENERATED"):
        problems.append(f"unknown text_role: {record['text_role']}")
    if not isinstance(record["source_locator"], dict):
        problems.append("source_locator must be an object")
    if not record["text"] and not record["normalized_text"]:
        problems.append("record has no text and no normalized_text")
    return problems


def dedupe_preserving_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
