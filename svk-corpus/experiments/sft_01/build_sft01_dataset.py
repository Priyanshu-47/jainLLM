#!/usr/bin/env python3
"""TASK 64 stage 1: build the SFT-01 train/eval dataset.

Inputs (read-only):
    data/training/sft_gold_v4_candidates.jsonl   54 Task-63 APPROVE candidates
    data/training/sft_reconciled_v1.jsonl         8 pre-existing HUMAN_VERIFIED rows
    data/evaluation/task62_reject_v1.jsonl        Task-63 REJECT decisions
    data/evaluation/task62_revise_v1.jsonl        Task-63 REVISE decisions
    data/training/sft_task62_review_queue_v1.jsonl example_id -> review_id map
    manifests/source_manifest.csv                 source metadata
    data/release/training_corpus.jsonl            unit texts (grounding for human rows)
    data/evaluation/dapt01_eval_cases.jsonl       frozen 47-case eval (overlap report only)

Outputs:
    data/training/sft_train_v1.jsonl              training split
    data/evaluation/sft_eval_v1.jsonl             held-out eval split (schema split=validation)
    data/reports/task64_sft01_build_stats.json    counts, exclusions, distributions, leakage

Conflict rule (documented in the Task 64 report):
    A row that is HUMAN_VERIFIED but whose identical record was adjudicated
    REJECT by Task 63 is EXCLUDED. The Task-63 "do not include REJECT"
    exclusion is an explicit hard rule; the prior human verification predates
    the evidence-grounding review. No decision is rewritten.

No row is ever created, rewritten or re-verified here: only mechanical schema
normalization, metadata verification, deterministic dedup and a deterministic
source-level split.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter, OrderedDict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
TASK61_DIR = os.path.join(ROOT, "experiments", "sft_curation", "task61")
if TASK61_DIR not in sys.path:
    sys.path.insert(0, TASK61_DIR)

from task61_common import (  # noqa: E402
    load_jainqq_evidence,
    load_manifest,
    load_rights_audit,
    map_knowledge_layer,
    map_religious_scope,
    rights_for,
)

GOLD_PATH = os.path.join(ROOT, "data", "training", "sft_gold_v4_candidates.jsonl")
HUMAN_PATH = os.path.join(ROOT, "data", "training", "sft_reconciled_v1.jsonl")
REJECT_PATH = os.path.join(ROOT, "data", "evaluation", "task62_reject_v1.jsonl")
REVISE_PATH = os.path.join(ROOT, "data", "evaluation", "task62_revise_v1.jsonl")
QUEUE_PATH = os.path.join(ROOT, "data", "training", "sft_task62_review_queue_v1.jsonl")
SCHEMA_PATH = os.path.join(ROOT, "data", "training", "sft_schema_v1.json")
CORPUS_PATH = os.path.join(ROOT, "data", "release", "training_corpus.jsonl")
FROZEN_EVAL_PATH = os.path.join(ROOT, "data", "evaluation", "dapt01_eval_cases.jsonl")

OUT_TRAIN = os.path.join(ROOT, "data", "training", "sft_train_v1.jsonl")
OUT_EVAL = os.path.join(ROOT, "data", "evaluation", "sft_eval_v1.jsonl")
OUT_STATS = os.path.join(ROOT, "data", "reports", "task64_sft01_build_stats.json")

SEED = 42
EVAL_FRACTION = 0.15
MIN_EVAL_ROWS = 6
FROZEN_EVAL_SHA256 = "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81"

ALLOWED_RIGHTS = {"TRAINING_ALLOWED", "TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE"}
EXAMPLE_ID_RE = re.compile(r"^[a-z0-9_-]+:[a-z0-9_-]+:[a-f0-9]{8}$")
SOURCE_ID_RE = re.compile(r"^SVK-\d{3,4}$")
RAW_URL_RE = re.compile(r"(?i)https?://|www\.|jainqq\.org/explore")
RAW_SVK_ID_RE = re.compile(r"(?i)\bsvk-\d{3,4}\b")
RAW_UNIT_ID_RE = re.compile(r":[a-z0-9]+:u\d{4,}:|:doc\b|:source_attribution:|:abstention")

MIN_ANSWER_WORDS = 12
NEAR_DUP_THRESHOLD = 0.80
QUOTE_MIN = 20

EXCLUDED_TASK63_REASON = (
    "identical question+answer adjudicated by Task 63"
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def fold(text) -> str:
    """Aggressive fold for cross-matching: NFKD, strip diacritics, alnum only."""
    s = unicodedata.normalize("NFKD", str(text or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join("".join(c.lower() if c.isalnum() else " " for c in s).split())


def load_schema():
    if not hasattr(load_schema, "_cache"):
        with open(SCHEMA_PATH, encoding="utf-8") as fh:
            load_schema._cache = json.load(fh)
    return load_schema._cache


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]

def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def shingles(text, k=3):
    s = fold(text).replace(" ", "")
    if not s:
        return set()
    return {s[i:i + k] for i in range(max(1, len(s) - k + 1))}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def load_source_manifest_raw():
    return load_manifest()


def quoted_spans(answer, min_len=QUOTE_MIN):
    return [m for m in re.findall(r'"([^"]{%d,})"' % min_len, answer or "")]


# ---------------------------------------------------------------------------
# input loading + mechanical normalization
# ---------------------------------------------------------------------------
def load_task63_decisions():
    """example_id -> {'decision': REJECT|REVISE, 'reason': ...} for hard exclusions."""
    queue = {}
    for row in read_jsonl(QUEUE_PATH):
        queue[row["example_id"]] = row["review_id"]
    out = {}
    for path, decision in ((REJECT_PATH, "REJECT"), (REVISE_PATH, "REVISE")):
        if not os.path.exists(path):
            continue
        for row in read_jsonl(path):
            rid = row.get("review_id")
            eid = next((e for e, r in queue.items() if r == rid), None)
            if eid is None:
                continue
            reason = row.get("reason") or row.get("revision_basis") or ""
            out[eid] = {"decision": decision, "review_id": rid, "reason": reason}
    return out


def normalize_row(row, input_kind, used_ids, notes):
    """Mechanical schema normalization only; never touches question/answer text."""
    if not EXAMPLE_ID_RE.match(str(row.get("example_id", ""))):
        digest = hashlib.sha256(
            (str(row.get("question")) + "\x00" + str(row.get("answer"))).encode("utf-8")
        ).hexdigest()[:8]
        base = f"{str(row.get('source_id', 'unknown')).lower()}:qa:{digest}"
        new_id, n = base, 1
        while new_id in used_ids:
            n += 1
            new_id = f"{str(row.get('source_id', 'unknown')).lower()}:qa:{digest[:-1]}{n}"
        row.setdefault("legacy_example_id", row.get("example_id"))
        row["example_id"] = new_id
        notes.append("example_id_reformatted_to_schema_pattern")

    prov = row.get("provenance") or {}
    if str(prov.get("source_quality", "")).upper() == "UNMEASURED":
        prov["source_quality"] = "UNKNOWN"
        row["provenance"] = prov
        notes.append("provenance.source_quality_UNMEASURED_to_UNKNOWN")

    schema = load_schema()
    flag_enum = set(schema["properties"]["quality_flags"]["items"]["enum"])
    flags = row.get("quality_flags") or []
    kept, moved = [], []
    for f in flags:
        (kept if f in flag_enum else moved).append(f)
    if moved:
        row["quality_flags"] = kept
        row.setdefault("quality_flags_notes", []).extend(moved)
        notes.append("quality_flags_non_enum_moved_to_quality_flags_notes")

    q, a = str(row.get("question") or "").strip(), str(row.get("answer") or "").strip()
    want = [{"role": "user", "content": q}, {"role": "assistant", "content": a}]
    if row.get("messages") != want:
        row["messages"] = want
        notes.append("messages_reformatted_from_question_answer")
    used_ids.add(row["example_id"])
    return row


def load_inputs():
    gold = read_jsonl(GOLD_PATH)
    human = read_jsonl(HUMAN_PATH)
    decisions = load_task63_decisions()

    candidates, normalization_log = [], []
    used_ids = set()
    for row in gold:
        r = dict(row)
        r["_input"] = "task63_approve"
        candidates.append(r)
        used_ids.add(r["example_id"])
    for row in human:
        notes = []
        r = normalize_row(dict(row), "human_verified", used_ids, notes)
        r["_input"] = "human_verified"
        r["_original_id"] = row["example_id"]
        candidates.append(r)
        if notes:
            normalization_log.append({"original_id": row["example_id"],
                                      "example_id": r["example_id"], "notes": notes})
    return candidates, decisions, normalization_log


# ---------------------------------------------------------------------------
# grounding / attribution checks (verified against metadata available to the row)
# ---------------------------------------------------------------------------
def corpus_unit_texts(source_ids, unit_ids):
    """One pass over the corpus: texts for the explicitly linked unit ids."""
    wanted = set(unit_ids)
    found = {}
    if not wanted or not os.path.exists(CORPUS_PATH):
        return found
    with open(CORPUS_PATH, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            uid = rec.get("unit_id") or rec.get("id")
            if uid in wanted:
                found[uid] = str(rec.get("text") or rec.get("normalized_text") or "")
            if len(found) == len(wanted):
                break
    return found


def corpus_quote_in_source(source_id, quote):
    """True when the (folded) quote occurs in any corpus unit of the source."""
    target = fold(quote)
    if not target or not os.path.exists(CORPUS_PATH):
        return False
    needle = '"source_id": "%s"' % source_id
    with open(CORPUS_PATH, encoding="utf-8") as fh:
        for line in fh:
            if needle not in line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = fold(str(rec.get("text") or "") + " " + str(rec.get("normalized_text") or ""))
            if target in text:
                return True
    return False


def linked_unit_ids(row):
    """Corpus unit ids a record points at (empty for manifest-shaped rows)."""
    prov = row.get("provenance") or {}
    unit_ids = list(prov.get("unit_ids") or [])
    text_id = prov.get("text_id")
    if text_id and not str(text_id).startswith("manifest:"):
        unit_ids.append(str(text_id))
    return sorted(set(unit_ids))


def grounding_check(row, manifest_row, unit_cache):
    """Return (ok, method, detail). Uses only evidence available to the record."""
    kind = row.get("_input") or (row.get("sft01") or {}).get("input")
    ev = row.get("evidence") or {}
    quotes = quoted_spans(row.get("answer"))

    if kind == "task63_approve":
        unit_text = fold(ev.get("unit_text") or "")
        hay = fold(" ".join([
            str(ev.get("unit_text") or ""),
            json.dumps(ev.get("extra") or {}, ensure_ascii=False),
            str(row.get("source_title") or ""),
            json.dumps(row.get("provenance") or {}, ensure_ascii=False),
            json.dumps(row.get("answer_metadata") or {}, ensure_ascii=False),
            json.dumps(manifest_row or {}, ensure_ascii=False),
        ]))
        if quotes:
            missing = [q for q in quotes if fold(q) and fold(q) not in unit_text and fold(q) not in hay]
            if missing:
                return False, "quote_not_in_linked_evidence", missing[0][:80]
        if not quotes and not ev.get("manifest_grounded") and not hay:
            return False, "no_linked_evidence", "evidence empty and no manifest grounding"
        if not quotes and ev.get("manifest_grounded") is not True and not ev.get("extra") and not unit_text:
            return False, "no_linked_evidence", "manifest_grounded false and no extra/unit_text"
        return True, ("quote_in_unit_text" if quotes else
                      "manifest_grounded_metadata" if ev.get("manifest_grounded") else
                      "evidence_metadata"), ""

    # HUMAN_VERIFIED rows: verify the inline quotation against corpus unit text.
    prov = row.get("provenance") or {}
    unit_ids = linked_unit_ids(row)
    if not quotes:
        hrev = row.get("human_review_evidence") or {}
        if isinstance(hrev, dict) and int(hrev.get("approvals") or 0) >= 1:
            return True, "human_review_evidence_no_quote", ""
        return False, "no_linked_evidence", "no inline quotation and no approval evidence"
    key = (row["example_id"], tuple(unit_ids))
    if key not in unit_cache:
        unit_cache[key] = corpus_unit_texts([prov.get("source_id")], unit_ids)
    joined = fold(" ".join(unit_cache[key].values()))
    quote_ok = all(fold(q) in joined for q in quotes)
    if quote_ok:
        return True, "corpus_linked_units", ""
    if corpus_quote_in_source(str(prov.get("source_id")), quotes[0]):
        return True, "corpus_source_units", ""
    return False, "quote_not_in_corpus_units", quotes[0][:80]


ATTR_PATTERNS = [
    (re.compile(r"as written by ([^.;]+?)(?: in (\d{4}))?[.;]"), "written_by"),
    (re.compile(r"published by ([^.;]+?)(?: in (\d{4}))?[.;]"), "published_by"),
    (re.compile(r"with relation_type (\w+)"), "relation_type"),
    (re.compile(r"knowledge layer is ([^.;]+?)(?: and |,|\.| and its)"), "knowledge_layer"),
    (re.compile(r"canonical status is (?:derived as |derived )?(\w+)"), "canonical_status"),
    (re.compile(r"classified as (\w+) material"), "knowledge_layer"),
    (re.compile(r"with (\w+) scope"), "religious_scope"),
    (re.compile(r"catalog header of \"([^\"]+)\""), "title"),
]

ROW_META_KEYS = [
    "canonical_status", "knowledge_layer", "religious_scope", "sect", "tradition",
    "lineage", "teacher_or_author", "curation_class", "question_type",
    "rights_status", "rights_basis", "source_title", "language",
]


def attribution_haystack(row, manifest_row, extra_text=""):
    parts = [
        str((row.get("evidence") or {}).get("unit_text") or ""),
        json.dumps(row.get("evidence") or {}, ensure_ascii=False),
        json.dumps(row.get("provenance") or {}, ensure_ascii=False),
        json.dumps(row.get("answer_metadata") or {}, ensure_ascii=False),
        json.dumps(row.get("citations") or {}, ensure_ascii=False),
        str(row.get("source_title") or ""),
        json.dumps(manifest_row or {}, ensure_ascii=False),
        extra_text,
    ]
    for key in ROW_META_KEYS:
        parts.append(str(row.get(key) or ""))
    return fold(" ".join(parts))


def attribution_check(row, manifest_row, extra_text=""):
    """Every traceable claim in the answer must appear in the row's metadata."""
    hay = attribution_haystack(row, manifest_row, extra_text)
    answer = row.get("answer") or ""
    for pattern, kind in ATTR_PATTERNS:
        for match in pattern.finditer(answer):
            value = match.group(1).strip()
            value = re.sub(r"\s*\([^)]*\)", "", value).strip()
            low = value.lower()
            if low.startswith(("not ", "no ", "unrecorded", "unknown")) or not value:
                continue
            value_fold = fold(value)
            if not value_fold:
                continue
            ok = value_fold in hay
            if not ok and kind in ("written_by", "published_by"):
                ok = fold(value.split(" in ")[0]) in hay
            if not ok and kind == "knowledge_layer":
                ok = (fold(value.split(" ")[0]) in hay
                      or map_knowledge_layer(value) == map_knowledge_layer(
                          str((row.get("provenance") or {}).get("knowledge_layer") or "")
                          or str(row.get("knowledge_layer") or ""))
                      or fold(str(row.get("knowledge_layer") or "")) in hay)
            if not ok and kind == "religious_scope":
                ok = (fold(str((row.get("provenance") or {}).get("religious_scope") or "")) in hay
                      or fold(str(row.get("religious_scope") or "")) in hay)
            if not ok:
                return False, f"{kind}:{value[:60]}"
            year = match.group(2) if match.lastindex and match.lastindex >= 2 else None
            if year and year not in hay:
                return False, f"{kind}_year:{year}"
    return True, ""


# ---------------------------------------------------------------------------
# metadata consistency, answer quality, rights
# ---------------------------------------------------------------------------
SECT_NEUTRAL = {"", "UNKNOWN", "MULTI_TRADITION", "MIXED", "GENERIC", "OMNIA", "ALL"}
TRADITION_NEUTRAL = {"", "UNKNOWN", "MULTI_TRADITION", "GENERIC", "MULTIPLE", "OMNIA"}


def consistency_issues(row, manifest_row):
    issues = []
    m = manifest_row or {}
    sect_row = str(row.get("sect") or "UNKNOWN").upper()
    sect_man = str(m.get("sect") or "").upper()
    if sect_row not in SECT_NEUTRAL and sect_man not in SECT_NEUTRAL and sect_row != sect_man:
        issues.append(f"sect:{sect_row}!={sect_man}")
    kl_row = map_knowledge_layer(str((row.get("provenance") or {}).get("knowledge_layer")
                                     or row.get("knowledge_layer") or ""))
    kl_man = map_knowledge_layer(str(m.get("knowledge_layer") or ""))
    # MIXED is a neutral superset claim (multiple layers in one source):
    # only flag when two specific, different layers are asserted.
    if (m.get("knowledge_layer") and kl_row != kl_man
            and "MIXED" not in (kl_row, kl_man)):
        issues.append(f"knowledge_layer:{kl_row}!={kl_man}")
    trad_row = str(row.get("tradition") or "").upper()
    trad_man = str(m.get("tradition") or "").upper()
    if trad_row not in TRADITION_NEUTRAL and trad_man not in TRADITION_NEUTRAL and trad_row != trad_man:
        issues.append(f"tradition:{trad_row}!={trad_man}")
    scope_row = map_religious_scope(str((row.get("provenance") or {}).get("religious_scope")
                                        or row.get("religious_scope") or ""))
    scope_man = map_religious_scope(str(m.get("religious_scope") or ""))
    if (scope_row not in SECT_NEUTRAL and scope_man not in SECT_NEUTRAL
            and scope_row != scope_man):
        issues.append(f"religious_scope:{scope_row}!={scope_man}")
    return issues


def answer_issues(row):
    issues = []
    q, a = str(row.get("question") or "").strip(), str(row.get("answer") or "").strip()
    if not q:
        issues.append("empty_question")
    if not a:
        issues.append("empty_answer")
    hay = f"{q} {a}"
    if RAW_URL_RE.search(hay):
        issues.append("raw_url")
    if RAW_SVK_ID_RE.search(hay):
        issues.append("raw_internal_id")
    if RAW_UNIT_ID_RE.search(hay):
        issues.append("raw_internal_id")
    words = a.split()
    if a and len(words) < MIN_ANSWER_WORDS:
        issues.append("fragmentary_answer")
    if a and a[-1] not in ".!\"'’”":
        issues.append("answer_missing_terminal_punctuation")
    msgs = row.get("messages") or []
    if len(msgs) != 2 or msgs[0].get("role") != "user" or msgs[1].get("role") != "assistant":
        issues.append("malformed_messages")
    elif msgs[0].get("content") != q or msgs[1].get("content") != a:
        issues.append("messages_do_not_match_question_answer")
    return issues


def provenance_issues(row, manifest_map):
    issues = []
    prov = row.get("provenance") or {}
    sid = str(prov.get("source_id") or row.get("source_id") or "")
    if not SOURCE_ID_RE.match(sid):
        issues.append(f"bad_source_id:{sid!r}")
    if not prov.get("text_id"):
        issues.append("missing_text_id")
    if not (prov.get("religious_scope") or row.get("religious_scope")):
        issues.append("missing_religious_scope")
    if sid and sid not in manifest_map:
        issues.append(f"source_not_in_manifest:{sid}")
    return issues


# ---------------------------------------------------------------------------
# per-row gate evaluation
# ---------------------------------------------------------------------------
def evaluate(row, decisions, manifest_map, audit, jainqq, unit_cache):
    eid_orig = row.get("_original_id", row["example_id"])
    if eid_orig in decisions:
        d = decisions[eid_orig]
        return None, f"TASK63_{d['decision']}", {
            "original_id": eid_orig, "review_id": d["review_id"],
            "task63_reason": d["reason"],
            "conflict": ("row is HUMAN_VERIFIED but Task 63 adjudicated the identical "
                         "record " + d["decision"] + "; Task 63 exclusion rule wins"),
        }

    sid = str((row.get("provenance") or {}).get("source_id") or row.get("source_id") or "")
    manifest_row = manifest_map.get(sid)

    rights = rights_for(sid, manifest_map, audit, jainqq)
    claimed = str(row.get("rights_status") or "")
    if claimed not in ALLOWED_RIGHTS:
        return None, "RIGHTS_NOT_CLEARED", {"claimed": claimed, "basis": row.get("rights_basis")}
    if not rights.get("allowed"):
        return None, "RIGHTS_NOT_CLEARED", {
            "claimed": claimed, "recomputed": rights.get("rights_status"),
            "basis": rights.get("basis"),
        }

    issues = provenance_issues(row, manifest_map)
    if issues:
        return None, "PROVENANCE_OR_MANIFEST_MISSING", {"issues": issues}

    issues = consistency_issues(row, manifest_row)
    if issues:
        return None, "METADATA_INCONSISTENT", {"issues": issues}

    ok, method, detail = grounding_check(row, manifest_row, unit_cache)
    if not ok:
        return None, "NOT_GROUNDED", {"method": method, "detail": detail}

    extra_text = ""
    kind = row.get("_input") or (row.get("sft01") or {}).get("input")
    if kind == "human_verified":
        key = (row["example_id"], tuple(linked_unit_ids(row)))
        extra_text = " ".join(unit_cache.get(key, {}).values())
    ok, detail = attribution_check(row, manifest_row, extra_text)
    if not ok:
        return None, "ATTRIBUTION_UNSUPPORTED", {"detail": detail}

    issues = answer_issues(row)
    if issues:
        return None, "ANSWER_QUALITY", {"issues": issues}

    return {
        "input": row["_input"],
        "rights": rights.get("rights_status"),
        "rights_basis": rights.get("basis"),
        "grounding": method,
        "attribution": "traced_to_metadata",
        "metadata_consistency": "ok",
        "manifest_source": "present",
    }, "SELECTED", {}


# ---------------------------------------------------------------------------
# dedup + deterministic source-level split
# ---------------------------------------------------------------------------
def dedup(selected):
    """Drop duplicate example_ids and near-duplicate questions (>=0.80)."""
    removed = []
    seen_ids = {}
    keep = []
    for row in selected:
        eid = row["example_id"]
        if eid in seen_ids:
            removed.append({"example_id": eid, "reason": "duplicate_example_id",
                            "kept": seen_ids[eid]})
            continue
        seen_ids[eid] = eid
        keep.append(row)
    dup_pairs = []
    sh = {r["example_id"]: shingles(r["question"]) for r in keep}
    ids = [r["example_id"] for r in keep]
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            v = jaccard(sh[ids[i]], sh[ids[j]])
            if v >= NEAR_DUP_THRESHOLD:
                dup_pairs.append((round(v, 3), ids[i], ids[j]))
    dropped = set()
    by_id = {r["example_id"]: r for r in keep}
    for _, a, b in sorted(dup_pairs, reverse=True):
        def prio(e):
            r = by_id[e]
            return (1 if r["_input"] == "human_verified" else 0, e)
        loser = a if prio(a) < prio(b) else b
        if loser in dropped:
            continue
        dropped.add(loser)
        removed.append({"example_id": loser, "reason": "near_duplicate_question",
                        "kept": b if loser == a else a})
    final = [r for r in keep if r["example_id"] not in dropped]
    return final, {"pairs_checked": len(keep) * (len(keep) - 1) // 2,
                   "near_dup_pairs": len(dup_pairs),
                   "removed": removed}


def assign_split(selected):
    """Deterministic source-level split; prefers frozen-eval sources into eval."""
    groups = OrderedDict()
    for row in selected:
        groups.setdefault(row["source_id"], []).append(row)

    def order_key(src):
        return int(hashlib.sha256(f"{SEED}:{src}".encode()).hexdigest()[:12], 16)

    overlap_srcs = [s for s in groups if any(
        r.get("sft01", {}).get("frozen_eval_source_overlap") for r in groups[s])]
    plain_srcs = [s for s in groups if s not in set(overlap_srcs)]
    target = max(MIN_EVAL_ROWS, round(len(selected) * EVAL_FRACTION))

    eval_set, eval_rows = [], 0
    for src in sorted(overlap_srcs, key=order_key) + sorted(plain_srcs, key=order_key):
        if eval_rows >= target:
            break
        eval_set.append(src)
        eval_rows += len(groups[src])
    eval_sources = set(eval_set)
    train_rows = [r for r in selected if r["source_id"] not in eval_sources]
    eval_rows_list = [r for r in selected if r["source_id"] in eval_sources]
    return train_rows, eval_rows_list, {
        "method": "source-level, sha256(seed=42|source_id) order, frozen-eval sources first",
        "seed": SEED,
        "eval_fraction_target": EVAL_FRACTION,
        "min_eval_rows": MIN_EVAL_ROWS,
        "target_eval_rows": target,
        "eval_sources": sorted(eval_sources),
        "train_sources": sorted({r["source_id"] for r in train_rows}),
        "overlap_sources_preferred_into_eval": sorted(
            set(eval_sources) & set(overlap_srcs)),
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    t0 = time.time()
    frozen_hash_before = sha256_file(FROZEN_EVAL_PATH)
    frozen_sources = set()
    for case in read_jsonl(FROZEN_EVAL_PATH):
        frozen_sources |= set(re.findall(r"SVK-\d{3,4}", json.dumps(case)))

    candidates, decisions, normalization_log = load_inputs()
    approve_count = sum(1 for c in candidates if c["_input"] == "task63_approve")
    human_input_count = sum(1 for c in candidates if c["_input"] == "human_verified")
    human_input_ids = [c.get("_original_id", c["example_id"]) for c in candidates
                       if c["_input"] == "human_verified"]
    manifest_map = load_source_manifest_raw()
    audit = load_rights_audit()
    jainqq = load_jainqq_evidence()

    unit_cache = {}
    selected, exclusion_counter, exclusion_detail = [], Counter(), []
    gates = Counter()
    for row in candidates:
        gate, code, detail = evaluate(row, decisions, manifest_map, audit, jainqq, unit_cache)
        if code != "SELECTED":
            exclusion_counter[code] += 1
            exclusion_detail.append({
                "original_id": row.get("_original_id", row["example_id"]),
                "example_id": row.get("example_id"),
                "input": row["_input"], "code": code, **detail,
            })
            continue
        row["sft01"] = {
            "input": row["_input"],
            "original_id": row.get("_original_id") or row["example_id"],
            "gates": gate,
            "frozen_eval_source_overlap": row["source_id"] in frozen_sources,
            "normalizations": [note for n in normalization_log
                               if n["original_id"] == row.get("_original_id")
                               for note in n["notes"]],
        }
        gates[f"rights:{gate['rights']}"] += 1
        gates[f"grounding:{gate['grounding']}"] += 1
        selected.append(row)

    selected, dedup_report = dedup(selected)
    for item in dedup_report["removed"]:
        exclusion_counter[item["reason"]] += 1
        exclusion_detail.append({**item, "code": item["reason"]})

    train_rows, eval_rows, split_report = assign_split(selected)
    for row in train_rows:
        row["split"] = "train"
    for row in eval_rows:
        row["split"] = "validation"
    for row in train_rows + eval_rows:
        row.pop("_input", None)
        row.pop("_original_id", None)

    # schema validation of every output row
    import jsonschema
    validator = jsonschema.Draft7Validator(load_schema())
    schema_errors = []
    for row in train_rows + eval_rows:
        errs = [f"{e.json_path}: {e.message[:120]}" for e in validator.iter_errors(row)]
        if errs:
            schema_errors.append({"example_id": row["example_id"], "errors": errs})

    # leakage checks
    train_srcs = {r["source_id"] for r in train_rows}
    eval_srcs = {r["source_id"] for r in eval_rows}
    leakage = {
        "shared_sources": sorted(train_srcs & eval_srcs),
        "shared_example_ids": sorted(
            {r["example_id"] for r in train_rows} & {r["example_id"] for r in eval_rows}),
        "shared_questions": sorted(
            {fold(r["question"]) for r in train_rows} & {fold(r["question"]) for r in eval_rows}),
        "shared_answers": sorted(
            {fold(r["answer"]) for r in train_rows} & {fold(r["answer"]) for r in eval_rows}),
    }

    def dist(rows, key):
        return dict(sorted(Counter(str(r.get(key) or "UNKNOWN") for r in rows).items()))

    def dist_prov(rows, key):
        return dict(sorted(Counter(
            str((r.get("provenance") or {}).get(key) or r.get(key) or "UNKNOWN")
            for r in rows).items()))

    overlap_train = [r["example_id"] for r in train_rows
                     if r["sft01"]["frozen_eval_source_overlap"]]
    overlap_eval = [r["example_id"] for r in eval_rows
                    if r["sft01"]["frozen_eval_source_overlap"]]

    human_selected = [r for r in selected if r["sft01"]["input"] == "human_verified"]

    stats = {
        "task": 64,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_sec": round(time.time() - t0, 1),
        "inputs": {
            "task63_approve": approve_count,
            "human_verified": human_input_count,
            "total": approve_count + human_input_count,
        },
        "conflict_rule": (
            "HUMAN_VERIFIED rows whose identical record is a Task 63 REJECT/REVISE "
            "are excluded; the explicit Task-63 exclusion rule takes precedence."),
        "exclusions": dict(sorted(exclusion_counter.items())),
        "exclusion_detail": exclusion_detail,
        "selected_total": len(selected),
        "splits": {
            "train": len(train_rows), "eval": len(eval_rows), **split_report,
        },
        "distributions": {
            "task_category": dist(selected, "task_category"),
            "rights_status": dist(selected, "rights_status"),
            "input": dist([{"_input": r["sft01"]["input"]} for r in selected], "_input"),
            "knowledge_layer": dist_prov(selected, "knowledge_layer"),
            "sect": dist_prov(selected, "sect"),
            "religious_scope": dist_prov(selected, "religious_scope"),
            "train_task_category": dist(train_rows, "task_category"),
            "eval_task_category": dist(eval_rows, "task_category"),
        },
        "human_verified": {
            "input": human_input_count,
            "input_ids": sorted(human_input_ids),
            "selected": len(human_selected),
            "excluded": human_input_count - len(human_selected),
            "excluded_ids": sorted(set(human_input_ids)
                                   - {r["sft01"].get("original_id") or r["example_id"]
                                      for r in human_selected}),
            "newly_created": 0,
            "selected_ids": sorted(r["example_id"] for r in human_selected),
        },
        "normalizations": normalization_log,
        "dedup": {k: v for k, v in dedup_report.items() if k != "removed"}
                | {"removed": dedup_report["removed"]},
        "leakage_checks": leakage,
        "frozen_eval": {
            "sha256": frozen_hash_before,
            "sha256_matches_expected": frozen_hash_before == FROZEN_EVAL_SHA256,
            "sources_in_frozen_eval": sorted(frozen_sources),
            "overlap_rows_train": len(overlap_train),
            "overlap_rows_eval": len(overlap_eval),
            "note": ("overlap sources are preferred into the eval split so they are never "
                     "trained on unless the eval budget is already full; residual overlap "
                     "is reported as a known limitation"),
        },
        "schema": {"valid": not schema_errors, "errors": schema_errors[:10]},
        "gates_passed_counts": dict(gates),
        "outputs": {
            "train_file": os.path.relpath(OUT_TRAIN, ROOT),
            "eval_file": os.path.relpath(OUT_EVAL, ROOT),
        },
    }

    write_jsonl(OUT_TRAIN, train_rows)
    write_jsonl(OUT_EVAL, eval_rows)
    stats["outputs"]["train_sha256"] = sha256_file(OUT_TRAIN)
    stats["outputs"]["eval_sha256"] = sha256_file(OUT_EVAL)
    stats["outputs"]["train_rows"] = len(train_rows)
    stats["outputs"]["eval_rows"] = len(eval_rows)
    os.makedirs(os.path.dirname(OUT_STATS), exist_ok=True)
    with open(OUT_STATS, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2, ensure_ascii=False)

    frozen_hash_after = sha256_file(FROZEN_EVAL_PATH)
    print("TASK 64 build summary")
    print("  inputs            : %d (approve=%d human_verified=%d)" % (
        stats["inputs"]["total"], stats["inputs"]["task63_approve"],
        stats["inputs"]["human_verified"]))
    print("  excluded          : %d %s" % (
        sum(exclusion_counter.values()), dict(exclusion_counter)))
    print("  selected          : %d -> train=%d eval=%d" % (
        len(selected), len(train_rows), len(eval_rows)))
    print("  schema valid      : %s" % (not schema_errors))
    print("  leakage           : %s" % (
        "CLEAN" if not any(leakage.values()) else leakage))
    print("  frozen eval hash  : %s (%s)" % (
        frozen_hash_before[:16], "unchanged" if frozen_hash_before == frozen_hash_after else "CHANGED"))
    print("  wrote             : %s, %s, %s" % (
        os.path.relpath(OUT_TRAIN, ROOT), os.path.relpath(OUT_EVAL, ROOT),
        os.path.relpath(OUT_STATS, ROOT)))
    if schema_errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
