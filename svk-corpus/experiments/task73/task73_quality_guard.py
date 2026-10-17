"""TASK 73 Phase 3 — query-variant quality guard.

Reads the raw generation output downloaded from Colab and produces the
finalized expansion file data/evaluation/task73_query_expansions.jsonl.

Decisions combine:
  1. automated checks recorded per variant (empty, length, content-term
     overlap with the original, script/language drift, verbatim copy),
  2. the manual review of ALL 141 variants against the guard rules
     (answers the question / invents facts / changes sect or entity /
     removes a critical religious term / unrelated / unsupported source
     claim). The manual decisions are encoded in MANUAL_INVALID below.

INVALID variants are retained in the output with a reason (recorded, never
silently dropped) and must be excluded from the retrieval union by the
experiment script.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

RAW = Path("/tmp/opencode/task73_query_expansions_raw.jsonl")
META = Path("/tmp/opencode/task73_expansion_run_metadata.json")
OUT = Path("data/evaluation/task73_query_expansions.jsonl")

# Manual review decisions: {example_id: {variant_index: reason}}
# Reviewed 2026-10-04 against all guard rules. Everything not listed here
# was judged VALID (faithful lexical reformulation, no answers, entities,
# sects, and critical terms preserved, language preserved).
MANUAL_INVALID: dict[str, dict[int, str]] = {
    "DAPT01EVAL-009": {3: "truncated_at_cap"},
    "DAPT01EVAL-010": {3: "truncated_at_cap"},
    "DAPT01EVAL-011": {3: "truncated_at_cap"},
    "DAPT01EVAL-013": {2: "truncated_at_cap", 3: "empty_after_truncation"},
    "DAPT01EVAL-016": {3: "truncated_at_cap"},
    "DAPT01EVAL-017": {3: "truncated_at_cap"},
    "DAPT01EVAL-018": {3: "truncated_at_cap"},
    "DAPT01EVAL-019": {3: "truncated_at_cap"},
    "DAPT01EVAL-020": {2: "truncated_at_cap", 3: "empty_after_truncation"},
    "DAPT01EVAL-045": {
        1: "truncated_at_cap",
        2: "empty_after_truncation",
        3: "empty_after_truncation",
    },
}

SCRIPT_PATTERNS = {
    "latin": re.compile(r"[A-Za-z]"),
    "devanagari": re.compile(r"[ऀ-ॿ]"),
    "gujarati": re.compile(r"[઀-૿]"),
}


def scripts_of(text: str) -> set[str]:
    out = set()
    for name, pat in SCRIPT_PATTERNS.items():
        if pat.search(text):
            out.add(name)
    return out


def tokens(text: str) -> set[str]:
    # NOTE: Python's \W splits Indic words at every matra (Mc/Mn are not
    # word chars), so build the tokenizer from explicit script ranges
    # (Latin, Devanagari, Gujarati) instead of \w.
    t = re.sub(r"[^0-9A-Za-zऀ-ॿ઀-૿\s]+", " ", text.casefold())
    return {x for x in t.split() if len(x) >= 3}


def overlap(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta:
        return 0.0
    return round(len(ta & tb) / len(ta), 3)


def quoted_and_terms(orig: str) -> set[str]:
    """Critical terms: quoted spans + capitalized multiword spans (latin) +
    Devanagari/Gujarati quoted terms."""
    terms = set(re.findall(r"'([^']+)'", orig))
    terms |= set(re.findall(r"\"([^\"]+)\"", orig))
    for t in re.findall(r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\b", orig):
        if t.lower() not in {"the", "of", "in", "who", "what", "and", "for", "a"}:
            terms.add(t)
    return terms


def main() -> None:
    rows = [json.loads(ln) for ln in RAW.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(rows) == 47, f"expected 47 rows, got {len(rows)}"
    meta = json.loads(META.read_text(encoding="utf-8"))

    out_rows = []
    stats = {"total_slots": 0, "valid": 0, "invalid": 0, "invalid_reasons": {}}
    per_case_notes = []

    for r in rows:
        eid = r["example_id"]
        orig = r["original_query"]
        orig_scripts = scripts_of(orig)
        orig_terms = quoted_and_terms(orig)
        inv_map = MANUAL_INVALID.get(eid, {})
        row = {
            "example_id": eid,
            "original_query": orig,
            "model": r["model"],
            "seed": r["seed"],
            "decoding": r["decoding"],
            "max_new_tokens": r["max_new_tokens"],
            "prompt_sha256": r["prompt_sha256"],
            "cap_hit": r["new_tokens"] >= r["max_new_tokens"],
        }
        n_valid = 0
        notes = []
        for i in (1, 2, 3):
            v = r[f"variant_{i}"].strip()
            stats["total_slots"] += 1
            checks = {
                "empty": v == "",
                "verbatim_original": v == orig,
                "min_len_ok": len(v) >= 3,
                "content_overlap": overlap(orig, v) if v else 0.0,
                "script_set": sorted(scripts_of(v)) if v else [],
                "script_drift": bool(v) and not (scripts_of(v) & orig_scripts),
                "terms_missing": sorted(
                    t for t in orig_terms
                    if t.casefold() not in v.casefold()
                ) if v else sorted(orig_terms),
            }
            if i in inv_map:
                valid, reason = False, inv_map[i]
            elif not v:
                valid, reason = False, "empty"
            elif checks["script_drift"]:
                valid, reason = False, "script_drift"
            else:
                # Manual review of all 141 variants is authoritative; the
                # overlap metric is recorded as a flag only (paraphrases of
                # short queries can legitimately overlap < 0.34).
                valid, reason = True, None
            checks["low_content_overlap_flag"] = checks["content_overlap"] < 0.34
            if valid:
                n_valid += 1
                stats["valid"] += 1
            else:
                stats["invalid"] += 1
                key = reason.split(":")[0]
                stats["invalid_reasons"][key] = stats["invalid_reasons"].get(key, 0) + 1
                notes.append(f"v{i}={reason}")
            row[f"variant_{i}"] = v
            row[f"variant_{i}_valid"] = valid
            row[f"variant_{i}_invalid_reason"] = reason
            row[f"variant_{i}_checks"] = checks
        row["n_valid_variants"] = n_valid
        if notes:
            per_case_notes.append(f"{eid}: {', '.join(notes)}")
        out_rows.append(row)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out_rows),
        encoding="utf-8",
    )
    sha = hashlib.sha256(OUT.read_bytes()).hexdigest()

    print(f"PHASE3_QUALITY_GUARD_DONE -> {OUT}")
    print(f"sha256 {sha}")
    print(
        f"cases=47 slots={stats['total_slots']} valid={stats['valid']} "
        f"invalid={stats['invalid']} reasons={stats['invalid_reasons']}"
    )
    print(f"cases_with_any_invalid ({len(per_case_notes)}):")
    for n in per_case_notes:
        print(f"  {n}")
    zero = [r["example_id"] for r in out_rows if r["n_valid_variants"] == 0]
    print(f"cases with ZERO valid variants: {zero}")
    # machine-readable tail for the experiment/report phases
    print(
        "RESULT_JSON::"
        + json.dumps(
            {
                "phase": 3,
                "input_raw_sha": hashlib.sha256(RAW.read_bytes()).hexdigest(),
                "output": str(OUT),
                "output_sha": sha,
                "n_cases": 47,
                "slots_total": stats["total_slots"],
                "slots_valid": stats["valid"],
                "slots_invalid": stats["invalid"],
                "invalid_reasons": stats["invalid_reasons"],
                "cases_zero_valid": zero,
                "run_metadata": meta,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
