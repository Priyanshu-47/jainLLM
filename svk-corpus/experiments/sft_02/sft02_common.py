"""Shared helpers for TASK 67 - SFT-02 dataset construction.

Read-only against the corpus, manifests and prior artifacts. Nothing outside
the declared SFT-02 output paths is modified. No synthetic religious content
is generated: every row built here quotes or directly transcribes evidence
from a rights-cleared corpus unit or manifest field.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Tuple

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

MANIFEST_PATH = os.path.join(ROOT, "manifests", "source_manifest.csv")
CORPUS_PATH = os.path.join(ROOT, "data", "release", "training_corpus.jsonl")
SCHEMA_PATH = os.path.join(ROOT, "data", "training", "sft_schema_v1.json")
GOLD_PATH = os.path.join(ROOT, "data", "training", "sft_gold_v4_candidates.jsonl")
TRAIN_V1_PATH = os.path.join(ROOT, "data", "training", "sft_train_v1.jsonl")
POOL_PATH = os.path.join(ROOT, "data", "training", "sft_verified_candidate_pool_v1.jsonl")
FROZEN_EVAL_PATH = os.path.join(ROOT, "data", "evaluation", "dapt01_eval_cases.jsonl")
RIGHTS_AUDIT_PATH = os.path.join(ROOT, "data", "rights", "jain_source_rights_audit_v1.json")

OUT_TRAIN = os.path.join(ROOT, "data", "training", "sft_train_v2.jsonl")
OUT_EVAL = os.path.join(ROOT, "data", "evaluation", "sft_eval_v2.jsonl")
OUT_STATS = os.path.join(ROOT, "data", "reports", "task67_sft02_build_stats.json")

SEED = "42"
EVAL_FRACTION = 0.15

# Third-party synthetic conversation export (ShareGPT): excluded from all
# Task-67 NEW rows. Approved Task-63 rows are unaffected.
SYNTHETIC_SOURCES = frozenset({"SVK-0026"})
MIN_EVAL_ROWS = 12
FROZEN_EVAL_SHA256 = (
    "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81"
)
ALLOWED_RIGHTS = {"TRAINING_ALLOWED", "TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE"}
EXAMPLE_ID_RE = re.compile(r"^[a-z0-9_-]+:[a-z0-9_-]+:[a-f0-9]{8}$")
SOURCE_ID_RE = re.compile(r"^SVK-\d{3,4}$")
RAW_URL_RE = re.compile(r"(?i)https?://|www\.|jainqq\.org/explore")
RAW_SVK_ID_RE = re.compile(r"(?i)\bsvk-\d{3,4}\b")
RAW_UNIT_ID_RE = re.compile(r":[a-z0-9]+:u\d{4,}:|:doc\b")
JSON_BLOB_RE = re.compile(r'"conversations"|\{"from"|\\n\s*"from"\s*:')
MIN_ANSWER_WORDS = 12
NEAR_DUP_THRESHOLD = 0.80
QUOTE_MIN = 20

# Task-66 regression categories the SFT-02 eval set must cover (Phase 7).
# Eval coverage: mirror the SFT-01 9-row protocol (source-level disjoint,
# behaviour-critical categories) and add abstention because Task-66 s14
# makes abstention calibration the central SFT-02 goal. Multilingual,
# practice, terminology and distinction rows stay train-only: the frozen
# 47-case benchmark already probes languages/sect externally.
REQUIRED_EVAL_COVERAGE = [
    "ABSTENTION/INSUFFICIENT_EVIDENCE",
    "CANONICAL_VS_COMMENTARY",
    "SOURCE_ATTRIBUTION",
]

# Task-61 category -> sft_schema_v1 task_category (project convention).
CATEGORY_TO_TASK_CATEGORY = {
    "STHANAKAVASI_DISTINCTION": "cross_tradition_distinction",
    "SOURCE_ATTRIBUTION": "source_citation",
    "ABSTENTION/INSUFFICIENT_EVIDENCE": "abstention",
    "AGAM_GROUNDED": "general_qa",
    "PRACTICE_EXPLANATION": "general_qa",
    "STHANAKAVASI_TERMINOLOGY": "sthanaqa",
    "PRAKRIT": "prakrit_explanation",
    "HINDI": "multilingual_mapping",
    "GUJARATI": "multilingual_mapping",
    "SANSKRIT": "multilingual_mapping",
    "GENERAL_JAIN_CONCEPT": "general_qa",
    "CANONICAL_VS_COMMENTARY": "canonical_commentary_distinction",
}


# ---------------------------------------------------------------------------
# basic helpers
# ---------------------------------------------------------------------------
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fold(text: str) -> str:
    """Aggressive fold for substring grounding checks (task-64 convention)."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text))
    text = text.replace("\u00a0", " ")
    return "".join(ch for ch in text if not ch.isspace()).lower()


def norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def digest_key(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def shingles(text: str, k: int = 3) -> set:
    t = norm_ws(text).lower()
    if not t:
        return set()
    if len(t) <= k:
        return {t}
    return {t[i:i + k] for i in range(len(t) - k + 1)}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter)


def read_jsonl(path: str) -> List[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def write_jsonl(path: str, rows: Iterable[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")


# ---------------------------------------------------------------------------
# frozen benchmark (read-only)
# ---------------------------------------------------------------------------
def load_frozen_sources() -> set:
    srcs = set()
    for case in read_jsonl(FROZEN_EVAL_PATH):
        sid = (case.get("provenance") or {}).get("source_id")
        if sid:
            srcs.add(sid)
    return srcs


def frozen_sha256() -> str:
    return sha256_file(FROZEN_EVAL_PATH)


# ---------------------------------------------------------------------------
# rights / manifest
# ---------------------------------------------------------------------------
class RightsContext:
    def __init__(self) -> None:
        self.manifest = load_manifest()
        self.audit = load_rights_audit()
        self.jainqq = load_jainqq_evidence()
        self._cache: Dict[str, dict] = {}

    def synthetic(self, source_id: str) -> bool:
        return source_id in SYNTHETIC_SOURCES

    def allowed(self, source_id: str) -> bool:
        return source_id in self.allowed_sources()

    def info(self, source_id: str) -> dict:
        if source_id not in self._cache:
            r = rights_for(source_id, self.manifest, self.audit, self.jainqq) or {}
            self._cache[source_id] = r
        return self._cache[source_id]

    def status(self, source_id: str) -> str:
        return str(self.info(source_id).get("rights_status") or "")

    def allowed_sources(self) -> set:
        if not hasattr(self, "_allowed"):
            self._allowed = {
                sid
                for sid in self.manifest
                if self.info(sid).get("allowed")
                and self.status(sid) in ALLOWED_RIGHTS
            }
        return self._allowed

    def manifest_row(self, source_id: str) -> dict:
        return self.manifest.get(source_id) or {}

    def knowledge_layer(self, source_id: str) -> str:
        return map_knowledge_layer((self.manifest_row(source_id) or {}).get("knowledge_layer"))

    def religious_scope(self, source_id: str) -> str:
        return map_religious_scope(str(self.manifest_row(source_id).get("religious_scope") or ""))


# ---------------------------------------------------------------------------
# corpus access
# ---------------------------------------------------------------------------
def iter_corpus() -> Iterable[dict]:
    with open(CORPUS_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def corpus_units_by_source(source_ids: set) -> Dict[str, List[dict]]:
    wanted = set(source_ids)
    out: Dict[str, List[dict]] = {sid: [] for sid in wanted}
    for rec in iter_corpus():
        sid = rec.get("source_id")
        if sid in wanted:
            out[sid].append(rec)
    return out


def unit_by_id() -> Dict[str, dict]:
    return {rec.get("id") or rec.get("unit_id"): rec for rec in iter_corpus()}


def usable_unit_text(rec: dict) -> str:
    """Reject JSON conversation blobs (SVK-0026 style) and empty text."""
    text = str(rec.get("text") or "")
    head = text[:400]
    if JSON_BLOB_RE.search(head) or head.lstrip().startswith("{"):
        return ""
    return text


# ---------------------------------------------------------------------------
# text quality
# ---------------------------------------------------------------------------
DEVANAGARI_RE = re.compile(r"[\u0900-\u097f]")
GUJARATI_RE = re.compile(r"[\u0a80-\u0aff]")
LATIN_RE = re.compile(r"[A-Za-z]")


def script_ok(text: str, language: str) -> bool:
    if language == "hi":
        return bool(DEVANAGARI_RE.search(text))
    if language == "gu":
        return bool(GUJARATI_RE.search(text))
    return True


def sentence_split(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?।॥])\s+|\n+", text)
    return [norm_ws(p) for p in parts if norm_ws(p)]


def good_sentence(s: str, min_words: int = 8, max_words: int = 120) -> bool:
    if not s or len(s) < 40 or len(s) > 700:
        return False
    if JSON_BLOB_RE.search(s) or s.lstrip().startswith("{"):
        return False
    words = s.split()
    if not (min_words <= len(words) <= max_words):
        return False
    letters = sum(c.isalpha() for c in s)
    if letters < 0.5 * len(s):
        return False
    digits = sum(c.isdigit() for c in s)
    if digits > 0.15 * len(s):
        return False
    return True


def quote_spans(answer: str, min_len: int = QUOTE_MIN) -> List[str]:
    return [
        norm_ws(m)
        for m in re.findall(r"[\"“']([^\"”']{4,})[\"”']", answer)
        if len(norm_ws(m)) >= min_len
    ]


# ---------------------------------------------------------------------------
# row construction
# ---------------------------------------------------------------------------
def make_example_id(source_id: str, unit_type: str, *seeds: str) -> str:
    sid = source_id.lower()
    h = digest_key(*seeds)[:8]
    return f"{sid}:{unit_type}:{h}"


def make_messages(question: str, answer: str) -> List[dict]:
    return [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]


def base_provenance(source_id: str, rctx: RightsContext, **extra: Any) -> dict:
    m = rctx.manifest_row(source_id)
    conf = str(m.get("sect_confidence") or "").strip().lower()
    conf = {"confirmed": "HIGH", "high": "HIGH", "medium": "MEDIUM",
            "low": "LOW", "unknown": "UNKNOWN"}.get(conf, "")
    if conf not in ("HIGH", "MEDIUM", "LOW", "UNKNOWN"):
        sect = str(m.get("sect") or "").strip().upper()
        conf = "MEDIUM" if sect and sect != "UNKNOWN" else "UNKNOWN"
    prov = {
        "source_id": source_id,
        "text_id": f"manifest:{source_id}",
        "title": m.get("title") or "",
        "author": m.get("author") or "unknown",
        "publication_year": m.get("publication_year") or "",
        "sect": m.get("sect") or "UNKNOWN",
        "sect_confidence": conf,
        "tradition": m.get("tradition") or "",
        "language": m.get("language") or "",
        "license_status": rctx.status(source_id),
        "knowledge_layer": rctx.knowledge_layer(source_id),
        "religious_scope": rctx.religious_scope(source_id),
        "locator": {"page": None, "section": None},
        "unit_ids": [],
    }
    prov.update(extra)
    return prov


def text_issues(text: str) -> List[str]:
    issues = []
    if not text or not text.strip():
        issues.append("empty")
        return issues
    if RAW_URL_RE.search(text):
        issues.append("raw_url")
    if RAW_SVK_ID_RE.search(text):
        issues.append("raw_source_id")
    if RAW_UNIT_ID_RE.search(text):
        issues.append("raw_unit_id")
    if len(text.split()) < MIN_ANSWER_WORDS:
        issues.append("too_short")
    return issues


ORIGIN_METHOD_BY_TAG = {
    "task67_sft02:calibration_unanswerable": ("synthetic_abstention", "medium"),
    "task67_sft02:anti_fabrication": ("synthetic_abstention", "medium"),
    "task67_sft02:calibration_answerable": ("synthetic_qa_generation", "medium"),
}


def origin_obj(tag) -> dict:
    """Schema-compliant origin object (sft_schema_v1: synthetic + method)."""
    if isinstance(tag, dict):
        return tag
    method, conf = ORIGIN_METHOD_BY_TAG.get(
        tag, ("synthetic_qa_generation", "high"))
    return {"synthetic": True, "method": method,
            "confidence": conf, "builder": tag}


def build_row(
    *,
    source_id: str,
    category: str,
    question: str,
    answer: str,
    language: str,
    origin: str,
    evidence: dict,
    rctx: RightsContext,
    unit_type: str = "qa",
    tags: Optional[List[str]] = None,
    knowledge_layer: Optional[str] = None,
    religious_scope: Optional[str] = None,
    canonical_status: str = "UNKNOWN",
    extra: Optional[dict] = None,
) -> dict:
    question = norm_ws(question)
    answer = norm_ws(answer)
    row = {
        "example_id": make_example_id(source_id, unit_type, question, answer),
        "version": "1.0",
        "task_category": CATEGORY_TO_TASK_CATEGORY[category],
        "category": category,
        "question": question,
        "answer": answer,
        "messages": make_messages(question, answer),
        "language": language,
        "source_id": source_id,
        "source_title": rctx.manifest_row(source_id).get("title") or "",
        "knowledge_layer": knowledge_layer or rctx.knowledge_layer(source_id),
        "religious_scope": religious_scope or "",
        "canonical_status": canonical_status,
        "rights_status": rctx.status(source_id),
        "provenance": base_provenance(source_id, rctx),
        "evidence": evidence,
        "origin": origin_obj(origin),
        "split": "train",  # placeholder; the deterministic split rewrites it
        "tags": tags or [],
    }
    if extra:
        row.update(extra)
    return row
