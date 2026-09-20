"""Pipeline stages. Every stage reads its predecessor's files and writes its own.

WHY FILE-BASED STAGES RATHER THAN ONE FUNCTION
Each stage is independently runnable and its output is inspectable on disk. That
is what makes the pipeline auditable: a reviewer can read
`data/normalized/<source_id>/normalization.json` and see exactly which characters
changed, without re-running anything. It also means a failure in one source never
destroys the work done on another.

STAGE CONTRACT
    manifest   -> manifests/source_manifest.csv
    gate       -> manifests/license_manifest.csv
    acquire    -> data/raw|<quarantine>/<source_id>/ + manifests/artifact_manifest.csv
    extract    -> data/extracted/<source_id>/{text.txt,extraction.json}
    normalize  -> data/normalized/<source_id>/{text.txt,normalization.json}
    segment    -> data/segmented/<source_id>/{units.jsonl,segmentation.json}
    dedupe     -> data/deduplicated/{decisions.jsonl,dedup_stats.json}
    quality    -> data/quality/{units_quality.jsonl,quality_stats.json} + ocr report
    release    -> data/release/{rag_corpus.jsonl,training_corpus.jsonl,
                                excluded_sources.jsonl,manifest.json}
    stats      -> data/reports/{corpus_statistics.md,INGEST_REPORT.md,
                                tokenizer_measurements.json,corpus_manifest.json}
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from svk_corpus import PIPELINE_VERSION, __version__
from svk_corpus.acquisition.internet_archive import acquire_item
from svk_corpus.acquisition.huggingface import acquire_huggingface
from svk_corpus.config import Config, load_config
from svk_corpus.deduplication.dedupe import Deduplicator, STATUS_EXACT
from svk_corpus.extraction import extract_any
from svk_corpus.licensing.gate import evaluate_all_sources, license_gate, write_license_manifest
from svk_corpus.manifests import (
    build_source_manifest,
    load_artifact_manifest,
    load_source_manifest,
    merge_artifact_rows,
    write_artifact_manifest,
    write_source_manifest,
)
from svk_corpus.normalization import (
    NORMALIZATION_VERSION,
    detect_language_hint,
    detect_script,
    language_script_consistency,
    normalize_text,
)
from svk_corpus.ocr.pipeline import build_report, engine_availability_note, write_reports, write_reports_csv
from svk_corpus.quality.checks import (
    assess_text,
    detect_running_headers,
    metadata_completeness,
    provenance_completeness,
)
from svk_corpus.release import (
    EXCLUDED_FILENAME,
    RAG_FILENAME,
    RELEASE_MANIFEST,
    TRAINING_FILENAME,
    JsonlWriter,
    build_record,
    sha256_file,
    write_excluded,
    write_release_manifest,
)
from svk_corpus.schemas.records import GateState, SourceRecord
from svk_corpus.segmentation import segment_document
from svk_corpus.selection import CORPUS_RAG, CORPUS_TRAINING, admit_all
from svk_corpus.tokenization.measurements import (
    TokenizerRegistry,
    cpt_eligibility,
    check_candidates_match_config,
    fetch_tokenizers,
    write_measurements,
)


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                    encoding="utf-8")
    return path


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _write_jsonl(path: Path, rows: Iterable[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


# ===========================================================================
# check
# ===========================================================================
def cmd_check(config: Config) -> int:
    print(f"svk-corpus {__version__}  pipeline {PIPELINE_VERSION}")
    print(f"python {sys.version.split()[0]} on {sys.platform}")
    print(f"repo root: {config.root}")
    problems: list[str] = []

    if sys.version_info < (3, 11):
        problems.append("Python 3.11+ required (tomllib for configs/policy.toml)")
    if not config.parent_manifest.is_file():
        problems.append(
            f"research-phase manifest not found at {config.parent_manifest}; it is a "
            f"read-only input to this pipeline"
        )
    config.ensure_dirs()
    for name in ("manifests", "raw", "quarantine", "extracted", "normalized",
                 "deduplicated", "release", "reports", "cache"):
        config.path("paths", name).mkdir(parents=True, exist_ok=True)

    for problem in check_candidates_match_config(config):
        print(f"  NOTE tokenizer config: {problem}")

    print(f"OCR: {engine_availability_note()}")
    print(f"Tokenizers {config.get('tokenizers', 'primary', '?')} is the primary "
          f"CPT measuring instrument")
    if problems:
        print("\nBLOCKING PROBLEMS:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\ncheck OK (stdlib only, no third-party imports required)")
    return 0


# ===========================================================================
# manifest / gate
# ===========================================================================
def cmd_manifest(config: Config) -> int:
    sources = build_source_manifest(config)
    path = write_source_manifest(sources, config.manifests_dir / "source_manifest.csv")
    print(f"source manifest: {len(sources)} sources -> {path}")
    return 0


def _load_sources(config: Config) -> list[SourceRecord]:
    return load_source_manifest(config.manifests_dir / "source_manifest.csv")


def cmd_gate(config: Config) -> int:
    sources = _load_sources(config)
    decisions = evaluate_all_sources(sources, config)
    path = write_license_manifest(decisions, config.manifests_dir / "license_manifest.csv")
    counts: dict[str, int] = {}
    for decision in decisions:
        counts[decision.state.value] = counts.get(decision.state.value, 0) + 1
    # The gate is authoritative for what we may DO with a source. Sync its
    # decision back into the manifest's free-text `training_permission` column
    # so a stale research-era value can never contradict the licence manifest.
    sync_training_permission(sources, decisions)
    write_source_manifest(sources, config.manifests_dir / "source_manifest.csv")
    print(f"licence manifest: {len(decisions)} decisions -> {path}")
    for state in ("TRAINING_ALLOWED", "RAG_ALLOWED", "WITH_CONDITIONS",
                  "NEEDS_PERMISSION", "NOT_ALLOWED", "UNKNOWN"):
        if counts.get(state):
            print(f"  {state:<20} {counts[state]}")
    return 0


def _gate_map(config: Config) -> dict[str, Any]:
    from svk_corpus.licensing.gate import load_license_manifest
    from svk_corpus.schemas.records import GateDecision, GateState

    rows = load_license_manifest(config.manifests_dir / "license_manifest.csv")
    out: dict[str, GateDecision] = {}
    for source_id, row in rows.items():
        out[source_id] = GateDecision(
            source_id=source_id,
            state=GateState(row["decision"]),
            rule_id=row["rule_id"],
            reason=row["reason"],
            evidence=json.loads(row["evidence"] or "{}"),
            confidence=row["confidence"],
            requirements=json.loads(row["requirements"] or "[]"),
            requirements_met=row.get("requirements_met") == "true",
            noncommercial=row.get("noncommercial") == "true",
            sharealike=row.get("sharealike") == "true",
            verification_required=row.get("verification_required") == "true",
            evaluated_at=row.get("evaluated_at", ""),
        )
    return out


from svk_corpus.selection import sync_training_permission


def _artifact_index(artifacts: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    """Best available artifact row per source, for provenance grading.

    Preference order matters: the EXTRACTED_TEXT row carries the hash of the text
    we actually distribute, which is the stronger provenance claim, so it wins over
    the raw download row when both exist.
    """
    index: dict[str, dict[str, str]] = {}
    preferred = {"EXTRACTED_TEXT": 0, "SOURCE_OCR_MARKUP": 1}
    for row in artifacts:
        source_id = row.get("source_id", "")
        if not source_id or row.get("status") not in ("OK", ""):
            continue
        artifact_type = row.get("artifact_type", "")
        if artifact_type in ("SOURCE_METADATA", "ACQUISITION_STATUS"):
            continue
        normalised = {
            "artifact_sha256": row.get("sha256", ""),
            "sha256": row.get("sha256", ""),
            "download_timestamp": row.get("download_timestamp", ""),
            "filename": row.get("filename", ""),
            "artifact_type": artifact_type,
        }
        rank = preferred.get(artifact_type, 5)
        existing = index.get(source_id)
        if existing is None or rank < preferred.get(existing["artifact_type"], 5):
            index[source_id] = normalised
    return index


def _admissions(config: Config, gates: dict[str, Any], artifacts: list[dict[str, str]]):
    sources = _load_sources(config)
    index = _artifact_index(artifacts)
    acquired = set(index)
    return sources, gates, admit_all(sources, gates, config,
                                     acquired_ids=acquired, artifact_index=index)


# ===========================================================================
# acquire
# ===========================================================================
def cmd_acquire(config: Config) -> int:
    sources = _load_sources(config)
    gates = _gate_map(config)
    artifacts: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    acquired = skipped = quarantined = 0

    for source in sources:
        gate = gates.get(source.source_id)
        # Repository names arrive from several catalogues with inconsistent
        # punctuation ('internet_archive', 'Internet Archive', 'IA'). Normalise
        # before dispatch so a formatting difference cannot silently skip a
        # source.
        repository = _normalise_repository(source.get("acquisition_repository"))
        if not repository:
            continue
        releasable = bool(gate and gate.releasable)
        if not releasable:
            quarantined += 1
            print(f"  QUARANTINE {source.source_id}: "
                  f"{(gate.state.value if gate else 'no gate decision')}")
        if repository == "internetarchive":
            new_artifacts, new_failures = acquire_item(source, config, releasable)
            artifacts.extend(a.as_row() for a in new_artifacts)
            failures.extend(new_failures)
            ok = any(a.values.get("status") == "OK" and
                     a.values.get("artifact_type") not in ("SOURCE_METADATA",
                                                           "ACQUISITION_STATUS")
                     for a in new_artifacts)
            acquired += 1 if ok else 0
            skipped += 0 if ok else 1
            print(f"  {'ACQUIRED ' if ok else 'NO TEXT  '} {source.source_id}")
        elif repository == "huggingface":
            # Round 2: real acquisition replaces the v0.1 placeholder that only
            # recorded the gap. Same provenance contract as the IA path:
            # verbatim metadata + hashed original file + checksums.
            new_artifacts, new_failures = acquire_huggingface(source, config)
            artifacts.extend(a.as_row() for a in new_artifacts)
            failures.extend(new_failures)
            ok = any(a.values.get("status") == "OK" and
                     a.values.get("artifact_type") not in ("SOURCE_METADATA",
                                                           "ACQUISITION_STATUS")
                     for a in new_artifacts)
            acquired += 1 if ok else 0
            skipped += 0 if ok else 1
            print(f"  {'ACQUIRED ' if ok else 'NO TEXT  '} {source.source_id} (huggingface)")
        else:
            print(f"  SKIP {source.source_id}: unsupported repository '{repository}'")

    write_artifact_manifest(artifacts, config.manifests_dir / "artifact_manifest.csv")
    _write_json(config.reports_dir / "acquisition_failures.json",
                {"generated_at": _now(), "failures": failures})
    print(f"acquire: {len(artifacts)} artifact rows, {acquired} with text, "
          f"{skipped} without, {quarantined} quarantined, {len(failures)} failures")
    return 0


# ===========================================================================
# extract
# ===========================================================================
def _text_artifacts(config: Config) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in load_artifact_manifest(config.manifests_dir / "artifact_manifest.csv"):
        if row.get("status") != "OK" or row.get("artifact_type") in (
                "SOURCE_METADATA", "ACQUISITION_STATUS", "EXTRACTED_TEXT"):
            continue
        out.setdefault(row["source_id"], row)
    return out


def cmd_extract(config: Config) -> int:
    artifacts = _text_artifacts(config)
    # Read-then-merge, never read-then-replace: extraction only appends rows.
    existing_rows = load_artifact_manifest(config.manifests_dir / "artifact_manifest.csv")
    new_rows: list[dict[str, str]] = []
    results: list[dict[str, Any]] = []

    for source_id, artifact in sorted(artifacts.items()):
        raw_dir = config.path("paths", "raw") / source_id
        path = raw_dir / artifact["filename"]
        if not path.is_file():
            print(f"  MISSING {source_id}: {path}")
            results.append({"source_id": source_id, "status": "MISSING_FILE",
                            "path": str(path)})
            continue
        result = extract_any(path)
        out_dir = config.path("paths", "extracted") / source_id
        out_dir.mkdir(parents=True, exist_ok=True)

        # Page boundaries: prefer the extractor's pages, joining with a form feed
        # so segmentation can recover page numbers.
        pages = [p for p in result.pages if p is not None]
        text = "\f".join(pages) if len(pages) > 1 else result.text

        (out_dir / "text.txt").write_text(text, encoding="utf-8")
        _write_json(out_dir / "extraction.json", {
            "source_id": source_id,
            "status": result.status,
            "method": result.method,
            "pages": len(pages),
            "characters": len(text),
            "error": result.error,
            "warnings": result.warnings,
            "metrics": result.metrics,
            "text_roles": result.text_roles,
            "artifact_filename": artifact["filename"],
            "artifact_sha256": artifact["sha256"],
            "source_url": artifact.get("source_url", ""),
            "extracted_at": _now(),
        })
        if pages:
            page_dir = out_dir / "pages"
            page_dir.mkdir(exist_ok=True)
            for index, page in enumerate(pages, start=1):
                (page_dir / f"{index:05d}.txt").write_text(page, encoding="utf-8")

        new_rows.append({
            "artifact_id": f"ext_{source_id}_{artifact['sha256'][:12]}",
            "source_id": source_id,
            "artifact_type": "EXTRACTED_TEXT",
            "filename": "text.txt",
            "sha256": sha256_file(out_dir / "text.txt"),
            "bytes": str((out_dir / "text.txt").stat().st_size),
            "mime_type": "text/plain",
            "download_timestamp": "",
            "extraction_method": result.method,
            "ocr_method": "source_text_layer" if result.method in
                          ("SOURCE_TEXT_LAYER", "SOURCE_OCR_MARKUP") else "",
            "normalization_version": "",
            "source_url": artifact.get("source_url", ""),
            "status": result.status,
            "error": result.error,
        })
        results.append({"source_id": source_id, "status": result.status,
                        "method": result.method, "characters": len(text),
                        "pages": len(pages), "error": result.error})
        print(f"  {result.status:<22} {source_id:<12} {result.method:<22} "
              f"{len(text):>9} chars {len(pages):>4} pages")

    merged = merge_artifact_rows(existing_rows, new_rows)
    if len(merged) < len(existing_rows):
        raise AssertionError(
            f"extract would shrink the artifact manifest from {len(existing_rows)} "
            f"to {len(merged)} rows; refusing to write"
        )
    write_artifact_manifest(merged, config.manifests_dir / "artifact_manifest.csv")
    _write_json(config.reports_dir / "extraction_summary.json",
                {"generated_at": _now(), "results": results})
    print(f"extract: {len(results)} artifacts processed, "
          f"{sum(1 for r in results if r.get('status') == 'OK')} with usable text, "
          f"artifact manifest {len(existing_rows)} -> {len(merged)} rows")
    return 0


# ===========================================================================
# normalize / segment
# ===========================================================================
def cmd_normalize(config: Config) -> int:
    sources = {s.source_id: s for s in _load_sources(config)}
    form = str(config.get("normalization", "unicode_form", "NFC"))
    base = config.path("paths", "extracted")
    for source_dir in sorted(p for p in base.glob("*") if p.is_dir()):
        text_path = source_dir / "text.txt"
        if not text_path.is_file():
            continue
        source_id = source_dir.name
        source = sources.get(source_id)
        raw = text_path.read_text(encoding="utf-8")
        result = normalize_text(raw, unicode_form=form)

        script_evidence = detect_script(result.normalized)
        hint = detect_language_hint(result.normalized, script=script_evidence.script)
        declared_language = source.get("language", "") if source else ""
        declared_script = source.get("script", "") if source else ""
        consistency = language_script_consistency(declared_language,
                                                  script_evidence.script)

        out_dir = config.path("paths", "normalized") / source_id
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "text.txt").write_text(result.normalized, encoding="utf-8")
        _write_json(out_dir / "normalization.json", {
            "source_id": source_id,
            "version": NORMALIZATION_VERSION,
            "generated_at": _now(),
            "changed": result.changed,
            "stats": result.stats.as_dict(),
            "script_evidence": script_evidence.as_dict(),
            "detected_language_hint": hint.as_dict(),
            "declared_language": declared_language,
            "declared_script": declared_script,
            "consistency_problems": consistency,
        })
        print(f"  {source_id:<12} {len(raw):>9} -> {len(result.normalized):>9} chars | "
              f"script {script_evidence.script} ({script_evidence.purity:.0%}) | "
              f"hint {hint.language}/{hint.confidence}")
    return 0


def cmd_segment(config: Config) -> int:
    sources = {s.source_id: s for s in _load_sources(config)}
    base = config.path("paths", "normalized")
    max_chars = int(config.get("segmentation", "max_unit_chars", 1500))
    total_units = 0
    for source_dir in sorted(p for p in base.glob("*") if p.is_dir()):
        text_path = source_dir / "text.txt"
        if not text_path.is_file():
            continue
        source_id = source_dir.name
        source = sources.get(source_id)
        norm = _read_json(source_dir / "normalization.json") or {}
        extraction = _read_json(config.path("paths", "extracted") / source_id /
                                "extraction.json") or {}
        # How the text was produced decides the text_role. A scan-derived OCR
        # layer is OCR, not the original encoding of the work. Round 2: a
        # structured parallel dataset carries separate roles per layer.
        method = extraction.get("method", "")
        roles = extraction.get("text_roles") or None
        if roles:
            text_role = roles[0]
        else:
            text_role = "OCR" if method in ("SOURCE_TEXT_LAYER", "SOURCE_OCR_MARKUP") else "ORIGINAL"
        language = (norm.get("detected_language_hint") or {}).get("language", "unknown")
        script = (norm.get("script_evidence") or {}).get("script", "unknown")

        text = text_path.read_text(encoding="utf-8")
        units, stats = segment_document(
            text, source_id=source_id, language=language, script=script,
            text_role=text_role, page_roles=roles, max_chunk_chars=max_chars,
            provenance={
                "source_url": source.get("source_url", "") if source else "",
                "artifact_sha256": extraction.get("artifact_sha256", ""),
                "repository": source.get("repository", "") if source else "",
                "identifier": source.get("acquisition_identifier", "") if source else "",
                "extraction_method": method,
                "text_role": text_role,
            },
        )
        out_dir = config.path("paths", "deduplicated").parent / "segmented" / source_id
        out_dir.mkdir(parents=True, exist_ok=True)
        _write_jsonl(out_dir / "units.jsonl", [u.to_dict() for u in units])
        _write_json(out_dir / "segmentation.json",
                    {"source_id": source_id, "generated_at": _now(),
                     "text_role": text_role, "stats": stats.as_dict()})
        total_units += stats.units
        print(f"  {source_id:<12} {stats.units:>6} units "
              f"({stats.verses} verse, {stats.paragraphs} para, {stats.chunks} chunk) "
              f"structure={stats.structure_confidence}")
    print(f"segment: {total_units} units across all sources")
    return 0


# ===========================================================================
# dedupe
# ===========================================================================
def _segmented_dirs(config: Config) -> list[Path]:
    base = config.path("paths", "deduplicated").parent / "segmented"
    return sorted(p for p in base.glob("*") if p.is_dir()) if base.is_dir() else []


def cmd_dedupe(config: Config) -> int:
    deduper = Deduplicator(
        near_threshold=float(config.get("dedup", "near_dup_threshold", 0.85)),
        num_hashes=int(config.get("dedup", "minhash_num_perm", 64)),
        shingle_size=int(config.get("dedup", "minhash_shingle", 5)),
    )
    decisions: list[dict] = []
    for source_dir in _segmented_dirs(config):
        for row in _read_jsonl(source_dir / "units.jsonl"):
            if row.get("unit_type") == "document":
                continue
            decision = deduper.add(
                row["unit_id"], row.get("normalized_text") or row.get("text") or "",
                raw_text=row.get("text") or "",
                text_role=row.get("text_role", "ORIGINAL"),
                language=row.get("language", "unknown"),
            )
            entry = {"unit_id": row["unit_id"], "source_id": row["source_id"],
                     **_decision_dict(decision)}
            decisions.append(entry)
    out_dir = config.path("paths", "deduplicated")
    _write_jsonl(out_dir / "decisions.jsonl", decisions)
    stats = deduper.stats()
    stats["clusters"] = deduper.cluster_summary()
    stats["generated_at"] = _now()
    _write_json(out_dir / "dedup_stats.json", stats)
    print(f"dedupe: {stats['units_evaluated']} units, "
          f"{stats[STATUS_EXACT]} exact, duplicate_rate={stats['duplicate_rate']:.4f}")
    print(f"  {stats['semantic']['reason']}")
    return 0


def _decision_dict(decision) -> dict:
    data = decision.as_dict()
    data.pop("unit_id", None)
    return data


# ===========================================================================
# quality
# ===========================================================================
def cmd_quality(config: Config) -> int:
    sources = {s.source_id: s for s in _load_sources(config)}
    rows: list[dict] = []
    reports = []
    for source_dir in _segmented_dirs(config):
        source_id = source_dir.name
        source = sources.get(source_id)
        segmentation = _read_json(source_dir / "segmentation.json") or {}
        structural = {"high": 1.0, "medium": 0.6, "unknown": 0.2}.get(
            (segmentation.get("stats") or {}).get("structure_confidence", "unknown"), 0.2)
        # Task 29: a document whose script evidence is itself ambiguous is a
        # legitimately mixed-script edition (SVK-2025/2029: Romanized Prakrit
        # mool + Devanagari Hindi). Per-unit SCRIPT_MISMATCH against the
        # document-level expectation would punish that mixture, so the flag is
        # relabelled descriptively. Intra-word confusion (SCRIPT_CONFUSION) —
        # the actual OCR-corruption signal — is untouched.
        norm_meta = _read_json(config.path("paths", "normalized") / source_id /
                               "normalization.json") or {}
        doc_mixed_script = bool((norm_meta.get("script_evidence") or {}).get("ambiguous"))
        units = [r for r in _read_jsonl(source_dir / "units.jsonl")
                 if r.get("unit_type") != "document"]
        page_dir = config.path("paths", "extracted") / source_id / "pages"
        pages = [p.read_text(encoding="utf-8") for p in sorted(page_dir.glob("*.txt"))] \
            if page_dir.is_dir() else []
        repeats = detect_running_headers(pages) if pages else []

        for row in units:
            text = row.get("normalized_text") or row.get("text") or ""
            quality = assess_text(text, language=row.get("language", "unknown"),
                                  script=row.get("script", "unknown"),
                                  structural_quality=structural)
            payload = quality.as_dict()
            if doc_mixed_script and "SCRIPT_MISMATCH" in payload.get("flags", []):
                payload["flags"].remove("SCRIPT_MISMATCH")
                payload["flags"].append("MIXED_SCRIPT_DOCUMENT")
            payload["unit_id"] = row["unit_id"]
            payload["source_id"] = source_id
            rows.append(payload)

        text_path = config.path("paths", "normalized") / source_id / "text.txt"
        text = text_path.read_text(encoding="utf-8") if text_path.is_file() else ""
        extraction = _read_json(config.path("paths", "extracted") / source_id /
                                "extraction.json") or {}
        report = build_report(
            source_id, text, pages,
            engine="internet-archive-derived" if extraction.get("method") in
                   ("SOURCE_TEXT_LAYER", "SOURCE_OCR_MARKUP") else extraction.get("method", "unknown"),
            declared_language=source.get("language", "") if source else "",
            declared_script=source.get("script", "") if source else "",
            native_language_claim=_native_language_claim(config, source_id),
        )
        if repeats:
            report.findings.append(
                f"{len(repeats)} candidate running header/footer lines detected "
                f"(reported, not removed): "
                + "; ".join(f"x{r.count} {r.text[:40]!r}" for r in repeats[:5])
            )
        reports.append(report)

    out_dir = config.path("paths", "deduplicated").parent / "quality"
    _write_jsonl(out_dir / "units_quality.jsonl", rows)
    summary = _quality_summary(rows, reports)
    _write_json(out_dir / "quality_stats.json", summary)
    write_reports(reports, out_dir / "ocr_quality_report.json")
    write_reports_csv(reports, out_dir / "ocr_quality_report.csv")
    print(f"quality: {len(rows)} units assessed, "
          f"{summary['flags']['units_with_flags']} carry flags; "
          f"OCR manual review required for {summary['ocr']['manual_review_required']} sources")
    return 0


def _native_language_claim(config: Config, source_id: str) -> str | None:
    """The holding repository's own language opinion, when its metadata has one."""
    path = config.path("paths", "raw") / source_id / "metadata.json"
    meta = _read_json(path)
    if not isinstance(meta, dict):
        return None
    raw = (meta.get("metadata") or {}).get("language")
    if isinstance(raw, str):
        return raw.strip() or None
    if isinstance(raw, list) and raw:
        return str(raw[0])
    return None


def _quality_summary(rows: Sequence[dict], reports: Sequence[Any]) -> dict:
    flags: dict[str, int] = {}
    for row in rows:
        for flag in row.get("flags", []):
            flags[flag] = flags.get(flag, 0) + 1
    n = max(1, len(rows))
    lengths = sorted(r.get("chars", 0) for r in rows)

    def percentile(fraction: float) -> int:
        if not lengths:
            return 0
        index = min(len(lengths) - 1, int(fraction * len(lengths)))
        return lengths[index]

    return {
        "generated_at": _now(),
        "units": len(rows),
        "unit_lengths": {
            "min": lengths[0] if lengths else 0,
            "p25": percentile(0.25),
            "p50": percentile(0.50),
            "p75": percentile(0.75),
            "p99": percentile(0.99),
            "max": lengths[-1] if lengths else 0,
            "mean": round(sum(lengths) / n, 2),
            "under_40_chars": sum(1 for v in lengths if v < 40),
            "note": "very short units are usually verse refrains or OCR line "
                    "fragments; they are kept but are weak retrieval targets",
        },
        "flags": {
            "units_with_flags": sum(1 for r in rows if r.get("flags")),
            "counts": dict(sorted(flags.items(), key=lambda kv: -kv[1])),
        },
        "means": {
            "unicode_quality": round(sum(r.get("unicode_quality", 0) for r in rows) / n, 6),
            "ocr_noise_estimate": round(
                sum(r.get("ocr_noise_estimate", 0) for r in rows) / n, 6),
            "structural_quality": round(
                sum(r.get("structural_quality", 0) for r in rows) / n, 6),
            "symbol_ratio": round(sum(r.get("symbol_ratio", 0) for r in rows) / n, 6),
        },
        "ocr": {
            "sources": len(reports),
            "manual_review_required": sum(1 for r in reports if r.manual_review_required),
            "engine_availability": engine_availability_note(),
        },
    }


# ===========================================================================
# release
# ===========================================================================
def cmd_release(config: Config) -> int:
    sources = {s.source_id: s for s in _load_sources(config)}
    artifacts = load_artifact_manifest(config.manifests_dir / "artifact_manifest.csv")
    gates = _gate_map(config)
    _, _, admissions = _admissions(config, gates, artifacts)
    admission_map = {a.source_id: a for a in admissions}

    artifact_index: dict[str, dict[str, str]] = {}
    for row in artifacts:
        if row.get("artifact_type") == "EXTRACTED_TEXT":
            artifact_index.setdefault(row["source_id"], row)

    quality_rows = {r["unit_id"]: r for r in _read_jsonl(
        config.path("paths", "deduplicated").parent / "quality" / "units_quality.jsonl")}
    dedup_rows = {r["unit_id"]: r for r in _read_jsonl(
        config.path("paths", "deduplicated") / "decisions.jsonl")}

    out_dir = config.path("paths", "release")
    min_unit_chars = int(config.get("release", "min_unit_chars_for_release", 24))
    training_flags = set(config.get("release", "training_floor_flags", []))
    rag_flags = set(config.get("release", "rag_floor_flags", []))
    include_translations_in_training = bool(config.get(
        "release", "include_translation_units_in_training", False))
    diverted_name = str(config.get("release", "diverted_units_filename",
                                "low_quality_units.jsonl"))

    writers = {
        CORPUS_RAG: JsonlWriter(out_dir / RAG_FILENAME),
        CORPUS_TRAINING: JsonlWriter(out_dir / TRAINING_FILENAME),
    }
    diverted = JsonlWriter(out_dir / diverted_name)
    stats = {CORPUS_RAG: {}, CORPUS_TRAINING: {}}
    excluded: list[dict] = []
    per_source: dict[str, dict[str, Any]] = {}
    diversion_counts: dict[str, int] = {}
    diversion_chars = 0

    for admission in admissions:
        source_id = admission.source_id
        source = sources.get(source_id)
        gate = gates.get(source_id)
        entry = {
            "source_id": source_id,
            "title": source.get("title", "") if source else "",
            "admitted_products": sorted(admission.corpora),
            "reasons": admission.reasons,
            "flags": admission.flags,
            "gate_state": gate.state.value if gate else "",
            "gate_rule": gate.rule_id if gate else "",
            "verification_outstanding": admission.verification_outstanding,
            "computed_provenance_grade": (admission.checks.get(
                "computed_provenance") or {}).get("grade", ""),
        }
        if not admission.corpora or source is None or gate is None:
            entry["units_released"] = 0
            per_source[source_id] = entry
            excluded.append({**entry, "reason_detail": admission.reasons})
            continue

        artifact = artifact_index.get(source_id, {})
        acquisitions = [r for r in artifacts if r["source_id"] == source_id
                        and r.get("download_timestamp")]
        timestamp = acquisitions[0]["download_timestamp"] if acquisitions else ""
        source_dir = config.path("paths", "deduplicated").parent / "segmented" / source_id
        units = [r for r in _read_jsonl(source_dir / "units.jsonl")
                 if r.get("unit_type") != "document"]

        written_counts = {CORPUS_RAG: 0, CORPUS_TRAINING: 0}
        skipped_dup = 0
        for row in units:
            dedup = dedup_rows.get(row["unit_id"], {})
            if dedup.get("status") in (STATUS_EXACT, "NEAR_DUPLICATE") \
                    and not dedup.get("kept", True):
                skipped_dup += 1
                continue

            unit = _rehydrate_unit(row)
            metrics = dict(quality_rows.get(row["unit_id"], {}))
            metrics.pop("unit_id", None)
            metrics.pop("source_id", None)
            unit.quality = metrics
            unit.quality["duplicate"] = {
                "status": dedup.get("status", "UNKNOWN"),
                "similarity": dedup.get("similarity", 0.0),
                "method": dedup.get("method", ""),
            }

            # --- release quality routing ---------------------------------
            text = unit.normalized_text or unit.text
            flags = set(metrics.get("flags") or [])
            products = set(admission.corpora)
            if len(text) < min_unit_chars:
                flags.add("BELOW_MIN_UNIT_CHARS")
            if flags & training_flags:
                products.discard(CORPUS_TRAINING)
            # Round 2: derived TRANSLATION layers (e.g. the Deshika English
            # side) stay out of the training corpus by policy - the English
            # text is still retrievable in RAG, but never conditions training.
            if (not include_translations_in_training
                    and unit.text_role == "TRANSLATION"):
                products.discard(CORPUS_TRAINING)
            if flags & rag_flags:
                products.discard(CORPUS_RAG)

            if not products:
                diversion_chars += len(text)
                for flag in sorted(flags) or ["UNSPECIFIED"]:
                    diversion_counts[flag] = diversion_counts.get(flag, 0) + 1
                record = build_record(
                    unit, source, gate,
                    artifact_sha256=artifact.get("sha256", ""),
                    acquisition_timestamp=timestamp,
                    pipeline_version=PIPELINE_VERSION,
                )
                record["work_role"] = ("TRANSLATION" if unit.text_role == "TRANSLATION"
                                       else "ORIGINAL")
                record["diversion"] = {
                    "reason_flags": sorted(flags),
                    "reason": "unit failed the release quality floor; held for "
                              "review rather than released or discarded",
                    "min_unit_chars": min_unit_chars,
                    "training_floor_flags": sorted(training_flags),
                    "rag_floor_flags": sorted(rag_flags),
                }
                diverted.write(record)
                continue

            record = build_record(
                unit, source, gate,
                artifact_sha256=artifact.get("sha256", ""),
                acquisition_timestamp=timestamp,
                pipeline_version=PIPELINE_VERSION,
            )
            record["work_role"] = ("TRANSLATION" if unit.text_role == "TRANSLATION"
                                   else "ORIGINAL")
            for product in (CORPUS_RAG, CORPUS_TRAINING):
                if product in products and writers[product].write(record):
                    written_counts[product] += 1

        entry["units_released"] = written_counts[CORPUS_RAG]
        entry["units_in_training"] = written_counts[CORPUS_TRAINING]
        entry["units_skipped_as_duplicate"] = skipped_dup
        entry["units_diverted_for_quality"] = len(units) - skipped_dup - max(
            written_counts[CORPUS_RAG], written_counts[CORPUS_TRAINING])
        entry["metadata_completeness"] = metadata_completeness(source.as_row())
        entry["provenance_completeness"] = provenance_completeness(
            {"provenance": {"source_url": source.get("source_url", ""),
                            "artifact_sha256": artifact.get("sha256", ""),
                            "repository": source.get("repository", ""),
                            "identifier": source.get("acquisition_identifier", ""),
                            "license_evidence_url": source.get("license_evidence_url", ""),
                            "acquisition_timestamp": timestamp}}
        )
        per_source[source_id] = entry
        print(f"  {source_id:<12} rag={written_counts[CORPUS_RAG]:>6} "
              f"train={written_counts[CORPUS_TRAINING]:>6} "
              f"dups_skipped={skipped_dup:<5} {sorted(admission.corpora)}")

    for product, writer in writers.items():
        closed = writer.close()
        stats[product] = {
            "written": closed.written,
            "skipped_validation": closed.skipped_validation,
            "skipped_empty": closed.skipped_empty,
            "bytes": closed.bytes,
            "sha256": closed.sha256,
            "filename": (RAG_FILENAME if product == CORPUS_RAG else TRAINING_FILENAME),
            "problems": writer.problems[:50],
            "problem_count": len(writer.problems),
        }
    diverted_stats = diverted.close()
    diversion = {
        "written": diverted_stats.written,
        "bytes": diverted_stats.bytes,
        "sha256": diverted_stats.sha256,
        "characters_withheld": diversion_chars,
        "by_flag": dict(sorted(diversion_counts.items(), key=lambda kv: -kv[1])),
        "min_unit_chars": min_unit_chars,
        "training_floor_flags": sorted(training_flags),
        "rag_floor_flags": sorted(rag_flags),
        "note": "these units are withheld from both products, not deleted; they are "
                "the human review queue for OCR and segmentation quality",
    }

    write_excluded(out_dir / EXCLUDED_FILENAME, excluded)
    manifest = {
        "corpus_version": config.get("project", "corpus_version", "svk-corpus-v0.1"),
        "pipeline_version": PIPELINE_VERSION,
        "generated_at": _now(),
        "products": {
            RAG_FILENAME: stats[CORPUS_RAG],
            TRAINING_FILENAME: stats[CORPUS_TRAINING],
            EXCLUDED_FILENAME: {"sources": len(excluded)},
            diverted_name: diversion,
        },
        "sources_released": sum(1 for e in per_source.values() if e.get("units_released")),
        "per_source": per_source,
    }
    write_release_manifest(out_dir / RELEASE_MANIFEST, manifest)
    _write_json(config.manifests_dir / "corpus_manifest.json", manifest)
    print(f"release: rag={stats[CORPUS_RAG]['written']} training="
          f"{stats[CORPUS_TRAINING]['written']} "
          f"withheld_for_quality={diverted_stats.written} "
          f"excluded_sources={len(excluded)}")
    print(f"  withheld flags: {diversion['by_flag']}")
    identical = stats[CORPUS_RAG]["sha256"] == stats[CORPUS_TRAINING]["sha256"]
    if identical:
        print("  NOTE: the RAG and training products are currently byte-identical "
              "(every admitted source is training-eligible). They are still "
              "written separately because they diverge as soon as a "
              "retrieval-only source is admitted.")
    return 0


def _rehydrate_unit(row: dict):
    from svk_corpus.schemas.records import TextUnit
    return TextUnit(
        unit_id=row["unit_id"],
        source_id=row["source_id"],
        parent_id=row.get("parent_id", ""),
        unit_type=row.get("unit_type", "paragraph"),
        text=row.get("text", ""),
        normalized_text=row.get("normalized_text", ""),
        language=row.get("language", "unknown"),
        script=row.get("script", "unknown"),
        page=row.get("page"),
        section=row.get("section"),
        source_locator=row.get("source_locator") or {},
        text_role=row.get("text_role", "ORIGINAL"),
        structure_confidence=row.get("structure_confidence", "unknown"),
        detected_label=row.get("detected_label"),
        provenance=row.get("provenance") or {},
        quality={},
    )


# ===========================================================================
# tokens / stats
# ===========================================================================
def _release_records(config: Config) -> dict[str, list[dict]]:
    out_dir = config.path("paths", "release")
    return {
        product: _read_jsonl(out_dir / filename)
        for product, filename in ((CORPUS_RAG, RAG_FILENAME),
                                  (CORPUS_TRAINING, TRAINING_FILENAME))
    }


def measure_release(config: Config) -> dict[str, Any]:
    """Measure the released corpora against the real candidate tokenizers."""
    fetched = fetch_tokenizers(config)
    registry = TokenizerRegistry.from_config(config)
    records = _release_records(config)

    payload: dict[str, Any] = {
        "generated_at": _now(),
        "tokenizer_fetch": fetched,
        "products": {},
        "primary_tokenizer": registry.primary,
    }
    for product, rows in records.items():
        groups: dict[str, dict[str, dict[str, int]]] = {}
        totals = {name: 0 for name in registry.names}
        characters = words = 0
        for row in rows:
            text = row.get("normalized_text") or row.get("text") or ""
            characters += len(text)
            words += len(text.split())
            # Characters/words are properties of the text, not of any tokenizer,
            # so they are accumulated once per row — not once per tokenizer.
            # (Previously this block sat inside the tokenizer loop, inflating
            # every by_group character/word total by len(registry.names).)
            for grouping in ("language", "script", "sect", "text_role", "source_id"):
                value = str(row.get(grouping) or "unknown")
                groups.setdefault(grouping, {}).setdefault(
                    value, {"characters": 0, "words": 0, **{n: 0 for n in registry.names}})
                bucket = groups[grouping][value]
                bucket["characters"] += len(text)
                bucket["words"] += len(text.split())
            for name in registry.names:
                count = len(registry.tokenizers[name].encode(text))
                totals[name] += count
                for grouping in ("language", "script", "sect", "text_role", "source_id"):
                    groups[grouping][str(row.get(grouping) or "unknown")][name] += count
        payload["products"][product] = {
            "records": len(rows),
            "characters": characters,
            "words": words,
            "tokens": totals,
            "tokens_per_character": {
                n: round(t / characters, 4) if characters else 0.0
                for n, t in totals.items()
            },
            "tokens_per_word": {
                n: round(t / words, 4) if words else 0.0 for n, t in totals.items()
            },
            "by_group": groups,
        }
    payload["tokenizers"] = registry.describe()
    payload["tokenizers_roundtrip_verified"] = registry.verified_names

    # The CPT verdict must name a tokenizer whose encoder actually passed its
    # round-trip check, otherwise the number is unverified.
    instrument = registry.primary if registry.primary in registry.verified_names else ""
    if not instrument and registry.verified_names:
        instrument = registry.verified_names[0]
    payload["primary_tokenizer"] = instrument
    payload["primary_tokenizer_verified"] = bool(
        instrument and registry.tokenizers[instrument].roundtrip_verified
    )
    if not instrument:
        payload["cpt"] = {
            "CPT_ELIGIBLE": "UNKNOWN",
            "clean_training_tokens": 0,
            "project_threshold": int(config.get("cpt", "token_threshold", 50_000_000)),
            "ratio_of_threshold": 0.0,
            "caveats": [
                "no candidate tokenizer could be loaded and verified in this "
                "environment, so no token count is reported. A count from an "
                "unverified encoder would be worse than no count.",
            ],
        }
        write_measurements(config.reports_dir / "tokenizer_measurements.json", payload)
        return payload

    training_tokens = payload["products"].get(CORPUS_TRAINING, {}).get(
        "tokens", {}).get(instrument, 0)
    payload["cpt"] = cpt_eligibility(
        training_tokens, int(config.get("cpt", "token_threshold", 50_000_000))
    )
    payload["cpt"]["tokenizer"] = instrument
    write_measurements(config.reports_dir / "tokenizer_measurements.json", payload)
    return payload


def cmd_tokens(config: Config) -> int:
    payload = measure_release(config)
    print("tokenizer measurements (released corpora):")
    for product, data in payload["products"].items():
        print(f"  {product}: {data['records']} records, {data['characters']} chars")
        for name, count in sorted(data["tokens"].items()):
            ratio = data["tokens_per_character"][name]
            verified = "verified" if name in payload.get("tokenizers_roundtrip_verified", []) \
                else "UNVERIFIED"
            print(f"    {name:<24} {count:>9} tokens  {ratio:>6} tok/char  [{verified}]")
    for entry in payload["tokenizer_fetch"]:
        if entry["status"] != "OK":
            print(f"    UNAVAILABLE {entry['name']}: {entry['error']}")
    return 0


def _load_fresh_measurements(path: Path, release_paths: Sequence[Path]) -> dict | None:
    """Return cached tokenizer measurements if they postdate the release files.

    The full measurement pass costs ~20 minutes for this corpus (six tokenizers
    over ~97K records), and the `tokens` stage already wrote the result. `stats`
    must not silently repeat that work — but it also must not reuse numbers that
    predate the release they describe. Freshness is decided by mtime comparison:
    the measurement file must exist, parse, and be newer than every release file.
    """
    if not path.is_file():
        return None
    mtimes = [p.stat().st_mtime for p in release_paths if p.is_file()]
    if not mtimes or path.stat().st_mtime < max(mtimes):
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) and "products" in payload else None


def cmd_stats(config: Config) -> int:
    from svk_corpus.reports import write_statistics, write_ingest_report

    release_dir = config.path("paths", "release")
    measurements_path = config.reports_dir / "tokenizer_measurements.json"
    cached = _load_fresh_measurements(
        measurements_path,
        (release_dir / RAG_FILENAME, release_dir / TRAINING_FILENAME),
    )
    if cached is not None:
        measurements = cached
        print("stats: reusing tokenizer_measurements.json "
              "(release unchanged since the tokens stage)")
    else:
        measurements = measure_release(config)
    payload = write_statistics(config, measurements)
    _write_json(config.reports_dir / "corpus_statistics.json", payload)
    write_ingest_report(config, payload, measurements)
    print(f"stats: wrote corpus_statistics.md, INGEST_REPORT.md, "
          f"tokenizer_measurements.json")
    return 0


# ===========================================================================
# validate
# ===========================================================================
def cmd_validate(config: Config) -> int:
    from svk_corpus.schemas.records import validate_release_record

    out_dir = config.path("paths", "release")
    problems: list[str] = []
    checked = 0
    for filename in (RAG_FILENAME, TRAINING_FILENAME):
        path = out_dir / filename
        if not path.is_file():
            problems.append(f"missing release product: {filename}")
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            checked += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                problems.append(f"{filename}:{line_number}: invalid JSON: {exc}")
                continue
            for problem in validate_release_record(record):
                problems.append(f"{filename}:{line_number} ({record.get('id')}): {problem}")
            if not record.get("provenance", {}).get("source_url"):
                problems.append(f"{filename}:{line_number}: provenance lacks source_url")
            if not record.get("license", {}).get("status"):
                problems.append(f"{filename}:{line_number}: license lacks status")
            if record.get("license", {}).get("status") in (
                    GateState.NEEDS_PERMISSION.value, GateState.NOT_ALLOWED.value,
                    GateState.UNKNOWN.value):
                problems.append(
                    f"{filename}:{line_number}: a {record['license']['status']} source "
                    f"reached the release; this is a gate violation"
                )
    print(f"validate: {checked} records checked, {len(problems)} problems")
    for problem in problems[:40]:
        print(f"  - {problem}")
    _write_json(config.reports_dir / "validation.json",
                {"generated_at": _now(), "records_checked": checked,
                 "problems": problems})
    return 1 if problems else 0


# ===========================================================================
# dispatch
# ===========================================================================
_REPOSITORY_ALIASES = {
    "": "",
    "internetarchive": "internetarchive",
    "ia": "internetarchive",
    "archiveorg": "internetarchive",
    "huggingface": "huggingface",
    "hf": "huggingface",
    "github": "github",
}


def _normalise_repository(raw: str) -> str:
    key = (raw or "").strip().lower()
    for ch in ("_", "-", " ", "."):
        key = key.replace(ch, "")
    return _REPOSITORY_ALIASES.get(key, key)


COMMANDS = {
    "check": cmd_check,
    "manifest": cmd_manifest,
    "gate": cmd_gate,
    "acquire": cmd_acquire,
    "extract": cmd_extract,
    "normalize": cmd_normalize,
    "segment": cmd_segment,
    "dedupe": cmd_dedupe,
    "quality": cmd_quality,
    "tokens": cmd_tokens,
    "release": cmd_release,
    "stats": cmd_stats,
    "validate": cmd_validate,
}

# Order matters: `release` must precede `tokens`/`stats`, because measurement is
# performed on the RELEASED records, not on intermediate layers.
ALL_ORDER = ("manifest", "gate", "acquire", "extract", "normalize", "segment",
             "dedupe", "quality", "release", "tokens", "stats", "validate")


def run(command: str, config: Config | None = None) -> int:
    config = config or load_config()
    config.ensure_dirs()
    if command == "all":
        worst = 0
        for name in ALL_ORDER:
            print(f"\n=== {name} ===")
            worst = max(worst, run(name, config))
        return worst
    handler = COMMANDS.get(command)
    if handler is None:
        print(f"unknown command: {command}\navailable: {sorted(COMMANDS)} or all")
        return 2
    return handler(config)
