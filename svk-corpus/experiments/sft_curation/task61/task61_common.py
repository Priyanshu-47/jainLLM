"""Shared helpers for TASK 61 - SFT data reconciliation and curation gate.

Read-only against corpus/manifests. No file is modified outside the Task 61
output paths declared in the task brief.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import unicodedata
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
MANIFEST = os.path.join(ROOT, "manifests", "source_manifest.csv")
CORPUS = os.path.join(ROOT, "data", "release", "training_corpus.jsonl")
RIGHTS_AUDIT = os.path.join(ROOT, "data", "rights", "jain_source_rights_audit_v1.json")
JAINQQ_EVIDENCE = os.path.join(ROOT, "data", "rights", "jainqq_permission_evidence_v1.json")
TRAIN_DIR = os.path.join(ROOT, "data", "domain_train")
SFT_DIR = os.path.join(ROOT, "data", "training")
SFT_SCHEMA = os.path.join(SFT_DIR, "sft_schema_v1.json")

# ---------------------------------------------------------------------------
# Category vocabulary required by TASK 61 (12 target categories).
# ---------------------------------------------------------------------------
CATEGORIES = [
    "STHANAKAVASI_DISTINCTION",
    "SOURCE_ATTRIBUTION",
    "ABSTENTION/INSUFFICIENT_EVIDENCE",
    "AGAM_GROUNDED",
    "PRACTICE_EXPLANATION",
    "STHANAKAVASI_TERMINOLOGY",
    "PRAKRIT",
    "HINDI",
    "GUJARATI",
    "SANSKRIT",
    "GENERAL_JAIN_CONCEPT",
    "CANONICAL_VS_COMMENTARY",
]

# category (Task 61) -> task_category (sft_schema_v1.json enum)
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

# Candidate classification classes (Task 61 brief, section 6).
CLASS_A = "HUMAN_VERIFIED_APPROVED"
CLASS_B = "HUMAN_REVISE_REQUIRED"
CLASS_C = "HUMAN_REJECTED"
CLASS_D = "NEW_CANDIDATE_REQUIRES_HUMAN_REVIEW"
CLASS_E = "RIGHTS_BLOCKED"
CLASS_F = "PROVENANCE_INCOMPLETE"
CLASS_G = "DUPLICATE"
CLASS_H = "UNSUITABLE_FOR_SFT"
CLASS_ORDER = [CLASS_A, CLASS_B, CLASS_C, CLASS_D, CLASS_E, CLASS_F, CLASS_G, CLASS_H]

STATE_PRESENT = "PRESENT"
STATE_RECOVERABLE = "RECOVERABLE"
STATE_EXCLUDED = "EXCLUDED_WITH_REASON"
STATE_NOT_VERIFIED = "NOT_VERIFIED"
VALID_STATES = [STATE_PRESENT, STATE_RECOVERABLE, STATE_EXCLUDED, STATE_NOT_VERIFIED]


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    return _read_jsonl(path)


def write_jsonl(path: str, rows: Iterable[Dict[str, Any]]) -> int:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=False) + "\n")
            n += 1
    return n


def load_manifest() -> Dict[str, Dict[str, str]]:
    with open(MANIFEST, encoding="utf-8") as fh:
        return {r["source_id"]: r for r in csv.DictReader(fh) if r.get("source_id")}


def load_rights_audit() -> Dict[str, Dict[str, Any]]:
    with open(RIGHTS_AUDIT, encoding="utf-8") as fh:
        data = json.load(fh)
    return {s["source_id"]: s for s in data.get("sources", [])}


def load_jainqq_evidence() -> Dict[str, Dict[str, Any]]:
    """Expand data/rights/jainqq_permission_evidence_v1.json to per-source records."""
    if not os.path.exists(JAINQQ_EVIDENCE):
        return {}
    with open(JAINQQ_EVIDENCE, encoding="utf-8") as fh:
        data = json.load(fh)
    out: Dict[str, Dict[str, Any]] = {}

    def _add(sid: str, rec: Dict[str, Any]) -> None:
        out.setdefault(sid, rec)

    if isinstance(data, dict):
        scope = data.get("scope") or {}
        if isinstance(scope, dict):
            base = {
                "permission_status": data.get("status"),
                "permission_date": (data.get("permission_evidence") or {}).get("permission_date"),
                "permission_holder": (data.get("permission_evidence") or {}).get("permission_holder"),
                "ml_training": scope.get("ml_training"),
                "sft": scope.get("sft"),
                "evidence_file": os.path.relpath(JAINQQ_EVIDENCE, ROOT),
                "confidence": data.get("confidence"),
                "attribution_requirements": data.get("attribution_requirements"),
            }
            for sid in scope.get("sources_covered", []) or []:
                _add(sid, dict(base))
        for key, val in data.items():
            if isinstance(val, dict) and str(key).startswith("SVK-"):
                rec = dict(val)
                rec.setdefault("source_id", key)
                _add(key, rec)
    elif isinstance(data, list):
        for rec in data:
            if isinstance(rec, dict) and rec.get("source_id"):
                _add(rec["source_id"], rec)
    return out


def load_split_map() -> Dict[str, str]:
    """Document-level split actually used by data/domain_train/*.jsonl."""
    split_of: Dict[str, str] = {}
    for split in ("train", "val", "test"):
        path = os.path.join(TRAIN_DIR, f"{split}.jsonl")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sid = rec.get("source_id") or str(rec.get("id", "")).split(":")[0]
                if sid and sid not in split_of:
                    split_of[sid] = split
    return split_of


def split_candidate(source_id: str, split_of: Dict[str, str]) -> str:
    s = split_of.get(source_id)
    if s == "val":
        return "validation"
    if s in ("train", "test"):
        return s
    return "unassigned_not_in_domain_train"


# ---------------------------------------------------------------------------
# Rights
# ---------------------------------------------------------------------------
def rights_for(
    source_id: str,
    manifest: Dict[str, Dict[str, str]],
    audit: Dict[str, Dict[str, Any]],
    jainqq: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Conservative rights decision for SFT candidacy of one source.

    allowed only when (manifest TRAINING_ALLOWED) OR (JainQQ permission
    evidence with sft scope) OR (rights audit category A_CLEARLY_USABLE).
    """
    m = manifest.get(source_id, {})
    a = audit.get(source_id, {})
    perm = (m.get("training_permission") or "").strip()
    perm_rule = perm.split(" ")[0] if perm else ""
    audit_cat = a.get("category", "")
    ev = jainqq.get(source_id, {})
    ev_sft = False
    if ev:
        status = str(ev.get("permission_status") or "").upper()
        if isinstance(ev.get("sft"), bool):
            ev_sft = bool(ev.get("sft"))
        elif status == "PERMISSION_GRANTED":
            ev_sft = True

    flags: List[str] = []
    if ev and perm_rule not in ("TRAINING_ALLOWED",):
        flags.append(
            "MANIFEST_RIGHTS_STALE: manifest training_permission=%r but permission evidence file reports %s"
            % (perm, ev.get("permission_status", ev.get("status", "unknown")))
        )

    if perm_rule == "TRAINING_ALLOWED":
        return {
            "allowed": True,
            "rights_status": "TRAINING_ALLOWED",
            "basis": f"manifest:{perm}",
            "audit_category": audit_cat,
            "flags": flags,
        }
    if perm_rule.upper() == "YES" and (m.get("license") or "").strip().upper() == "TRAINING_ALLOWED":
        flags.append(
            "LEGACY_PERMISSION_COLUMN: training_permission=%r while license=%r (license_confidence=%s)"
            % (perm, m.get("license"), m.get("license_confidence"))
        )
        if not audit_cat:
            flags.append("RIGHTS_AUDIT_NOT_COVERED: source absent from jain_source_rights_audit_v1.json")
        return {
            "allowed": True,
            "rights_status": "TRAINING_ALLOWED",
            "basis": "manifest:license=%s (training_permission legacy value %r)" % (m.get("license"), perm),
            "audit_category": audit_cat,
            "flags": flags,
        }
    if ev_sft:
        return {
            "allowed": True,
            "rights_status": "TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE",
            "basis": "jainqq_permission_evidence:" + str(ev.get("permission_status", "")),
            "audit_category": audit_cat,
            "flags": flags,
        }
    if audit_cat == "A_CLEARLY_USABLE":
        return {
            "allowed": True,
            "rights_status": "TRAINING_ALLOWED",
            "basis": "rights_audit:A_CLEARLY_USABLE",
            "audit_category": audit_cat,
            "flags": flags,
        }
    if audit_cat in ("B_USABLE_AFTER_PERMISSION", "C_UNCERTAIN"):
        return {
            "allowed": False,
            "rights_status": "NEEDS_PERMISSION" if audit_cat == "B_USABLE_AFTER_PERMISSION" else "RIGHTS_UNCERTAIN",
            "basis": f"rights_audit:{audit_cat}",
            "audit_category": audit_cat,
            "flags": flags,
        }
    if audit_cat == "D_RESTRICTED":
        return {
            "allowed": False,
            "rights_status": "NOT_ALLOWED",
            "basis": "rights_audit:D_RESTRICTED",
            "audit_category": audit_cat,
            "flags": flags,
        }
    if perm_rule in ("NOT_ALLOWED",):
        return {"allowed": False, "rights_status": "NOT_ALLOWED", "basis": f"manifest:{perm}", "audit_category": audit_cat, "flags": flags}
    if perm_rule in ("NEEDS_PERMISSION",):
        return {"allowed": False, "rights_status": "NEEDS_PERMISSION", "basis": f"manifest:{perm}", "audit_category": audit_cat, "flags": flags}
    if perm_rule in ("UNKNOWN",) or not perm_rule:
        return {"allowed": False, "rights_status": "RIGHTS_UNKNOWN", "basis": f"manifest:{perm or 'missing'}", "audit_category": audit_cat, "flags": flags}
    if perm_rule == "RAG_ONLY":
        return {"allowed": False, "rights_status": "RAG_ONLY", "basis": f"manifest:{perm}", "audit_category": audit_cat, "flags": flags}
    if perm_rule == "WITH_CONDITIONS":
        return {"allowed": False, "rights_status": "RIGHTS_UNCERTAIN", "basis": f"manifest:{perm}", "audit_category": audit_cat, "flags": flags}
    return {"allowed": False, "rights_status": perm_rule or "RIGHTS_UNKNOWN", "basis": f"manifest:{perm or 'missing'}", "audit_category": audit_cat, "flags": flags}


# ---------------------------------------------------------------------------
# Knowledge layer / religious scope / canonical status derivation
# ---------------------------------------------------------------------------
KNOWLEDGE_LAYER_MAP = {
    "CANONICAL": "CANONICAL_SCRIPTURE",
    "PRIMARY CANON": "CANONICAL_SCRIPTURE",
    "COMMENTARY": "COMMENTARY",
    "TEACHING": "TEACHER_INTERPRETATION",
    "LEXICON": "LEXICON",
    "SECONDARY SCHOLARSHIP": "SECONDARY_SCHOLARSHIP",
    "PRACTICE": "REFERENCE",
    "REFERENCE": "REFERENCE",
}
SCOPE_MAP = {
    "CORE_STHANAKAVASI": "CORE_STHANAKAVASI",
    "HIGH_STHANAKAVASI_RELEVANCE": "HIGH_STHANAKAVASI_RELEVANCE",
    "COMPARATIVE_OTHER_TRADITION": "COMPARATIVE_OTHER_TRADITION",
    "CONTEXTUAL_JAIN": "CONTEXTUAL_JAIN",
    "CANONICAL_FOUNDATION": "CONTEXTUAL_JAIN",
    "UNKNOWN": "UNKNOWN",
    "": "UNKNOWN",
}


def map_knowledge_layer(raw: str) -> str:
    """Map manifest knowledge_layer free text to sft_schema_v1 enum."""
    raw_u = (raw or "").upper()
    if not raw_u:
        return "MIXED"
    if "COMMENTARY" in raw_u:
        return "COMMENTARY"
    for key, val in KNOWLEDGE_LAYER_MAP.items():
        if key in raw_u:
            return val
    return "MIXED"


def map_religious_scope(raw: str) -> str:
    raw_u = (raw or "").strip().upper()
    if raw_u in SCOPE_MAP:
        return SCOPE_MAP[raw_u]
    for key, val in SCOPE_MAP.items():
        if key and key in raw_u:
            return val
    return "UNKNOWN"


def canonical_status(man: Dict[str, str]) -> str:
    """Derived canonical_status (manifest has no canonical_status column).

    Derivation table is published in sft_audit_v1.json -> derivations.
    """
    rel = (man.get("relation_type") or "").strip().lower()
    layer = (man.get("knowledge_layer") or "").upper()
    category = (man.get("text_category") or "").upper()
    if rel == "edition_of":
        return "EDITION_OF_CANONICAL"
    if rel in ("translation_of",):
        return "TRANSLATION_OF_CANONICAL"
    if rel == "commentary":
        return "COMMENTARY"
    if "PRIMARY CANON" in layer or "CANONICAL" in layer:
        return "CANONICAL"
    if "COMMENTARY" in layer:
        return "COMMENTARY"
    if "LEXICON" in layer:
        return "REFERENCE_LEXICON"
    if "SECONDARY" in layer:
        return "SECONDARY_SCHOLARSHIP"
    if "PRACTICE" in layer:
        return "PRACTICE_LITERATURE"
    if any(tok in category for tok in ("SUTRA", "AGAM", "ANGA", "SUTTAN")):
        return "CANONICAL"
    if any(tok in category for tok in ("DICTIONARY", "KOSH", "ENCYCLOPEDIA")):
        return "REFERENCE_LEXICON"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Text hygiene
# ---------------------------------------------------------------------------
_PUNCT_BLACKLIST = set("^~`#$%&{}[]<>|+=*\\/\"'‘’“”")


def ocr_noise_score(text: str) -> Dict[str, Any]:
    """Heuristic OCR noise measurement used by quality gate 11/6."""
    if not text:
        return {"score": 1.0, "hits": ["empty"]}
    hits: List[str] = []
    chars = [c for c in text if not c.isspace()]
    n = max(len(chars), 1)
    black = sum(1 for c in chars if c in _PUNCT_BLACKLIST)
    if black:
        hits.append(f"blacklist_chars={black}")
    inner_period = len(re.findall(r"[A-Za-z]\.[A-Za-z]", text))
    if inner_period >= 2:
        hits.append(f"inner_period={inner_period}")
    repl = text.count("�") + text.count("?")
    if text.count("�"):
        hits.append("replacement_char")
    alpha = sum(1 for c in chars if c.isalpha())
    ascii_letters = sum(1 for c in chars if ("a" <= c <= "z") or ("A" <= c <= "Z"))
    letters = [c for c in chars if c.isalpha()]
    non_ascii_alpha = [c for c in letters if ord(c) > 127]
    if letters and len(non_ascii_alpha) / max(len(letters), 1) > 0.5:
        # non-latin script: judge by devanagari/gujarati joining marks instead
        pass
    else:
        if alpha and ascii_letters / alpha < 0.9:
            hits.append("non_ascii_letters_in_latin_text")
    control = sum(1 for c in text
                  if unicodedata.category(c) == "Cc" and c not in "\n\t\r")
    if control:
        hits.append(f"control_chars={control}")
    long_runs = re.findall(r"[^\s]{12,}", text)
    noisy_runs = [t for t in long_runs if sum(ch.isdigit() for ch in t) > len(t) * 0.5]
    if noisy_runs:
        hits.append("digit_heavy_tokens")
    score = min(len(hits) * 0.25, 1.0)
    if black > 3 or text.count("?") > 3:
        score = max(score, 0.9)
    return {"score": round(score, 3), "hits": hits}


BOILERPLATE_PATTERNS = [
    r"public domain books",
    r"our gateways to the past",
    r"gutenberg",
    r"copyright term has expired",
    r"marks, notations and other",
    r"jain education international for private and personal use only",
    r"^page #\d+",
    r"^-{5,}",
    r"_{5,}",
    r"catalog link: https://jainqq\.org",
    r"^jainqq source svk-",
]


def is_boilerplate(text: str) -> bool:
    t = text.strip().lower()
    if not t:
        return True
    for pat in BOILERPLATE_PATTERNS:
        if re.search(pat, t):
            return True
    return False


def normalize_q(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "").lower()
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def shingles(text: str, k: int = 5) -> set:
    t = re.sub(r"\s+", " ", (text or "").lower()).strip()
    if len(t) < k:
        return {t} if t else set()
    return {t[i:i + k] for i in range(len(t) - k + 1)}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def make_example_id(source_id: str, category: str, payload: str) -> str:
    """Schema-v1 conforming id: ^[a-z0-9_-]+:[a-z0-9_-]+:[a-f0-9]{8}$"""
    slug = re.sub(r"[^a-z0-9_]+", "_", category.lower()).strip("_") or "qa"
    h = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:8]
    sid = source_id.lower()
    return f"{sid}:{slug}:{h}"


def load_units(wanted: Optional[set] = None, source_ids: Optional[set] = None) -> Dict[str, Dict[str, Any]]:
    """Index training corpus units by id.

    Records carry both ``id`` (release row id) and ``unit_id`` (segmented unit
    id used by the SFT candidate artifacts); both are indexed so either form
    resolves to the same record.
    """
    out: Dict[str, Dict[str, Any]] = {}
    seen = set()
    with open(CORPUS, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            uid = rec.get("id", "")
            unit_id = rec.get("unit_id", "")
            keys = {k for k in (uid, unit_id) if k}
            if wanted is not None:
                if not (keys & wanted):
                    if source_ids is not None and rec.get("source_id") not in source_ids:
                        continue
                    if source_ids is None:
                        continue
            for k in keys:
                out[k] = rec
            seen.add(uid)
            if wanted is not None and wanted <= set(out):
                break
    return out
