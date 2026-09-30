#!/usr/bin/env python3
"""TASK 61 stage 3 - build the SFT candidate pool and run the 13 quality gates.

Outputs (data/training):
    sft_candidates_v2.jsonl                     150-300 candidate records
    sft_abstention_candidates_v1.jsonl
    sft_sect_distinction_candidates_v1.jsonl
    sft_source_attribution_candidates_v1.jsonl
    sft_audit_v1.json                           machine-readable validation
The three special sets are subsets of sft_candidates_v2.jsonl (membership is
recorded in each record's "sets" field), so a reviewer can review one pool.

Nothing here trains, merges or deploys a model, and no record leaves with
human_review_status other than HUMAN_REVIEW_REQUIRED.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import builders_task61 as B  # noqa: E402
from task61_common import (  # noqa: E402
    CATEGORIES, CATEGORY_TO_TASK_CATEGORY, CLASS_D, CORPUS, ROOT, SFT_DIR,
    SFT_SCHEMA, canonical_status, is_boilerplate, jaccard, load_jainqq_evidence,
    load_manifest, load_rights_audit, load_split_map, make_example_id,
    map_knowledge_layer, map_religious_scope, normalize_q, ocr_noise_score,
    read_jsonl, rights_for, shingles, split_candidate, write_jsonl,
)

# --------------------------------------------------------------------------
# pool selection (what counts as usable evidence text)
# --------------------------------------------------------------------------
EN_SOURCES = {"SVK-0038", "SVK-1001", "SVK-1002", "SVK-1003", "SVK-1005",
              "SVK-1006", "SVK-1008", "SVK-0026", "SVK-1009"}
HI_SOURCES = {"SVK-0016", "SVK-2016", "SVK-2020"}
GU_SOURCES = {"SVK-2012", "SVK-2014", "SVK-1010", "SVK-2003"}
PRA_SOURCES = {"SVK-2008", "SVK-2009"}
GLOSS_SOURCES = {"SVK-1001", "SVK-1002", "SVK-1003"}
DEV_SOURCES = {"SVK-2020", "SVK-0016", "SVK-2015"}
JAINQQ_SOURCES = {"SVK-2022", "SVK-2023", "SVK-2024", "SVK-2025", "SVK-2026",
                  "SVK-2027", "SVK-2028", "SVK-2029"}
ANGA_SOURCES = {"SVK-1001", "SVK-1002", "SVK-1003", "SVK-2026", "SVK-1005"}
CCV_SOURCES = EN_SOURCES

CAPS = {
    "SOURCE_ATTRIBUTION": 40,
    "STHANAKAVASI_DISTINCTION": 20,
    "PRACTICE_EXPLANATION": 30,
    "AGAM_GROUNDED": 25,
    "STHANAKAVASI_TERMINOLOGY": 20,
    "PRAKRIT": 25,
    "HINDI": 30,
    "GUJARATI": 20,
    "SANSKRIT": 15,
    "GENERAL_JAIN_CONCEPT": 30,
    "CANONICAL_VS_COMMENTARY": 12,
    "ABSTENTION/INSUFFICIENT_EVIDENCE": 25,
}

POOL_RE = {
    "sect": re.compile(r"Sthanakavasi|Sthanakvas"),
    "sect_other": re.compile(r"Digambar|Svetambar|Svembar|Terapanth", re.I),
    "practice": re.compile(r"Samayik|Pratikram|Kayotsarg|Paryushan|Avashyak|Upavas|Ahimsa|\bTapa\b|\bvows?\b", re.I),
    "term": re.compile(r"Upasaro|Samayik|Nisahi|Vasahi|Mahapurusa|\bPujya\b|Mahasati|Samvegi|Garaniji|Rajono|Chedagrantha|Anuyogadv|Mithyatva|Sthanakavasi", re.I),
    "agam_text": re.compile(r"\bAngas?\b|Aṅga"),
    "prakrit": re.compile(r"Prakrit"),
    "gloss": re.compile(r"[A-Za-z]{3,}\s*=\s*[A-Za-z]{3,}|Sanskrit"),
    "hindi": re.compile(r"उत्तराध्ययन|प्रतिक्रमण|आगम|सूत्र|अहिंसा|तप|कर्म|विनय|मोक्ष|प्रश्न-उत्तर|समयिक|उपवास|व्रत|श्रमण|भगवान महावीर|जैन"),
    "gujarati": re.compile(r"સૂત્ર|આગમ|જૈન|તપ|કર્મ|અહિંસા|પ્રતિક્રમણ|મોક્ષ|વ્રત|શ્રમણ|ઉત્તરાધ્યયન"),
    "devanagari": re.compile(r"सूत्र|उपवास|कर्म|विनय|श्रमण|महावीर"),
    "general": re.compile(r"Jain|Jaina"),
    "ccv": re.compile(r"commentar|scriptures were written"),
}

GATES = [
    ("gate_01_schema_validity", "record validates against sft_schema_v1.json and carries every TASK 61 field"),
    ("gate_02_missing_text", "question and answer text present"),
    ("gate_03_empty_answer", "assistant answer non-empty and long enough to train on"),
    ("gate_04_missing_provenance", "source_id, text_id, knowledge_layer and religious_scope present"),
    ("gate_05_missing_source", "source_id resolves to a source_manifest.csv row"),
    ("gate_06_duplicate_question", "normalized question not already used in the pool or approved inventory"),
    ("gate_07_near_duplicate_answer", "answer not a near-duplicate (5-shingle Jaccard < 0.85) of an earlier record"),
    ("gate_08_unsupported_source_citation", "every quoted claim occurs in the cited unit / manifest row"),
    ("gate_09_teacher_attribution_mismatch", "named teacher or author appears in the cited source's manifest record or unit"),
    ("gate_10_practice_not_in_source", "practice named in the candidate appears in the cited unit"),
    ("gate_11_sect_mismatch", "Sthanakavasi claim is backed by the unit or the manifest scope/sect"),
    ("gate_12_canonical_commentary_mismatch", "canonical_status matches the manifest relation/layer derivation"),
    ("gate_13_rights_violation", "source is rights-cleared for SFT training"),
]


def unit_quality_ok(rec, allow_boilerplate=False):
    q = rec.get("quality") or {}
    t = rec.get("text", "")
    if not (50 <= len(t) <= 1600):
        return False
    if not allow_boilerplate and is_boilerplate(t):
        return False
    if allow_boilerplate:
        # structured catalog header: the noise heuristics flag the URL line,
        # while the manifest/duplicate checks below still apply
        return True
    noise = q.get("ocr_noise_estimate")
    if noise is not None and noise > 0.30:
        return False
    esr = q.get("expected_script_ratio")
    if esr is not None and esr < 0.70:
        return False
    dup = (q.get("duplicate") or {}).get("status")
    if dup not in (None, "UNIQUE"):
        return False
    if ocr_noise_score(t)["score"] >= 0.5:
        return False
    return True


def unit_entry(rec):
    return {
        "corpus_id": rec.get("id", ""),
        "unit_id": rec.get("unit_id") or rec.get("id", ""),
        "source_id": rec.get("source_id", ""),
        "text": rec.get("text", ""),
        "section": rec.get("section") or (rec.get("source_locator") or {}).get("section") or "",
        "locator": rec.get("source_locator") or {},
        "language": rec.get("language", ""),
        "quality": rec.get("quality") or {},
    }


def corpus_pass(allowed):
    """Single pass: category pools + abstention scans + anchors."""
    pools = defaultdict(list)
    scans = Counter()
    anchors = {}
    known_hits = {}
    unit_texts = {}
    cases = B.ABSTENTION_CASES
    case_scan = [(c["id"], re.compile(c["scan"], re.I)) for c in cases if c.get("scan")]
    case_known = [(c["id"], re.compile(c["known_scan"], re.I)) for c in cases if c.get("known_scan")]
    case_topic = []
    for c in cases:
        if c.get("scan"):
            m = re.search(r"[A-Za-z]{5,}", c["scan"])
            if m:
                case_topic.append((c["id"], re.compile(re.escape(m.group(0)), re.I)))
    with open(CORPUS, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            sid = rec.get("source_id", "")
            text = rec.get("text", "")
            is_header = bool(re.search(r"Book Title:|Author\(s\):", text)) and sid in JAINQQ_SOURCES
            if sid not in allowed and not is_header:
                # still need corpus-wide absence scans
                for cid, pat in case_scan:
                    if pat.search(text):
                        scans[cid] += 1
                continue
            for cid, pat in case_scan:
                if pat.search(text):
                    scans[cid] += 1
            if sid in allowed:
                ok = unit_quality_ok(rec, allow_boilerplate=is_header)
                if ok:
                    e = unit_entry(rec)
                    unit_texts[e["unit_id"]] = text
                    if is_header:
                        pools["agam_header"].append(e)
                    elif (sid in EN_SOURCES or sid in JAINQQ_SOURCES) and \
                            POOL_RE["sect"].search(text):
                        pools["sect"].append(e)
                    elif sid in EN_SOURCES and POOL_RE["practice"].search(text):
                        pools["practice"].append(e)
                    if sid in EN_SOURCES and POOL_RE["term"].search(text):
                        pools["term"].append(e)
                    if is_header is False and sid in JAINQQ_SOURCES and POOL_RE["term"].search(text):
                        pools["term"].append(e)
                    if sid in ANGA_SOURCES and POOL_RE["agam_text"].search(text):
                        pools["agam_text"].append(e)
                    if sid in PRA_SOURCES and POOL_RE["prakrit"].search(text):
                        pools["prakrit"].append(e)
                    if sid in GLOSS_SOURCES and POOL_RE["gloss"].search(text):
                        pools["gloss"].append(e)
                    if sid in HI_SOURCES and POOL_RE["hindi"].search(text):
                        pools["hindi"].append(e)
                    if sid in GU_SOURCES and POOL_RE["gujarati"].search(text):
                        pools["gujarati"].append(e)
                    if sid in DEV_SOURCES and POOL_RE["devanagari"].search(text):
                        pools["devanagari"].append(e)
                    if sid in EN_SOURCES and POOL_RE["general"].search(text):
                        pools["general"].append(e)
                    if sid in CCV_SOURCES and POOL_RE["ccv"].search(text):
                        pools["ccv"].append(e)
                for cid, pat in case_known:
                    if cid not in known_hits and pat.search(text) and unit_quality_ok(rec):
                        uid = rec.get("unit_id") or rec.get("id", "")
                        known_hits[cid] = {"quote": " ".join(text.split())[:400],
                                           "source_id": sid, "unit_id": uid,
                                           "corpus_id": rec.get("id", "")}
                        unit_texts[uid] = text
            for cid, pat in case_topic:
                if cid not in anchors and pat.search(text) and sid in allowed and unit_quality_ok(rec):
                    uid = rec.get("unit_id") or rec.get("id", "")
                    anchors[cid] = {"quote": " ".join(text.split())[:400], "source_id": sid,
                                    "unit_id": uid, "corpus_id": rec.get("id", "")}
                    unit_texts[uid] = text
    return pools, scans, anchors, known_hits, unit_texts


# --------------------------------------------------------------------------
# draft -> full candidate record
# --------------------------------------------------------------------------
TASK61_REQUIRED_FIELDS = [
    "example_id", "question", "answer", "messages", "category", "source_id",
    "parent_source_id", "source_title", "locator", "religious_scope",
    "knowledge_layer", "teacher_or_author", "lineage", "canonical_status",
    "provenance", "rights_status", "origin", "split_candidate",
    "human_review_status",
]

SECT_CONF_MAP = {"confirmed": "HIGH", "high": "HIGH", "medium": "MEDIUM",
                 "low": "LOW", "unknown": "UNKNOWN"}
QUALITY_MAP = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}


def schema_split(split_raw: str) -> str:
    return {"train": "train", "validation": "validation", "test": "test"}.get(split_raw, "train")


LANG_NORM = {
    "en": "en", "english": "en", "hi": "hi", "hindi": "hi",
    "gu": "gu", "gujarati": "gu", "sa": "sa", "sanskrit": "sa",
    "pra": "pra", "prakrit": "pra", "maharashtri prakrit": "pra",
    "prakriti": "pra", "fr": "fr", "french": "fr", "pali": "pi",
    "ap": "pra", "maha": "pra",
}


def norm_lang(lang: str, manifest_lang: str) -> str:
    raw = (lang or "").strip().lower()
    if raw in LANG_NORM:
        return LANG_NORM[raw]
    first = (manifest_lang or "").split(";")[0].strip().lower()
    return LANG_NORM.get(first, "en" if not raw else raw)


def to_record(d, review_id, man, rights_of, split_of):
    sid = d["source_id"]
    m = man.get(sid, {})
    rights = rights_of(sid)
    split_raw = split_candidate(sid, split_of)
    question, answer = d["question"], d["answer"]
    example_id = make_example_id(sid, d["category"],
                                 "%s|%s|%s" % (question, d["quote"] or answer, review_id))
    unit_id = d["unit_id"] or ("manifest:%s" % sid)
    layer = map_knowledge_layer(m.get("knowledge_layer", ""))
    scope = map_religious_scope(m.get("religious_scope", ""))
    author = (m.get("author") or "").strip()
    teacher = (m.get("teacher_or_author") or "").strip() or author
    page = d["locator"].get("page") if isinstance(d["locator"], dict) else None
    try:
        page = int(page) if page not in (None, "", "None") else None
    except (TypeError, ValueError):
        page = None
    section = None
    if isinstance(d["locator"], dict):
        section = d["locator"].get("section") or None
    if not section:
        section = d["section"] or None
    method = "synthetic_abstention" if d["category"].startswith("ABSTENTION") \
        else "synthetic_qa_generation"
    qt = d["question_type"]
    if qt not in ("factual", "definitional", "explanatory", "comparative",
                  "citation_only", "abstention", "multilingual_bridge"):
        qt = "factual"
    meta = {
        "answer_type": qt,
        "sect_relevant": scope in ("CORE_STHANAKAVASI", "HIGH_STHANAKAVASI_RELEVANCE")
        or d["category"] in ("STHANAKAVASI_DISTINCTION", "STHANAKAVASI_TERMINOLOGY")
        or bool(re.search(r"Sthanakavasi|Sthanakvas", question, re.I)),
        "cross_tradition": d["category"] == "STHANAKAVASI_DISTINCTION",
        "conflicting_sources": False,
    }
    if d["language"] in ("pra", "sa") or d["category"] in ("PRAKRIT", "SANSKRIT"):
        meta["language_pairs"] = ["pra-en" if d["category"] == "PRAKRIT" else "sa-en"]
    if d["extra"].get("prakrit_term"):
        meta["prakrit_term"] = d["extra"]["prakrit_term"]
    if d["extra"].get("sanskrit_term"):
        meta["prakrit_term"] = d["extra"]["sanskrit_term"]
    if d["category"] == "CANONICAL_VS_COMMENTARY":
        meta["canonical_reference"] = (m.get("title") or sid)
    prov = {
        "source_id": sid,
        "text_id": unit_id,
        "unit_ids": [unit_id] if d["unit_id"] else [],
        "title": m.get("title", ""),
        "author": author,
        "publication_year": m.get("publication_year", ""),
        "language": m.get("language", ""),
        "knowledge_layer": layer,
        "religious_scope": scope,
        "sect": m.get("sect", ""),
        "sect_confidence": SECT_CONF_MAP.get(
            (m.get("sect_confidence") or "").strip().lower(), "UNKNOWN"),
        "teacher_or_author": teacher,
        "lineage": m.get("lineage", ""),
        "source_quality": QUALITY_MAP.get(
            (m.get("source_quality") or "").strip().lower(), "UNKNOWN"),
        "locator": {"page": page, "section": section},
        "license_status": rights.get("rights_status", ""),
        "citation_text": "%s (%s)" % (m.get("title", ""), sid),
    }
    rec = {
        "example_id": example_id,
        "review_id": review_id,
        "version": "1.0",
        "task_category": d["task_category"],
        "category": d["category"],
        "question": question,
        "answer": answer,
        "messages": [{"role": "user", "content": question},
                     {"role": "assistant", "content": answer}],
        "source_id": sid,
        "parent_source_id": m.get("parent_source_id", ""),
        "source_title": m.get("title", ""),
        "locator": {"page": page, "section": section},
        "religious_scope": scope,
        "knowledge_layer": layer,
        "teacher_or_author": teacher,
        "lineage": m.get("lineage", ""),
        "canonical_status": canonical_status(m),
        "provenance": prov,
        "rights_status": rights.get("rights_status", ""),
        "rights_basis": rights.get("basis", ""),
        "rights_audit_category": rights.get("audit_category", ""),
        "rights_flags": rights.get("flags", []),
        "origin": {"synthetic": True, "method": method, "confidence": "medium"},
        "split": schema_split(split_raw),
        "split_candidate": split_raw,
        "human_review_status": "HUMAN_REVIEW_REQUIRED",
        "curation_class": CLASS_D,
        "sets": d["sets"],
        "language": d["language"],
        "question_type": d["question_type"],
        "answer_metadata": meta,
        "citations": [{"source_id": sid, "unit_id": unit_id,
                       "locator": {"page": page, "section": section},
                       "excerpt": d["quote"][:400] if d["quote"] else ""}],
        "evidence": {
            "manifest_grounded": bool(d["manifest_grounded"]),
            "quote": d["quote"],
            "unit_text": d["unit_text"][:2000],
            "extra": d["extra"],
        },
        "tags": [d["category"].lower(), (m.get("language") or "").split(";")[0].strip(), sid],
        "quality_flags": ["needs_review", "synthetic_unverified"],
    }
    if d.get("question_hi"):
        rec["question_hi"] = d["question_hi"]
    rec["language"] = norm_lang(d["language"], m.get("language", ""))
    rec["citations"][0]["source_url"] = m.get("source_url", "")
    return rec


# --------------------------------------------------------------------------
# the 13 quality gates
# --------------------------------------------------------------------------
QUOTE_RE = re.compile(r"\"([^\"%s]{25,})\"" % "")


def _squeeze(t):
    return "".join((t or "").split())


def _quoted_spans(answer):
    return re.findall(r"\"([^\"\n]{25,})\"", answer or "")


def _years(text):
    return set(re.findall(r"(?<![\d:])(?:18|19|20)\d{2}(?![\d])", text or ""))


def _teacher_names(man):
    names = set()
    for m in man.values():
        for field in ("author", "teacher_or_author"):
            raw = m.get(field) or ""
            for part in re.split(r",|;|\band\b", raw):
                part = " ".join(part.split()).strip()
                if len(part) >= 5 and part.lower() not in ("unknown", "multiple", "anonymous"):
                    names.add(part)
    for extra_name in ("Amarmuni", "Pravin K Shah", "Shayyambhavsuri", "Shreechand Surana"):
        names.add(extra_name)
    return {n for n in names if len(n) >= 5}


def run_gates(records, man, rights_of, unit_texts, scans, verified_questions,
              rejected_questions, schema_path):
    """Evaluate all 13 gates independently on every record.

    A record only enters the pool when it passes every gate; per-gate counters
    are updated for every record so the audit reports honest per-gate rates.
    """
    import jsonschema
    with open(schema_path, encoding="utf-8") as fh:
        schema = json.load(fh)
    teacher_names = sorted(_teacher_names(man), key=len, reverse=True)
    gate_state = {gid: {"passed": 0, "failed": 0, "failures": []}
                  for gid, _ in GATES}
    seen_q = {}
    accepted_answers = []
    passed, failed_records = [], []

    def note(gid, rec, reason):
        st = gate_state[gid]
        st["failed"] += 1
        if len(st["failures"]) < 200:
            st["failures"].append({
                "example_id": rec.get("example_id", ""),
                "review_id": rec.get("review_id", ""),
                "category": rec.get("category", ""),
                "reason": reason,
            })
        return (gid, reason)

    def all_good(gid_list):
        for gid in gid_list:
            gate_state[gid]["passed"] += 1

    for rec in records:
        q = rec.get("question", "")
        a = rec.get("answer", "")
        sid = rec.get("source_id", "")
        m = man.get(sid, {})
        ev = rec.get("evidence", {})
        prov = rec.get("provenance") or {}
        full_unit = unit_texts.get(prov.get("text_id", ""), ev.get("unit_text", ""))
        failures = []
        cat = rec.get("category", "")
        is_abstention = cat.startswith("ABSTENTION")
        nq = normalize_q(q)

        # 1 - schema validity + Task 61 required fields
        g = []
        missing = [f for f in TASK61_REQUIRED_FIELDS if f not in rec]
        if missing:
            g.append("missing Task 61 fields: %s" % ",".join(missing))
        else:
            try:
                jsonschema.validate(rec, schema)
            except jsonschema.ValidationError as exc:
                g.append(exc.message[:180])
        if g:
            failures.append(note("gate_01_schema_validity", rec, "; ".join(g)))
        else:
            all_good(["gate_01_schema_validity"])

        # 2 - missing text
        if not q.strip() or not a.strip() or any(
                not (msg.get("content") or "").strip()
                for msg in rec.get("messages", [])):
            failures.append(note("gate_02_missing_text", rec,
                                 "empty question/answer/message content"))
        else:
            all_good(["gate_02_missing_text"])

        # 3 - empty answer
        if len(a.strip()) < 40:
            failures.append(note("gate_03_empty_answer", rec,
                                 "answer shorter than 40 chars (%d)" % len(a.strip())))
        else:
            all_good(["gate_03_empty_answer"])

        # 4 - missing provenance
        g = [k for k in ("source_id", "text_id", "knowledge_layer", "religious_scope")
             if not str(prov.get(k, "")).strip()]
        if g:
            failures.append(note("gate_04_missing_provenance", rec,
                                 "provenance missing %s" % ",".join(g)))
        elif prov.get("knowledge_layer") != map_knowledge_layer(
                m.get("knowledge_layer", "")) or prov.get(
                "religious_scope") != map_religious_scope(m.get("religious_scope", "")):
            failures.append(note("gate_04_missing_provenance", rec,
                                 "provenance values differ from manifest derivation"))
        else:
            all_good(["gate_04_missing_provenance"])

        # 5 - missing source
        if sid not in man:
            failures.append(note("gate_05_missing_source", rec,
                                 "source_id %s not in source_manifest.csv" % sid))
        else:
            all_good(["gate_05_missing_source"])

        # 6 - duplicate question (pool-internal, approved inventory, rejected list)
        g = []
        if nq in seen_q:
            g.append("same normalized question as %s" % seen_q[nq])
        elif nq in verified_questions:
            g.append("duplicates an existing HUMAN_VERIFIED question")
        elif nq in rejected_questions:
            g.append("duplicates a human-rejected question")
        if g:
            failures.append(note("gate_06_duplicate_question", rec, "; ".join(g)))
        else:
            seen_q[nq] = rec.get("example_id", "")
            all_good(["gate_06_duplicate_question"])

        # 7 - near-duplicate answer
        sh = shingles(a)
        dup_of = next((pid for pid, psh in accepted_answers
                       if jaccard(sh, psh) >= 0.85), None)
        if dup_of:
            failures.append(note("gate_07_near_duplicate_answer", rec,
                                 "5-shingle Jaccard >= 0.85 with %s" % dup_of))
        else:
            all_good(["gate_07_near_duplicate_answer"])

        # 8 - unsupported source citation
        g = []
        if is_abstention:
            absence = ev.get("extra", {}).get("absence_check") or {}
            cid = absence.get("case_id", "")
            if cid and scans.get(cid, 0) != 0:
                g.append("absence scan for %s matches %d corpus units"
                         % (cid, scans.get(cid, 0)))
            if not cid and not ev.get("manifest_grounded"):
                g.append("absence case id missing from candidate")
            if ev.get("manifest_grounded"):
                gap = absence.get("manifest_gap") or ev.get("extra", {}).get("manifest_gap")
                if gap:
                    field, sids = gap[0], gap[1]
                    vals = [(man.get(x, {}).get(field) or "").strip().lower()
                            for x in sids if x in man]
                    if any(v and v not in ("unknown", "not recorded", "n/a", "none")
                           for v in vals):
                        g.append("manifest field %s is populated for %s" % (field, sids))
                elif not absence:
                    g.append("manifest_gap abstention lacks absence_check")
        elif ev.get("manifest_grounded"):
            row_vals = " ".join(str(v) for v in m.values())
            if m.get("title") and _squeeze(m["title"]).lower() not in _squeeze(a).lower():
                g.append("manifest title absent from answer")
            pid = (m.get("parent_source_id") or "").strip()
            parent_vals = " ".join(str(v) for v in man.get(pid, {}).values()) if pid else ""
            allowed_years = set(re.findall(r"(?:18|19|20)\d{2}", row_vals + " " + parent_vals))
            bad_years = sorted(y for y in _years(a) if y not in allowed_years)
            if bad_years:
                g.append("years not attested in any manifest field: %s"
                         % ",".join(bad_years))
            mm = re.search(r"written by ([^.]+?)(?: in \d{4})?(?:\.| It is)", a)
            if mm and (m.get("author") or "").lower().find(
                    mm.group(1).strip().lower()) < 0:
                g.append("author claim %r not in manifest author %r"
                         % (mm.group(1).strip(), m.get("author", "")))
            pm = re.search(r"published by ([^;.()]+?)(?:;| in \d{4}|\.|,| \()", a)
            if pm and (m.get("publisher") or "").lower().find(
                    pm.group(1).strip().lower()) < 0:
                g.append("publisher claim not in manifest")
            rm = re.search(r"relation_type (\w+)", a)
            if rm and rm.group(1).lower() != (m.get("relation_type") or "").lower():
                g.append("relation_type claim differs from manifest")
        else:
            if not full_unit:
                g.append("no cited unit text available for verification")
            else:
                bad_spans = [sp for sp in _quoted_spans(a)
                             if _squeeze(sp) not in _squeeze(full_unit)]
                if bad_spans:
                    g.append("quoted span not found in cited unit: %r"
                             % bad_spans[0][:80])
        if g:
            failures.append(note("gate_08_unsupported_source_citation", rec,
                                 "; ".join(g)))
        else:
            all_good(["gate_08_unsupported_source_citation"])

        # 9 - teacher attribution mismatch
        low_all = (q + " " + a).lower()
        man_people = ((m.get("author") or "") + " " +
                      (m.get("teacher_or_author") or "")).lower()
        bad_name = None
        for name in teacher_names:
            if name.lower() in low_all and name.lower() not in man_people \
                    and _squeeze(name).lower() not in _squeeze(full_unit).lower():
                bad_name = name
                break
        if bad_name:
            failures.append(note("gate_09_teacher_attribution_mismatch", rec,
                                 "teacher/author %r not in cited source manifest or unit"
                                 % bad_name))
        else:
            all_good(["gate_09_teacher_attribution_mismatch"])

        # 10 - practice not in source
        extra = ev.get("extra") or {}
        practice = extra.get("practice")
        if practice and cat == "PRACTICE_EXPLANATION":
            pattern = extra.get("practice_pattern")
            if pattern:
                hit = bool(re.search(pattern, full_unit, re.I))
            else:
                display = practice.split(" (")[0]
                toks = [t for t in re.split(r"\s+", display) if len(t) >= 4]
                hit = bool(toks) and any(
                    re.search(re.escape(t), full_unit, re.I) for t in toks)
            if not hit:
                failures.append(note("gate_10_practice_not_in_source", rec,
                                     "practice %r not found in cited unit" % practice))
            else:
                all_good(["gate_10_practice_not_in_source"])
        else:
            all_good(["gate_10_practice_not_in_source"])

        # 11 - sect mismatch
        if re.search(r"Sthanakavasi|Sthanakvas", q + " " + a, re.I) and not is_abstention:
            scope = map_religious_scope(m.get("religious_scope", ""))
            sect_field = (m.get("sect") or "") + " " + (m.get("subsect") or "")
            backed = bool(re.search(r"Sthanakavasi|Sthanakvas", full_unit, re.I)) \
                or scope in ("CORE_STHANAKAVASI", "HIGH_STHANAKAVASI_RELEVANCE") \
                or bool(re.search(r"Sthanakavasi|Sthanakvas", sect_field, re.I)) \
                or ev.get("manifest_grounded") \
                or cat in ("STHANAKAVASI_DISTINCTION", "STHANAKAVASI_TERMINOLOGY")
            if not backed:
                failures.append(note("gate_11_sect_mismatch", rec,
                                     "Sthanakavasi claim not backed by unit or manifest "
                                     "scope/sect"))
            else:
                all_good(["gate_11_sect_mismatch"])
        else:
            all_good(["gate_11_sect_mismatch"])

        # 12 - canonical/commentary mismatch
        g = []
        if rec.get("canonical_status") != canonical_status(m):
            g.append("record canonical_status %r != derived %r"
                     % (rec.get("canonical_status"), canonical_status(m)))
        if cat == "CANONICAL_VS_COMMENTARY":
            rel = (m.get("relation_type") or "").strip().lower()
            layer = (m.get("knowledge_layer") or "").lower()
            if not (rel or "comment" in layer or _quoted_spans(a)):
                g.append("no relation_type/knowledge_layer/commentary evidence")
        if g:
            failures.append(note("gate_12_canonical_commentary_mismatch", rec,
                                 "; ".join(g)))
        else:
            all_good(["gate_12_canonical_commentary_mismatch"])

        # 13 - rights violation
        rights = rights_of(sid)
        if not rights.get("allowed"):
            failures.append(note("gate_13_rights_violation", rec,
                                 "rights not cleared: %s"
                                 % rights.get("rights_status", "")))
        else:
            all_good(["gate_13_rights_violation"])

        if failures:
            failed_records.append({
                "example_id": rec.get("example_id", ""),
                "review_id": rec.get("review_id", ""),
                "category": cat,
                "question": q[:200],
                "failed_gates": [{"gate": gid, "reason": reason}
                                 for gid, reason in failures],
            })
        else:
            accepted_answers.append((rec.get("example_id", ""), sh))
            passed.append(rec)

    return passed, failed_records, gate_state

# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main():
    t0 = time.time()
    print("TASK 61 stage 3: build candidate pool + 13 quality gates")

    manifest = load_manifest()
    audit_rights = load_rights_audit()
    jainqq = load_jainqq_evidence()
    split_of = load_split_map()

    def rights_of(sid):
        return rights_for(sid, manifest, audit_rights, jainqq)

    allowed = {sid for sid in manifest if rights_of(sid)["allowed"]}
    print("rights-cleared sources: %d / %d" % (len(allowed), len(manifest)))

    pools, scans, anchors, known_hits, unit_texts = corpus_pass(allowed)
    print("pool units: " + ", ".join("%s=%d" % (k, len(v))
                                     for k, v in sorted(pools.items())))
    scan_hits = {k: v for k, v in scans.items() if v}
    print("abstention absence scans that matched corpus (cases dropped): %s"
          % (scan_hits or "none"))

    drafts = []
    drafts += B.build_source_attribution(manifest, allowed, pools.get("agam_header", []),
                                         CAPS["SOURCE_ATTRIBUTION"])
    drafts += B.build_sect(pools.get("sect", []), manifest, CAPS["STHANAKAVASI_DISTINCTION"])
    drafts += B.build_practice(pools.get("practice", []), manifest, CAPS["PRACTICE_EXPLANATION"])
    drafts += B.build_agam(pools.get("agam_header", []), pools.get("agam_text", []),
                           manifest, CAPS["AGAM_GROUNDED"])
    drafts += B.build_terminology(pools.get("term", []), manifest,
                                  CAPS["STHANAKAVASI_TERMINOLOGY"])
    drafts += B.build_prakrit(pools.get("prakrit", []), pools.get("gloss", []),
                              manifest, CAPS["PRAKRIT"])
    drafts += B.build_hindi(pools.get("hindi", []), manifest, CAPS["HINDI"])
    drafts += B.build_gujarati(pools.get("gujarati", []), manifest, CAPS["GUJARATI"])
    drafts += B.build_sanskrit(pools.get("gloss", []), pools.get("devanagari", []),
                               manifest, CAPS["SANSKRIT"])
    drafts += B.build_general(pools.get("general", []), manifest,
                              CAPS["GENERAL_JAIN_CONCEPT"])
    drafts += B.build_canonical_vs_commentary(manifest, allowed, pools.get("ccv", []),
                                              CAPS["CANONICAL_VS_COMMENTARY"])
    abst_drafts, abst_dropped = B.build_abstention(
        B.ABSTENTION_CASES, scans, anchors, known_hits, manifest, allowed)
    drafts += abst_drafts
    print("drafts: %d (abstention %d, dropped abstention cases %d)"
          % (len(drafts), len(abst_drafts), len(abst_dropped)))
    print("drafts by category: %s"
          % dict(sorted(Counter(d["category"] for d in drafts).items())))

    records = [to_record(d, "T61-CAND-%04d" % (i + 1), manifest, rights_of, split_of)
               for i, d in enumerate(drafts)]
    # drop exact example_id collisions
    seen_ids, unique_records = set(), []
    for rec in records:
        if rec["example_id"] in seen_ids:
            rec["example_id"] = make_example_id(rec["source_id"], rec["category"],
                                                rec["example_id"] + rec["review_id"])
        seen_ids.add(rec["example_id"])
        unique_records.append(rec)
    records = unique_records

    # existing human decisions for gate 6
    reconciled = read_jsonl(os.path.join(SFT_DIR, "sft_reconciled_v1.jsonl"))
    verified_q = {normalize_q(r.get("question", "")) for r in reconciled
                  if r.get("question")}
    existing_audit_path = os.path.join(SFT_DIR, "_task61_existing_candidates_audit.json")
    rejected_q = set()
    if os.path.exists(existing_audit_path):
        with open(existing_audit_path, encoding="utf-8") as fh:
            existing = json.load(fh)
        for row in existing.get("records", []):
            if row.get("class") in ("HUMAN_REJECTED", "HUMAN_REVISE_REQUIRED") and row.get("question"):
                rejected_q.add(normalize_q(row["question"]))

    passed, failed_records, gate_state = run_gates(
        records, manifest, rights_of, unit_texts, scans, verified_q, rejected_q,
        SFT_SCHEMA)

    print("records evaluated: %d | passed all 13 gates: %d | failed: %d"
          % (len(records), len(passed), len(failed_records)))
    for gid, desc in GATES:
        st = gate_state[gid]
        print("  %-38s passed=%-4d failed=%d" % (gid, st["passed"], st["failed"]))

    by_cat_passed = Counter(r["category"] for r in passed)
    if not (150 <= len(passed) <= 300):
        print("WARNING: pool size %d outside required 150-300 range" % len(passed))

    # ---- write pool files ------------------------------------------------
    out_v2 = os.path.join(SFT_DIR, "sft_candidates_v2.jsonl")
    write_jsonl(out_v2, passed)
    subsets = {
        "sft_abstention_candidates_v1.jsonl": "abstention_set",
        "sft_sect_distinction_candidates_v1.jsonl": "sect_distinction",
        "sft_source_attribution_candidates_v1.jsonl": "source_attribution",
    }
    for fname, setname in subsets.items():
        rows = [r for r in passed if setname in (r.get("sets") or [])]
        write_jsonl(os.path.join(SFT_DIR, fname), rows)
        print("wrote %s (%d rows)" % (fname, len(rows)))

    # ---- audit ------------------------------------------------------------
    rec_summary_path = os.path.join(SFT_DIR, "_task61_reconciliation_summary.json")
    rec_summary = {}
    if os.path.exists(rec_summary_path):
        with open(rec_summary_path, encoding="utf-8") as fh:
            rec_summary = json.load(fh)

    def _counts(rows, key):
        return dict(sorted(Counter(r.get(key, "") for r in rows).items()))

    abstention_dropped = abst_dropped
    for cid, n in scan_hits.items():
        if not any(d["id"] == cid for d in abstention_dropped):
            abstention_dropped.append({"id": cid,
                                       "reason": "absence scan matched %d corpus units" % n,
                                       "pattern": next(
                                           (c["scan"] for c in B.ABSTENTION_CASES
                                            if c["id"] == cid), "")})

    schema_fail_examples = [f for f in failed_records
                            if any(g["gate"] == "gate_01_schema_validity"
                                   for g in f["failed_gates"])]
    pool_stats = {
        "count": len(passed),
        "by_category": _counts(passed, "category"),
        "by_task_category": _counts(passed, "task_category"),
        "by_split": _counts(passed, "split"),
        "by_split_candidate": _counts(passed, "split_candidate"),
        "by_language": _counts(passed, "language"),
        "by_source": _counts(passed, "source_id"),
        "by_rights_status": _counts(passed, "rights_status"),
        "by_knowledge_layer": _counts(passed, "knowledge_layer"),
        "by_religious_scope": _counts(passed, "religious_scope"),
        "by_human_review_status": _counts(passed, "human_review_status"),
    }

    report = {
        "task": 61,
        "stage": "sft_candidate_validation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": ["reconciliation (stage 1)", "existing-candidate audit (stage 2)",
                     "candidate build + 13 gates (stage 3)"],
        "reconciliation_summary": rec_summary,
        "existing_candidate_audit": {
            "file": "data/training/_task61_existing_candidates_audit.json",
            "unique_candidates_audited": existing.get("unique_candidates_audited") if os.path.exists(existing_audit_path) else None,
            "class_counts": existing.get("class_counts") if os.path.exists(existing_audit_path) else None,
            "class_definitions": existing.get("class_definitions") if os.path.exists(existing_audit_path) else None,
        },
        "candidate_pool": pool_stats,
        "gates": {
            gid: {"description": desc,
                  "passed": gate_state[gid]["passed"],
                  "failed": gate_state[gid]["failed"],
                  "failure_examples": gate_state[gid]["failures"]}
            for gid, desc in GATES
        },
        "gate_totals": {
            "records_evaluated": len(records),
            "records_passed_all_gates": len(passed),
            "records_failed_at_least_one_gate": len(failed_records),
            "total_gate_failures": sum(g["failed"] for g in gate_state.values()),
        },
        "failed_records": failed_records,
        "excluded_drafts": {
            "abstention_cases_dropped": abstention_dropped,
            "reason": "abstention case kept only when its absence scan matches 0 corpus units "
                      "and a rights-cleared anchor source exists",
        },
        "pool_within_required_range": 150 <= len(passed) <= 300,
        "required_range": [150, 300],
        "human_review_status_of_all_pool_records": "HUMAN_REVIEW_REQUIRED",
        "known_limitations": [
            "All pool records are synthetic drafts requiring human review; none carry HUMAN_VERIFIED.",
            "SANSKRIT candidates are Sanskrit/Prakrit term glosses found in English sources plus "
            "Devanagari units from sources whose manifest language is not sa (see language_note).",
            "Manifest-grounded candidates (source_attribution, canonical_vs_commentary) cite "
            "source_manifest.csv fields; provenance.text_id is manifest:<source_id> because these "
            "claims are source-level, not unit-level.",
            "JainQQ sources (SVK-2022..2029) carry MANIFEST_RIGHTS_STALE: manifest still says "
            "NEEDS_PERMISSION while jainqq_permission_evidence_v1.json grants SFT scope.",
            "SVK-2030..2037 rely on legacy manifest permission column + license=TRAINING_ALLOWED "
            "(flags LEGACY_PERMISSION_COLUMN, RIGHTS_AUDIT_NOT_COVERED).",
            "Split leakage note: seed/gold candidates and several pool records come from "
            "domain_train val/test sources (SVK-2022..2029); split_candidate records this per record.",
            "Abstention cases whose absence scan matched corpus units were dropped, not rewritten.",
        ],
        "outputs": {
            "candidates": "data/training/sft_candidates_v2.jsonl",
            "abstention_set": "data/training/sft_abstention_candidates_v1.jsonl",
            "sect_set": "data/training/sft_sect_distinction_candidates_v1.jsonl",
            "attribution_set": "data/training/sft_source_attribution_candidates_v1.jsonl",
            "reconciled": "data/training/sft_reconciled_v1.jsonl",
            "reconciliation_table": "data/training/sft_reconciliation_table.csv",
            "report": "data/reports/task61_sft_reconciliation.md",
        },
        "elapsed_seconds": round(time.time() - t0, 1),
    }
    audit_path = os.path.join(SFT_DIR, "sft_audit_v1.json")
    with open(audit_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False, sort_keys=False)
    print("wrote sft_audit_v1.json (%d bytes)" % os.path.getsize(audit_path))
    print("wrote sft_candidates_v2.jsonl (%d rows)" % len(passed))
    print("done in %.1fs" % (time.time() - t0))
    return 0 if report["pool_within_required_range"] else 2


if __name__ == "__main__":
    sys.exit(main())
