"""Knowledge architecture validators (Task 20).

Provides validation for:
- Jain Knowledge Ontology (traditions, layers, roles, practices, etc.)
- Agam Inventory entries
- Source Registry entries
- Knowledge Coverage Matrix entries

Key rule: availability on JainQQ or Jainebooks MUST NOT automatically
imply training permission. download_available=true does NOT imply
rights_status=CLEAR.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_KNOWLEDGE_DIR = Path(__file__).resolve().parents[3] / "data" / "knowledge"
_ONTOLOGY_PATH = _KNOWLEDGE_DIR / "jain_knowledge_ontology_v1.json"
_AGAM_PATH = _KNOWLEDGE_DIR / "agam_inventory_v1.json"
_REGISTRY_PATH = _KNOWLEDGE_DIR / "source_registry_v1.json"
_COVERAGE_PATH = _KNOWLEDGE_DIR / "knowledge_coverage_v1.json"

# ---------------------------------------------------------------------------
# Controlled vocabularies (loaded from ontology or hardcoded for validation)
# ---------------------------------------------------------------------------

TRADITIONS = {
    "STHANAKAVASI",
    "SVETAMBARA_GENERIC",
    "SVETAMBARA_MURTIPUJAKA",
    "TERAPANTHI",
    "DIGAMBARA",
    "MULTI_TRADITION",
    "UNKNOWN",
}

KNOWLEDGE_LAYERS = {
    "CANONICAL",
    "SUTRA",
    "COMMENTARY",
    "TEACHER_INTERPRETATION",
    "PRACTICE",
    "PHILOSOPHY",
    "HISTORY",
    "BIOGRAPHY",
    "PRAVACHAN",
    "LEXICON",
    "TRANSLATION",
    "EDUCATIONAL",
    "COMPARATIVE",
    "OTHER",
}

CONTENT_ROLES = {
    "PRIMARY_SCRIPTURE",
    "SCRIPTURE_TRANSLATION",
    "SCRIPTURE_EXPLANATION",
    "COMMENTARY",
    "TEACHING",
    "PRACTICE_GUIDANCE",
    "BIOGRAPHICAL",
    "HISTORICAL",
    "REFERENCE",
    "LEXICON",
    "COMPARATIVE",
    "OTHER",
}

PRACTICES = {
    "SAMAYIK",
    "PRATIKRAMAN",
    "KAYOTSARGA",
    "VANDANA",
    "PRATYAKHYAN",
    "CHAUVISANTHO",
    "AVASHYAKA",
    "PARYUSHAN",
    "OTHER",
}

CANONICAL_STATUSES = {
    "CANONICAL",
    "CANONICAL_TRANSLATION",
    "COMMENTARY_ON_CANON",
    "TRADITIONAL_TEXT",
    "NON_CANONICAL",
    "UNKNOWN",
}

RIGHTS_STATUSES = {
    "CLEAR",
    "PERMISSION_REQUIRED",
    "UNCLEAR",
    "RESTRICTED",
    "UNKNOWN",
}

VERIFICATION_STATUSES = {
    "VERIFIED",
    "PROVISIONAL",
    "CONTESTED",
    "UNKNOWN",
}

RELIGIOUS_SCOPES = {
    "CORE_STHANAKAVASI",
    "HIGH_STHANAKAVASI_RELEVANCE",
    "COMPARATIVE_OTHER_TRADITION",
    "CONTEXTUAL_JAIN",
    "UNKNOWN",
}

PLATFORMS = {
    "JAINQQ",
    "JAINEBOOKS",
    "INTERNET_ARCHIVE",
    "GITHUB",
    "GRETIL",
    "MANUAL_ACQUISITION",
    "OTHER",
}

AGAM_GROUPS = {
    "ANGA",
    "UPANGA",
    "MULASUTRA",
    "CHEDASUTRA",
    "PARISHISHTA",
    "PRATIYANUYOGA",
    "UNKNOWN",
}

COVERAGE_STATUSES = {
    "STRONG",
    "PARTIAL",
    "WEAK",
    "MISSING",
    "RIGHTS_BLOCKED",
    "NEEDS_RESEARCH",
}

COVERAGE_CATEGORIES = {
    "AGAMA",
    "PRACTICE",
    "PHILOSOPHY",
    "HISTORY",
    "BIOGRAPHY",
    "LEXICON",
    "CROSS_TRADITION",
    "MODERN",
    "LANGUAGE",
}

TRADITION_RELEVANCE = {
    "STHANAKAVASI_ONLY",
    "SVETAMBARA_WIDE",
    "ALL_JAIN",
    "UNKNOWN",
}

ENTITY_TYPES = {
    "AGAM",
    "SUTRA",
    "PRACTICE",
    "TEACHER",
    "ACHARYA",
    "MUNI",
    "SADHVI",
    "AUTHOR",
    "COMMENTATOR",
    "TRANSLATOR",
    "BOOK",
    "MAGAZINE",
    "PRAVACHAN",
    "CONCEPT",
    "TIRTHANKARA",
    "PLACE",
    "HISTORICAL_EVENT",
    "LINEAGE",
}

RELATIONSHIP_TYPES = {
    "SOURCE_CONTAINS",
    "SOURCE_TRANSLATES",
    "SOURCE_COMMENTARY_ON",
    "SOURCE_EXPLAINS",
    "TEACHER_AUTHORED",
    "TEACHER_COMMENTED",
    "TEACHER_TAUGHT",
    "PRACTICE_REFERENCED_BY",
    "AGAM_PART_OF_INVENTORY",
    "CONCEPT_EXPLAINED_BY",
    "SOURCE_BELONGS_TO_TRADITION",
}


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def load_ontology() -> dict[str, Any]:
    """Load the knowledge ontology."""
    return _load_json(_ONTOLOGY_PATH)


def load_agam_inventory() -> dict[str, Any]:
    """Load the Agam inventory."""
    return _load_json(_AGAM_PATH)


def load_source_registry() -> dict[str, Any]:
    """Load the source registry."""
    return _load_json(_REGISTRY_PATH)


def load_coverage_matrix() -> dict[str, Any]:
    """Load the knowledge coverage matrix."""
    return _load_json(_COVERAGE_PATH)


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------

def validate_agam_entry(entry: dict[str, Any]) -> list[str]:
    """Validate a single Agam inventory entry.

    Returns a list of violation descriptions (empty if valid).
    """
    violations: list[str] = []

    # Required fields
    for field in ["agam_id", "traditional_name", "group", "tradition",
                   "canonical_status", "language", "script",
                   "translation_available", "commentary_available",
                   "rights_status", "verification_status"]:
        if field not in entry:
            violations.append(f"missing required field: {field}")

    # agam_id format
    agam_id = entry.get("agam_id", "")
    if agam_id and not agam_id.startswith("AGAM-"):
        violations.append(f"agam_id must start with 'AGAM-': {agam_id!r}")

    # Enum checks
    group = entry.get("group", "")
    if group and group not in AGAM_GROUPS:
        violations.append(f"invalid group: {group!r}")

    tradition = entry.get("tradition", "")
    if tradition and tradition not in TRADITIONS:
        violations.append(f"invalid tradition: {tradition!r}")

    cs = entry.get("canonical_status", "")
    if cs and cs not in CANONICAL_STATUSES:
        violations.append(f"invalid canonical_status: {cs!r}")

    rs = entry.get("rights_status", "")
    if rs and rs not in RIGHTS_STATUSES:
        violations.append(f"invalid rights_status: {rs!r}")

    vs = entry.get("verification_status", "")
    if vs and vs not in VERIFICATION_STATUSES:
        violations.append(f"invalid verification_status: {vs!r}")

    # VERIFIED canonical_status requires source_basis
    if cs == "CANONICAL" and vs == "VERIFIED" and not entry.get("source_basis"):
        violations.append("VERIFIED canonical_status requires source_basis")

    return violations


def validate_agam_inventory(inventory: dict[str, Any]) -> list[str]:
    """Validate the full Agam inventory.

    Returns a list of violation descriptions (empty if valid).
    """
    violations: list[str] = []
    entries = inventory.get("sample_entries", [])
    seen_ids: set[str] = set()

    for i, entry in enumerate(entries):
        eid = entry.get("agam_id", f"entry_{i}")
        if eid in seen_ids:
            violations.append(f"duplicate agam_id: {eid!r}")
        seen_ids.add(eid)
        entry_violations = validate_agam_entry(entry)
        for v in entry_violations:
            violations.append(f"{eid}: {v}")

    return violations


def validate_source_entry(entry: dict[str, Any]) -> list[str]:
    """Validate a single source registry entry.

    Returns a list of violation descriptions (empty if valid).
    """
    violations: list[str] = []

    # Required fields
    for field in ["source_id", "title", "platform", "tradition",
                   "religious_scope", "knowledge_layer", "content_role",
                   "canonical_status", "language", "script",
                   "rights_status", "verification_status",
                   "retrieval_candidate", "sft_candidate"]:
        if field not in entry:
            violations.append(f"missing required field: {field}")

    # source_id format
    sid = entry.get("source_id", "")
    if sid and not sid.startswith("EXT-"):
        violations.append(f"source_id must start with 'EXT-': {sid!r}")

    # Enum checks
    platform = entry.get("platform", "")
    if platform and platform not in PLATFORMS:
        violations.append(f"invalid platform: {platform!r}")

    tradition = entry.get("tradition", "")
    if tradition and tradition not in TRADITIONS:
        violations.append(f"invalid tradition: {tradition!r}")

    scope = entry.get("religious_scope", "")
    if scope and scope not in RELIGIOUS_SCOPES:
        violations.append(f"invalid religious_scope: {scope!r}")

    layer = entry.get("knowledge_layer", "")
    if layer and layer not in KNOWLEDGE_LAYERS:
        violations.append(f"invalid knowledge_layer: {layer!r}")

    role = entry.get("content_role", "")
    if role and role not in CONTENT_ROLES:
        violations.append(f"invalid content_role: {role!r}")

    cs = entry.get("canonical_status", "")
    if cs and cs not in CANONICAL_STATUSES:
        violations.append(f"invalid canonical_status: {cs!r}")

    rs = entry.get("rights_status", "")
    if rs and rs not in RIGHTS_STATUSES:
        violations.append(f"invalid rights_status: {rs!r}")

    vs = entry.get("verification_status", "")
    if vs and vs not in VERIFICATION_STATUSES:
        violations.append(f"invalid verification_status: {vs!r}")

    # KEY RULE: download_available does NOT imply rights_status=CLEAR
    if entry.get("download_available") and entry.get("rights_status") == "CLEAR":
        if not entry.get("license") and not entry.get("license_evidence_url"):
            violations.append(
                "rights_status=CLEAR with download_available=true but no "
                "license or license_evidence_url — download alone does not "
                "grant training permission"
            )

    # sft_candidate requires CLEAR rights
    if entry.get("sft_candidate") and rs not in ("CLEAR",):
        violations.append(
            f"sft_candidate=true requires rights_status=CLEAR, got {rs!r}"
        )

    # VERIFIED verification_status on canonical requires source_basis-like evidence
    if vs == "VERIFIED" and cs in ("CANONICAL", "CANONICAL_TRANSLATION",
                                    "COMMENTARY_ON_CANON"):
        if not entry.get("license") and not entry.get("license_evidence_url"):
            violations.append(
                f"VERIFIED canonical status ({cs}) requires evidence "
                "(license or license_evidence_url)"
            )

    return violations


def validate_source_registry(registry: dict[str, Any]) -> list[str]:
    """Validate the full source registry.

    Returns a list of violation descriptions (empty if valid).
    """
    violations: list[str] = []
    entries = registry.get("initial_entries", [])
    seen_ids: set[str] = set()

    for i, entry in enumerate(entries):
        sid = entry.get("source_id", f"entry_{i}")
        if sid in seen_ids:
            violations.append(f"duplicate source_id: {sid!r}")
        seen_ids.add(sid)
        entry_violations = validate_source_entry(entry)
        for v in entry_violations:
            violations.append(f"{sid}: {v}")

    return violations


def validate_coverage_entry(entry: dict[str, Any]) -> list[str]:
    """Validate a single coverage matrix entry.

    Returns a list of violation descriptions (empty if valid).
    """
    violations: list[str] = []

    # Required fields
    for field in ["topic_id", "topic_name", "category", "tradition_relevance",
                   "coverage_status", "retrieval_ready", "sft_ready",
                   "evaluation_ready", "source_count"]:
        if field not in entry:
            violations.append(f"missing required field: {field}")

    # topic_id format
    tid = entry.get("topic_id", "")
    if tid and not tid.startswith("TOPIC-"):
        violations.append(f"topic_id must start with 'TOPIC-': {tid!r}")

    # Enum checks
    cat = entry.get("category", "")
    if cat and cat not in COVERAGE_CATEGORIES:
        violations.append(f"invalid category: {cat!r}")

    tr = entry.get("tradition_relevance", "")
    if tr and tr not in TRADITION_RELEVANCE:
        violations.append(f"invalid tradition_relevance: {tr!r}")

    cs = entry.get("coverage_status", "")
    if cs and cs not in COVERAGE_STATUSES:
        violations.append(f"invalid coverage_status: {cs!r}")

    # source_count must be non-negative
    sc = entry.get("source_count")
    if sc is not None and sc < 0:
        violations.append(f"source_count must be non-negative, got {sc}")

    return violations


def validate_coverage_matrix(matrix: dict[str, Any]) -> list[str]:
    """Validate the full coverage matrix.

    Returns a list of violation descriptions (empty if valid).
    """
    violations: list[str] = []
    entries = matrix.get("entries", [])
    seen_ids: set[str] = set()

    for i, entry in enumerate(entries):
        tid = entry.get("topic_id", f"entry_{i}")
        if tid in seen_ids:
            violations.append(f"duplicate topic_id: {tid!r}")
        seen_ids.add(tid)
        entry_violations = validate_coverage_entry(entry)
        for v in entry_violations:
            violations.append(f"{tid}: {v}")

    return violations


def check_no_download_implies_training(
    entries: list[dict[str, Any]],
) -> list[str]:
    """Verify that no source is considered training-usable merely because
    download_available=true.

    Returns a list of violations (empty if clean).
    """
    violations: list[str] = []
    for entry in entries:
        sid = entry.get("source_id", "unknown")
        if (entry.get("download_available")
                and entry.get("rights_status") not in ("CLEAR",)):
            if entry.get("sft_candidate"):
                violations.append(
                    f"{sid}: sft_candidate=true but rights_status is not CLEAR "
                    f"(download_available does not imply training permission)"
                )
    return violations


def check_no_unlicensed_verified_canonical(
    entries: list[dict[str, Any]],
) -> list[str]:
    """Verify that no source claims VERIFIED canonical status without
    an explicit rights/license basis.

    Returns a list of violations (empty if clean).
    """
    violations: list[str] = []
    for entry in entries:
        sid = entry.get("source_id", "unknown")
        vs = entry.get("verification_status", "")
        cs = entry.get("canonical_status", "")
        if vs == "VERIFIED" and cs in ("CANONICAL", "CANONICAL_TRANSLATION",
                                        "COMMENTARY_ON_CANON"):
            if not entry.get("license") and not entry.get("license_evidence_url"):
                violations.append(
                    f"{sid}: VERIFIED canonical status ({cs}) without "
                    f"license or license_evidence_url"
                )
    return violations


# ---------------------------------------------------------------------------
# Acquisition queue validation
# ---------------------------------------------------------------------------

_KNOWLEDGE_DIR_ACQ = _KNOWLEDGE_DIR.parent / "acquisition"
_QUEUE_PATH = _KNOWLEDGE_DIR_ACQ / "source_acquisition_queue_v1.json"

PRIORITIES = {"P0", "P1", "P2", "P3"}

ACQUISITION_STATUSES = {
    "DISCOVERED",
    "METADATA_REVIEWED",
    "RIGHTS_REVIEW",
    "APPROVED",
    "ACQUIRED",
    "REJECTED",
}

AVAILABILITY_STATES = {"ONLINE_FREE", "ONLINE_PAID", "IN_LIBRARY", "UNKNOWN"}

EXPECTED_USES = {"RETRIEVAL", "SFT", "BOTH", "REFERENCE"}


def load_acquisition_queue() -> dict[str, Any]:
    """Load the source acquisition queue."""
    return _load_json(_QUEUE_PATH)


def validate_acquisition_candidate(entry: dict[str, Any]) -> list[str]:
    """Validate a single acquisition queue candidate.

    Returns a list of violation descriptions (empty if valid).
    """
    violations: list[str] = []

    # Required fields
    for field in ["candidate_id", "title", "platform", "priority",
                   "tradition", "knowledge_layer", "content_role",
                   "language", "rights_status", "acquisition_status",
                   "expected_use", "duplicate_candidate"]:
        if field not in entry:
            violations.append(f"missing required field: {field}")

    # candidate_id format
    cid = entry.get("candidate_id", "")
    if cid and not cid.startswith("ACQ-"):
        violations.append(f"candidate_id must start with 'ACQ-': {cid!r}")

    # Enum checks
    priority = entry.get("priority", "")
    if priority and priority not in PRIORITIES:
        violations.append(f"invalid priority: {priority!r}")

    platform = entry.get("platform", "")
    if platform and platform not in PLATFORMS:
        violations.append(f"invalid platform: {platform!r}")

    tradition = entry.get("tradition", "")
    if tradition and tradition not in TRADITIONS:
        violations.append(f"invalid tradition: {tradition!r}")

    layer = entry.get("knowledge_layer", "")
    if layer and layer not in KNOWLEDGE_LAYERS:
        violations.append(f"invalid knowledge_layer: {layer!r}")

    role = entry.get("content_role", "")
    if role and role not in CONTENT_ROLES:
        violations.append(f"invalid content_role: {role!r}")

    practice = entry.get("practice")
    if practice is not None and practice not in PRACTICES:
        violations.append(f"invalid practice: {practice!r}")

    rs = entry.get("rights_status", "")
    if rs and rs not in RIGHTS_STATUSES:
        violations.append(f"invalid rights_status: {rs!r}")

    acq = entry.get("acquisition_status", "")
    if acq and acq not in ACQUISITION_STATUSES:
        violations.append(f"invalid acquisition_status: {acq!r}")

    eu = entry.get("expected_use", "")
    if eu and eu not in EXPECTED_USES:
        violations.append(f"invalid expected_use: {eu!r}")

    avail = entry.get("availability", "")
    if avail and avail not in AVAILABILITY_STATES:
        violations.append(f"invalid availability: {avail!r}")

    # KEY RULE: P0 candidates should not have RESTRICTED rights
    if priority == "P0" and rs == "RESTRICTED":
        violations.append(
            f"P0 candidate has rights_status=RESTRICTED — "
            f"cannot be priority acquisition target"
        )

    # KEY RULE: no SFT candidate may have RESTRICTED rights
    eu_val = entry.get("expected_use", "")
    if eu_val in ("SFT", "BOTH") and rs == "RESTRICTED":
        violations.append(
            f"expected_use={eu_val!r} but rights_status={rs!r} — "
            f"SFT training requires CLEAR rights, RESTRICTED is a blocker"
        )

    # Duplicate candidates must record duplicate_of
    if entry.get("duplicate_candidate") and not entry.get("duplicate_of"):
        violations.append(
            "duplicate_candidate=true but duplicate_of is not set"
        )

    return violations


def validate_acquisition_queue(queue: dict[str, Any]) -> list[str]:
    """Validate the full acquisition queue.

    Returns a list of violation descriptions (empty if valid).
    """
    violations: list[str] = []
    candidates = queue.get("candidates", [])
    seen_ids: set[str] = set()

    for i, entry in enumerate(candidates):
        cid = entry.get("candidate_id", f"entry_{i}")
        if cid in seen_ids:
            violations.append(f"duplicate candidate_id: {cid!r}")
        seen_ids.add(cid)
        entry_violations = validate_acquisition_candidate(entry)
        for v in entry_violations:
            violations.append(f"{cid}: {v}")

    return violations


def check_no_p0_restricted_rights(
    candidates: list[dict[str, Any]],
) -> list[str]:
    """Verify no P0 candidate has RESTRICTED rights.

    Returns a list of violations (empty if clean).
    """
    violations: list[str] = []
    for entry in candidates:
        cid = entry.get("candidate_id", "unknown")
        if (entry.get("priority") == "P0"
                and entry.get("rights_status") == "RESTRICTED"):
            violations.append(
                f"{cid}: P0 candidate with RESTRICTED rights"
            )
    return violations


def check_no_sft_without_clear_rights(
    candidates: list[dict[str, Any]],
) -> list[str]:
    """Verify no SFT-destined candidate has RESTRICTED rights.

    Returns a list of violations (empty if clean).
    """
    violations: list[str] = []
    for entry in candidates:
        cid = entry.get("candidate_id", "unknown")
        eu = entry.get("expected_use", "")
        rs = entry.get("rights_status", "")
        if eu in ("SFT", "BOTH") and rs == "RESTRICTED":
            violations.append(
                f"{cid}: expected_use={eu!r} but rights_status={rs!r}"
            )
    return violations
