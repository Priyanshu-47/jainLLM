"""Manifest construction and access.

The manifest is the system of record. Nothing downstream may read a source field
from anywhere else, and nothing may be ingested without a manifest row.

Layout of the manifest system:
  parents  : one source record per candidate source, built from
             (a) the read-only research-phase manifest at ../jain_svk_corpus_manifest.csv
             (b) configs/new_sources.csv, holding sources discovered during this
                 milestone, in the same schema
             (c) configs/curated_fields.csv, the extension fields the licence gate
                 needs (publisher, dates, evidence URLs, confidence, flags)
  artifacts: one row per downloaded/extracted artifact, sha256-addressed
  licence  : one row per source, the deterministic gate decision
  corpus   : the release-level record (versions, counts, hashes)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from svk_corpus.config import Config
from svk_corpus.schemas.records import (
    ARTIFACT_MANIFEST_FIELDS,
    SOURCE_MANIFEST_FIELDS,
    SourceRecord,
)

# Fields that come from the research-phase manifest but are renamed in the
# milestone schema. Anything not listed is carried across by the same name.
_PARENT_FIELD_ALIASES = {
    "format": "source_format",
}

# Defaults applied to every source record before curation is joined in.
_DEFAULTS = {
    "publisher": "unknown",
    "publication_year": "",
    "author_death_year": "",
    "license_confidence": "low",
    "uploader_asserted": "false",
    "ia_rights_statement": "false",
    "verification_required": "true",
    "curation_status": "NOT_CURATED",
    "acquisition_repository": "",
    "acquisition_identifier": "",
    "source_status": "CANDIDATE",
    "acquisition_status": "PENDING",
    "ocr_required": "false",
    "provenance": "",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def _parent_rows(config: Config) -> list[dict[str, str]]:
    parent = config.parent_manifest
    if not parent.is_file():
        raise FileNotFoundError(
            f"research-phase manifest not found at {parent}. It is a read-only input "
            f"to this pipeline; see README.md."
        )
    return _read_csv(parent)


def _new_source_rows(config: Config) -> list[dict[str, str]]:
    path = config.root / "configs" / "new_sources.csv"
    return _read_csv(path) if path.is_file() else []


def _curation_rows(config: Config) -> dict[str, dict[str, str]]:
    path = config.root / "configs" / "curated_fields.csv"
    if not path.is_file():
        return {}
    return {row["source_id"]: row for row in _read_csv(path) if row.get("source_id")}


def _metadata_rows(config: Config) -> dict[str, dict[str, str]]:
    """Round-2 language/sect/relation metadata layer (configs/metadata_fields.csv).

    Kept separate from licence curation on purpose: language classification and
    sect attribution are RESEARCH claims with their own evidence bases, and
    mixing them into the rights file made the rights record carry claims it
    cannot answer.
    """
    path = config.root / "configs" / "metadata_fields.csv"
    if not path.is_file():
        return {}
    return {row["source_id"]: row for row in _read_csv(path) if row.get("source_id")}


def _religious_scope_rows(config) -> dict[str, dict[str, str]]:
    """Religious-scope audit layer (configs/religious_scope.csv).

    Same discipline as the metadata layer: this file states WHAT a source is
    (CORE_STHANAKAVASI, CANONICAL_FOUNDATION, ...), never what we may do with
    it. Cells are packed as "value | confidence | basis | layer | teacher |
    lineage" in one CSV-safe column; empty or unknown ids are skipped. This
    layer is the sole authority for its six fields, mirroring how the metadata
    layer owns language/sect/relation fields.
    """
    path = config.root / "configs" / "religious_scope.csv"
    if not path.is_file():
        return {}
    out: dict[str, dict[str, str]] = {}
    order = ("religious_scope", "religious_scope_confidence",
             "religious_scope_basis", "knowledge_layer",
             "teacher_or_author", "lineage")
    for row in _read_csv(path):
        sid = (row.get("source_id") or "").strip()
        if not sid:
            continue
        packed = row.get("religious_scope") or ""
        parts = [p.strip() for p in packed.split("|")]
        parts += [""] * (len(order) - len(parts))
        entry = dict(zip(order, parts))
        if entry["religious_scope"]:
            out[sid] = entry
    return out


def _normalise_source_id(raw: str) -> str:
    return (raw or "").strip()


def build_source_manifest(config: Config) -> list[SourceRecord]:
    """Union the parent manifest with newly discovered sources, then join curation."""
    records: dict[str, dict[str, str]] = {}
    origin: dict[str, str] = {}

    for row in _parent_rows(config):
        sid = _normalise_source_id(row.get("source_id", ""))
        if not sid:
            continue
        records[sid] = _remap_parent_row(row)
        origin[sid] = "parent_manifest"

    for row in _new_source_rows(config):
        sid = _normalise_source_id(row.get("source_id", ""))
        if not sid:
            continue
        if sid in records:
            # Contradiction between the two inputs is a hard error rather than a
            # silent overwrite: see README "Contradiction handling".
            raise ValueError(f"source_id {sid} appears in both the parent manifest and "
                             f"configs/new_sources.csv")
        records[sid] = _remap_parent_row(row)
        origin[sid] = "new_sources"

    curation = _curation_rows(config)
    metadata_fields = _metadata_rows(config)
    religious_scope = _religious_scope_rows(config)

    out: list[SourceRecord] = []
    for sid in sorted(records):
        values = dict(records[sid])
        for key, default in _DEFAULTS.items():
            values.setdefault(key, default)
        cur = curation.get(sid)
        if cur:
            values["curation_status"] = "CURATED"
            for key, value in cur.items():
                if key == "source_id":
                    continue
                if key == "curation_note":
                    values["notes"] = _merge_notes(values.get("notes", ""), value)
                    continue
                values[key] = value
        else:
            if values.get("curation_status") == "CURATED":
                values["curation_status"] = "CURATED"
        meta = metadata_fields.get(sid)
        if meta:
            # Empty cells in the metadata file never overwrite anything: the
            # layer states claims, it does not erase them.
            for key, value in meta.items():
                if key == "source_id" or not value:
                    continue
                values[key] = value
        audit = religious_scope.get(sid)
        if audit:
            for key, value in audit.items():
                values[key] = value
        # Evidence URL falls back to the item page so that every decision has one.
        if not values.get("license_evidence_url"):
            values["license_evidence_url"] = values.get("source_url", "")
        values["provenance"] = _provenance_json(values, origin.get(sid, "unknown"))
        for key in SOURCE_MANIFEST_FIELDS:
            values.setdefault(key, "")
        out.append(SourceRecord({k: values.get(k, "") for k in SOURCE_MANIFEST_FIELDS}))
    return out


def _remap_parent_row(row: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in row.items():
        if key is None:
            continue
        out[_PARENT_FIELD_ALIASES.get(key, key)] = value
    return out


def _merge_notes(existing: str, addition: str) -> str:
    if not existing:
        return addition
    if addition in existing:
        return existing
    return f"{existing} :: {addition}"


def _provenance_json(values: dict[str, str], origin: str) -> str:
    payload = {
        "manifest_origin": origin,
        "repository": values.get("repository", ""),
        "acquisition_repository": values.get("acquisition_repository", ""),
        "identifier": values.get("acquisition_identifier", ""),
        "source_url": values.get("source_url", ""),
        "license_evidence_url": values.get("license_evidence_url", ""),
        "curation_status": values.get("curation_status", "NOT_CURATED"),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


# ---------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------
def write_source_manifest(sources: list[SourceRecord], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(SOURCE_MANIFEST_FIELDS),
                                quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for src in sources:
            writer.writerow(src.as_row())
    return path


def load_source_manifest(path: Path) -> list[SourceRecord]:
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} not found. Run `make manifest` first."
        )
    return [SourceRecord(row) for row in _read_csv(path)]


def update_source_fields(path: Path, updates: dict[str, dict[str, str]]) -> Path:
    """Read-modify-write selected fields for selected sources."""
    sources = load_source_manifest(path)
    for src in sources:
        patch = updates.get(src.source_id)
        if not patch:
            continue
        for key, value in patch.items():
            if key not in SOURCE_MANIFEST_FIELDS:
                raise KeyError(f"unknown source manifest field: {key}")
            src.values[key] = value
    return write_source_manifest(sources, path)


def _artifact_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (row.get("source_id", ""), row.get("artifact_type", ""),
            row.get("filename", ""), row.get("sha256", ""))


def merge_artifact_rows(existing: list[dict[str, str]],
                        new: list[dict[str, str]]) -> list[dict[str, str]]:
    """Union two artifact row sets, keeping existing rows first.

    Appending stages (extraction adds EXTRACTED_TEXT rows) must never be able to
    shrink the manifest. Losing the acquisition rows would orphan every release
    record from its source artifact, which is the one thing this pipeline promises
    never to do, so the merge is explicit and order-preserving rather than a
    wholesale rewrite.
    """
    seen: dict[tuple[str, str, str, str], dict[str, str]] = {}
    out: list[dict[str, str]] = []
    for row in [*existing, *new]:
        key = _artifact_key(row)
        if key in seen:
            existing_index = out.index(seen[key])
            out[existing_index] = row
            continue
        seen[key] = row
        out.append(row)
    return out


def write_artifact_manifest(rows: list[dict[str, str]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(ARTIFACT_MANIFEST_FIELDS),
                                quoting=csv.QUOTE_ALL, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in ARTIFACT_MANIFEST_FIELDS})
    return path


def load_artifact_manifest(path: Path) -> list[dict[str, str]]:
    return _read_csv(path) if path.is_file() else []
