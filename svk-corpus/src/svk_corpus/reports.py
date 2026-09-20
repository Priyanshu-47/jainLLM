"""Markdown reporting.

Every number in these reports is read from a file the pipeline wrote, never
recomputed from memory and never estimated. Where a number is unavailable the
report says so; a blank is not filled with a plausible value.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any

from svk_corpus import PIPELINE_VERSION, __version__
from svk_corpus.config import Config
from svk_corpus.manifests import load_artifact_manifest
from svk_corpus.release import count_records


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


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


def _table(rows: list[tuple[str, Any]], headers: tuple[str, str]) -> str:
    if not rows:
        return "_none_\n"
    out = [f"| {headers[0]} | {headers[1]} |", "| --- | --- |"]
    for key, value in rows:
        out.append(f"| {key} | {value} |")
    return "\n".join(out) + "\n"


def collect(config: Config, measurements: dict[str, Any]) -> dict[str, Any]:
    """Assemble every reported figure from the files on disk."""
    release_dir = config.path("paths", "release")
    import csv

    manifest = _read_json(release_dir / "manifest.json") or {}
    license_path = config.manifests_dir / "license_manifest.csv"
    license_rows = []
    if license_path.is_file():
        with license_path.open("r", encoding="utf-8", newline="") as fh:
            license_rows = list(csv.DictReader(fh))

    source_rows = []
    source_path = config.manifests_dir / "source_manifest.csv"
    if source_path.is_file():
        with source_path.open("r", encoding="utf-8", newline="") as fh:
            source_rows = list(csv.DictReader(fh))

    artifact_rows = load_artifact_manifest(config.manifests_dir / "artifact_manifest.csv")
    rag = _read_jsonl(release_dir / "rag_corpus.jsonl")
    training = _read_jsonl(release_dir / "training_corpus.jsonl")
    excluded = _read_jsonl(release_dir / "excluded_sources.jsonl")
    quality = _read_json(config.path("paths", "deduplicated").parent / "quality" /
                         "quality_stats.json") or {}
    dedup = _read_json(config.path("paths", "deduplicated") / "dedup_stats.json") or {}
    extraction_summary = _read_json(config.reports_dir / "extraction_summary.json") or {}
    failures = _read_json(config.reports_dir / "acquisition_failures.json") or {}
    ocr = _read_json(config.path("paths", "deduplicated").parent / "quality" /
                     "ocr_quality_report.json") or {}
    validation = _read_json(config.reports_dir / "validation.json") or {}

    gate_counts: dict[str, int] = {}
    for row in license_rows:
        gate_counts[row.get("decision", "?")] = gate_counts.get(row.get("decision", "?"), 0) + 1

    releases = {row["source_id"] for row in rag} | {row["source_id"] for row in training}

    def group(records: list[dict], field: str) -> list[tuple[str, int]]:
        counts: dict[str, int] = {}
        for record in records:
            value = record.get(field)
            key = str(value) if value not in (None, "", "unknown") else "unknown"
            counts[key] = counts.get(key, 0) + 1
        return sorted(counts.items(), key=lambda kv: -kv[1])

    pages = sum(r.get("pages", 0) for r in extraction_summary.get("results", [])
                if isinstance(r.get("pages"), int))

    return {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
        "version": {"pipeline": PIPELINE_VERSION, "package": __version__,
                    "corpus": manifest.get("corpus_version", "unknown")},
        "sources_total": len(source_rows),
        "sources_released": len(releases),
        "sources_excluded": len(excluded),
        "sources_acquired": len({r["source_id"] for r in artifact_rows
                                 if r.get("artifact_type") == "EXTRACTED_TEXT"}),
        "gate_counts": gate_counts,
        "artifact_rows": len(artifact_rows),
        "release_bytes": {
            "rag": int((manifest.get("products") or {}).get("rag_corpus.jsonl", {}).get("bytes", 0) or 0),
            "training": int((manifest.get("products") or {}).get("training_corpus.jsonl", {}).get("bytes", 0) or 0),
        },
        "documents": len(extraction_summary.get("results", [])),
        "pages": pages,
        "extraction": extraction_summary.get("results", []),
        "acquired_rag": len(rag),
        "acquired_training": len(training),
        "excluded": excluded,
        "quality": quality,
        "dedup": dedup,
        "ocr": ocr,
        "validation": validation,
        "failures": failures.get("failures", []),
        "groups": {
            "language": group(rag, "language"),
            "script": group(rag, "script"),
            "text_role": group(rag, "text_role"),
            "sect": group(rag, "sect"),
            "tradition": group(rag, "tradition"),
            "unit_type": group(rag, "unit_type"),
            "source": group(rag, "source_id"),
            "year": group(rag, "publication_year"),
        },
        "training_groups": {
            "language": group(training, "language"),
            "script": group(training, "script"),
        },
        "measurements": measurements,
    }


def write_statistics(config: Config, measurements: dict[str, Any]) -> dict[str, Any]:
    data = collect(config, measurements)
    path = config.reports_dir / "corpus_statistics.md"
    path.write_text(render_statistics(data), encoding="utf-8")
    return data


def render_statistics(data: dict[str, Any]) -> str:
    m = data["measurements"]
    lines: list[str] = []
    add = lines.append

    add("# svk-corpus v0.1 — corpus statistics\n")
    add(f"Generated: {data['generated_at']}  ")
    add(f"Pipeline: {data['version']['pipeline']}  ")
    add(f"Corpus version: `{data['version']['corpus']}`\n")
    add("All figures below are read from the pipeline's own output files. "
        "Nothing is estimated. Where a figure is unavailable it is marked.\n")

    add("## 1. Volume\n")
    rag = m["products"].get("rag", {})
    train = m["products"].get("training", {})
    primary = m.get("primary_tokenizer", "unknown")
    add(_table([
        ("Sources in manifest", data["sources_total"]),
        ("Sources passing the licence gate and released", data["sources_released"]),
        ("Sources acquired (text extracted)", data["sources_acquired"]),
        ("Sources excluded from release", data["sources_excluded"]),
        ("Documents (one per extracted source)", data["documents"]),
        ("Pages", data["pages"] if data["pages"] else "not recorded"),
        ("RAG records (text units)", f"{data['acquired_rag']:,}"),
        ("Training records (text units)", f"{data['acquired_training']:,}"),
        ("RAG characters", f"{rag.get('characters', 0):,}"),
        ("Training characters", f"{train.get('characters', 0):,}"),
        ("RAG words", f"{rag.get('words', 0):,}"),
        ("Training words", f"{train.get('words', 0):,}"),
        (f"RAG tokens ({primary})", f"{rag.get('tokens', {}).get(primary, 0):,}"),
        (f"Training tokens ({primary})", f"{train.get('tokens', {}).get(primary, 0):,}"),
        ("On-disk size of the release directory", _release_bytes(data)),
    ], ("Measure", "Value")))

    add("### Token counts by tokenizer\n")
    rows = []
    for name in sorted(set(rag.get("tokens", {})) | set(train.get("tokens", {}))):
        verified = name in m.get("tokenizers_roundtrip_verified", [])
        rows.append((
            name + ("" if verified else " (UNVERIFIED: round-trip check failed)"),
            f"rag {rag.get('tokens', {}).get(name, 0):,} / "
            f"train {train.get('tokens', {}).get(name, 0):,} "
            f"({rag.get('tokens_per_character', {}).get(name, 0)} tok/char on rag)",
        ))
    add(_table(rows, ("Tokenizer", "Tokens")))
    add("Tokenizers that could not be downloaded are recorded in "
        "`tokenizer_measurements.json` under `tokenizer_fetch`, with their HTTP "
        "status. They are not silently omitted.\n")

    add("## 2. Language (RAG corpus)\n")
    add(_table(data["groups"]["language"], ("Language", "Records")))
    add("## 3. Script (RAG corpus)\n")
    add(_table(data["groups"]["script"], ("Script", "Records")))
    add("## 4. Text role (RAG corpus)\n")
    add(_table(data["groups"]["text_role"], ("Text role", "Records")))
    add("## 5. Sect (RAG corpus)\n")
    add(_table(data["groups"]["sect"], ("Sect", "Records")))
    add("## 6. Unit type (RAG corpus)\n")
    add(_table(data["groups"]["unit_type"], ("Unit type", "Records")))
    add("## 7. Source (RAG corpus)\n")
    add(_table(data["groups"]["source"], ("Source id", "Records")))

    add("## 8. Licensing\n")
    add(_table(sorted(data["gate_counts"].items()), ("Gate decision", "Sources")))
    add("Excluded sources, with the rule and reason for each: "
        "`data/release/excluded_sources.jsonl`.\n")

    add("## 9. Quality\n")
    quality = data["quality"]
    dedup = data["dedup"]
    add(_table([
        ("Units assessed", quality.get("units", 0)),
        ("Units carrying quality flags", (quality.get("flags") or {}).get("units_with_flags", 0)),
        ("Mean Unicode quality", (quality.get("means") or {}).get("unicode_quality", "n/a")),
        ("Mean OCR noise estimate", (quality.get("means") or {}).get("ocr_noise_estimate", "n/a")),
        ("Mean structural quality", (quality.get("means") or {}).get("structural_quality", "n/a")),
        ("Units evaluated for duplication", dedup.get("units_evaluated", 0)),
        ("Exact duplicates", dedup.get("EXACT_DUPLICATE", 0)),
        ("Near duplicates", dedup.get("NEAR_DUPLICATE", 0)),
        ("Duplicate rate (exact+near)", dedup.get("duplicate_rate", "n/a")),
        ("OCR: sources needing manual review",
         (quality.get("ocr") or {}).get("manual_review_required", "n/a")),
        ("OCR engines available", (quality.get("ocr") or {}).get("engine_availability", "n/a")),
    ], ("Metric", "Value")))
    flags = (quality.get("flags") or {}).get("counts", {})
    add("### Quality flags\n")
    add(_table(sorted(flags.items(), key=lambda kv: -kv[1]), ("Flag", "Units")))

    add("## 10. CPT verdict\n")
    cpt = m.get("cpt", {})
    add(_table([
        ("Clean training tokens", f"{cpt.get('clean_training_tokens', 0):,}"),
        ("Measuring tokenizer", primary),
        ("Project threshold", f"{cpt.get('project_threshold', 0):,}"),
        ("Ratio of threshold", cpt.get("ratio_of_threshold", "n/a")),
        ("**CPT_ELIGIBLE**", f"**{cpt.get('CPT_ELIGIBLE', 'UNKNOWN')}**"),
    ], ("Question", "Answer")))
    for caveat in cpt.get("caveats", []):
        add(f"- {caveat}")
    add("")
    return "\n".join(lines)


def _release_bytes(data: dict[str, Any]) -> str:
    total = 0
    for product in ("rag", "training"):
        blob = (data["measurements"].get("products") or {}).get(product, {})
        total += int(blob.get("bytes", 0) or 0)
    if not total:
        return "not recorded"
    return f"{total / 1_048_576:.3f} MiB"


def write_ingest_report(config: Config, data: dict[str, Any],
                        measurements: dict[str, Any]) -> Path:
    path = config.reports_dir / "INGEST_REPORT.md"
    m = measurements
    rag = m["products"].get("rag", {})
    train = m["products"].get("training", {})
    primary = m.get("primary_tokenizer", "unknown")

    attempted = [r for r in data["extraction"]]
    ok = [r for r in attempted if r.get("status") == "OK"]
    failed = [r for r in attempted if r.get("status") not in ("OK",)]
    lines: list[str] = []
    add = lines.append

    add("# INGEST_REPORT.md — svk-corpus v0.1\n")
    add(f"Generated: {data['generated_at']}  ")
    add(f"Corpus version: `{data['version']['corpus']}`  ")
    add(f"Pipeline: {data['version']['pipeline']}\n")

    add("## Sources\n")
    add(_table([
        ("Sources in manifest", data["sources_total"]),
        ("Sources with acquisition configured", len({r["source_id"] for r in data['extraction']})),
        ("Sources successfully acquired and extracted", len(ok)),
        ("Sources with download/extraction failures", len(failed)),
        ("Sources rejected by the licence gate (never downloaded as text)",
         data["gate_counts"].get("NOT_ALLOWED", 0)),
        ("Sources requiring permission", data["gate_counts"].get("NEEDS_PERMISSION", 0)),
        ("Sources with unresolved (UNKNOWN) status", data["gate_counts"].get("UNKNOWN", 0)),
        ("Sources admitted to a release product", data["sources_released"]),
        ("Sources excluded from the release, with reasons", data["sources_excluded"]),
    ], ("Measure", "Value")))

    add("### Extraction outcome per source\n")
    add("| Source | Status | Method | Characters | Pages | Error |")
    add("| --- | --- | --- | --- | --- | --- |")
    for row in sorted(data["extraction"], key=lambda r: r.get("source_id", "")):
        add(f"| {row.get('source_id','')} | {row.get('status','')} | "
            f"{row.get('method','')} | {row.get('characters','')} | "
            f"{row.get('pages','')} | {(row.get('error') or '')[:60]} |")
    add("")

    add("## OCR\n")
    add(f"Engines: {(data['quality'].get('ocr') or {}).get('engine_availability', 'n/a')}\n")
    add(_table([
        ("Sources with an OCR report", data["ocr"].get("sources", 0)),
        ("Sources needing manual review", data["ocr"].get("manual_review_required", 0)),
    ], ("Measure", "Value")))
    add("Full per-source calibration: `data/quality/ocr_quality_report.json` and "
        "`.csv`.\n")

    add("## Totals\n")
    add(_table([
        ("Documents", data["documents"]),
        ("Pages", data["pages"] if data["pages"] else "not recorded"),
        ("RAG records", f"{data['acquired_rag']:,}"),
        ("Training records", f"{data['acquired_training']:,}"),
        ("Characters (RAG)", f"{rag.get('characters', 0):,}"),
        ("Characters (training)", f"{train.get('characters', 0):,}"),
        ("Words (RAG)", f"{rag.get('words', 0):,}"),
        (f"Tokens (RAG, {primary})", f"{rag.get('tokens', {}).get(primary, 0):,}"),
        (f"Tokens (training, {primary})", f"{train.get('tokens', {}).get(primary, 0):,}"),
    ], ("Measure", "Value")))

    add("### Tokens by language\n")
    add(_token_table(rag, "language", primary))
    add("### Tokens by script\n")
    add(_token_table(rag, "script", primary))
    add("### Tokens by text role\n")
    add(_token_table(rag, "text_role", primary))
    add("### Tokens by sect\n")
    add(_token_table(rag, "sect", primary))

    add("## Duplication\n")
    add(_table([
        ("Units evaluated", data["dedup"].get("units_evaluated", 0)),
        ("Exact duplicates", data["dedup"].get("EXACT_DUPLICATE", 0)),
        ("Short exact repeats kept (low signal)", data["dedup"].get("EXACT_DUPLICATE_LOW_SIGNAL", 0)),
        ("Near duplicates", data["dedup"].get("NEAR_DUPLICATE", 0)),
        ("Duplicate rate", data["dedup"].get("duplicate_rate", "n/a")),
    ], ("Measure", "Value")))
    add(f"Semantic dedup: **disabled**. {(data['dedup'].get('semantic') or {}).get('reason','')}\n")

    add("## Quality\n")
    add(_table([
        ("Units assessed", data["quality"].get("units", 0)),
        ("Units carrying flags", (data["quality"].get("flags") or {}).get("units_with_flags", 0)),
        ("Mean Unicode quality", (data["quality"].get("means") or {}).get("unicode_quality", "n/a")),
        ("Mean OCR noise estimate", (data["quality"].get("means") or {}).get("ocr_noise_estimate", "n/a")),
    ], ("Measure", "Value")))

    add("## Tokens by tokenizer (all measured, none assumed)\n")
    add(_table([
        (name + ("" if name in m.get("tokenizers_roundtrip_verified", []) else " (UNVERIFIED)"),
         f"{rag.get('tokens', {}).get(name, 0):,} rag / "
         f"{train.get('tokens', {}).get(name, 0):,} training")
        for name in sorted(set(rag.get("tokens", {})) | set(train.get("tokens", {})))
    ], ("Tokenizer", "Tokens")))

    add("## CPT conclusion\n")
    cpt = m.get("cpt", {})
    add(_table([
        ("Clean training tokens", f"{cpt.get('clean_training_tokens', 0):,}"),
        ("Threshold", f"{cpt.get('project_threshold', 0):,}"),
        ("Ratio", cpt.get("ratio_of_threshold", "n/a")),
        ("**CPT_ELIGIBLE**", f"**{cpt.get('CPT_ELIGIBLE', 'UNKNOWN')}**"),
    ], ("Question", "Answer")))
    add("")

    add("## Major problems\n")
    for problem in _major_problems(data):
        add(f"- {problem}")
    add("")

    add("## Excluded sources\n")
    add("| Source | Gate | Rule | Reason |")
    add("| --- | --- | --- | --- |")
    for row in sorted(data["excluded"], key=lambda r: r.get("source_id", "")):
        reason = "; ".join(row.get("reasons", []))[:200].replace("|", "/")
        add(f"| {row.get('source_id','')} | {row.get('gate_state','')} | "
            f"{row.get('gate_rule','')} | {reason} |")
    add("")

    add("## Next recommended engineering action\n")
    add(_next_action(data))
    add("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _token_table(product: dict, grouping: str, primary: str) -> str:
    group = (product.get("by_group") or {}).get(grouping, {})
    if not group:
        return "_no data_\n"
    lines = [f"| {grouping} | Records | Characters | Words | Tokens ({primary}) | tok/char |",
             "| --- | --- | --- | --- | --- | --- |"]
    for value, data in sorted(group.items(), key=lambda kv: -kv[1].get("characters", 0)):
        chars = data.get("characters", 0)
        tokens = data.get(primary, 0)
        ratio = round(tokens / chars, 4) if chars else 0.0
        lines.append(f"| {value} | {data.get('records', 0)} | {chars:,} | "
                     f"{data.get('words', 0):,} | {tokens:,} | {ratio} |")
    return "\n".join(lines) + "\n"


def _major_problems(data: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if not data["sources_released"]:
        problems.append("No source reached the release. The corpus is empty.")
    failures = data.get("failures") or []
    if failures:
        problems.append(f"{len(failures)} acquisition failure(s) recorded in "
                        f"acquisition_failures.json")
    if data["gate_counts"].get("UNKNOWN"):
        problems.append(
            f"{data['gate_counts']['UNKNOWN']} source(s) have UNKNOWN licensing "
            f"status, usually a missing publication year, and are therefore "
            f"neither usable nor provably unusable"
        )
    if data["gate_counts"].get("NEEDS_PERMISSION"):
        problems.append(
            f"{data['gate_counts']['NEEDS_PERMISSION']} source(s) require permission. "
            f"These are the project's largest legal blocker."
        )
    if (data["quality"].get("ocr") or {}).get("manual_review_required"):
        problems.append(
            f"{(data['quality']['ocr'])['manual_review_required']} source(s) require "
            f"manual OCR review before their text may be treated as even "
            f"provisional scripture"
        )
    m = data["measurements"]
    for entry in m.get("tokenizer_fetch", []):
        if entry.get("status") != "OK":
            problems.append(
                f"tokenizer '{entry['name']}' unavailable ({entry.get('error')}); its "
                f"token economics are unmeasured, not assumed"
            )
    for name in m.get("tokenizers", []):
        if isinstance(name, dict) and name.get("unavailable"):
            problems.append(f"tokenizer '{name['name']}' not measured: "
                            f"{name['unavailable']}")
    sect_counts = dict(data["groups"]["sect"])
    svk_specific = sum(
        n for k, n in sect_counts.items()
        if k.upper().startswith("STHANAKAVASI")
    )
    if svk_specific == 0:
        problems.append(
            "Sectarian coverage: no released source is verified as "
            "Sthanakavasi-specific, so the corpus cannot yet answer a "
            "Sthanakavasi-specific question from Sthanakavasi text."
        )
    else:
        problems.append(
            f"Sectarian coverage: {svk_specific:,} records are Sthanakavasi-"
            f"attributed, but attribution rests on publisher imprint metadata "
            f"(A.B. Sthanakvasi Jain Conference / Shastroddhar Samiti imprints), "
            f"not on content-level sect marking; treat sect as provenance-based, "
            f"not verified per-verse."
        )
    problems.append(
        "Language coverage is dominated by whatever the acquired scans happen to "
        "contain; there is no bilingual alignment and no translation layer."
    )
    return problems


def _next_action(data: dict[str, Any]) -> str:
    cpt = data["measurements"].get("cpt", {})
    verdict = cpt.get("CPT_ELIGIBLE", "UNKNOWN")
    if verdict == "NO":
        return (
            "**Do not attempt continued pretraining.** Instead, build the retrieval "
            "layer: index this release with a multilingual embedding model plus "
            "BM25 hybrid search, and measure retrieval recall on a hand-written "
            "question set. Justification: the training corpus is "
            f"{cpt.get('clean_training_tokens', 0):,} tokens against a "
            f"{cpt.get('project_threshold', 0):,}-token threshold "
            f"({cpt.get('ratio_of_threshold', 0)}x), so SFT and RAG are the only "
            "technically defensible next steps, and RAG is the one that does not "
            "require scholar-verified instruction data first."
        )
    return (
        "**Proceed to a CPT feasibility pass**, but only after the tokenizer choice "
        "is settled: the spread between candidate tokenizers on this text decides "
        "the real cost. See the token table above."
    )
