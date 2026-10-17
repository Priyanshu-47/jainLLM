#!/usr/bin/env python3
"""TASK 67 stage 1: build the SFT-02 train/eval dataset (NO TRAINING).

Inputs (read-only):
    data/training/sft_gold_v4_candidates.jsonl     54 Task-63 APPROVE rows
    data/training/sft_train_v1.jsonl               5 HUMAN_VERIFIED rows (selected ids)
    data/training/sft_verified_candidate_pool_v1.jsonl  practice-tagged units
    data/release/training_corpus.jsonl             unit texts (grounding)
    manifests/source_manifest.csv                  source metadata
    data/rights/jain_source_rights_audit_v1.json   rights decisions
    data/evaluation/dapt01_eval_cases.jsonl        frozen 47-case benchmark (exclusion only)

Outputs:
    data/training/sft_train_v2.jsonl               training split
    data/evaluation/sft_eval_v2.jsonl              held-out eval split
    data/reports/task67_sft02_build_stats.json     counts, distributions, gate report

Design (Task-66 SFT-02 requirements section 13-14, Task-67 phases 2-7):
  * zero SOURCE_OVERLAP: every row's source must be outside the frozen 18
  * approved Task-63 rows retained subject to the attribution cap
  * new rows are grounded: verbatim spans from rights-cleared corpus units or
    manifest fields, verified by re-runnable checks; absence claims are
    verified mechanically before an abstention row is emitted
  * no synthetic religious facts, no invented doctrine
  * anti-template concentration gate runs before the split is written
  * deterministic source-level split, seed 42
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

HERE = os.path.abspath(os.path.dirname(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
SFT01_DIR = os.path.join(ROOT, "experiments", "sft_01")
if SFT01_DIR not in sys.path:
    sys.path.insert(0, SFT01_DIR)

import anti_template_gate as gate  # noqa: E402
from sft02_common import (  # noqa: E402
    ALLOWED_RIGHTS,
    CATEGORY_TO_TASK_CATEGORY,
    EVAL_FRACTION,
    FROZEN_EVAL_SHA256,
    GOLD_PATH,
    MIN_EVAL_ROWS,
    OUT_EVAL,
    OUT_STATS,
    OUT_TRAIN,
    POOL_PATH,
    REQUIRED_EVAL_COVERAGE,
    SEED,
    SYNTHETIC_SOURCES,
    TRAIN_V1_PATH,
    RightsContext,
    build_row,
    corpus_units_by_source,
    digest_key,
    fold,
    frozen_sha256,
    good_sentence,
    iter_corpus,
    jaccard,
    load_frozen_sources,
    make_messages,
    norm_ws,
    quote_spans,
    read_jsonl,
    script_ok,
    sentence_split,
    shingles,
    text_issues,
    usable_unit_text,
    write_json,
    write_jsonl,
)

HUMAN_IDS = [
    "svk-2022:qa:23bb2ae8",
    "svk-2022:qa:e3a4db5c",
    "svk-2023:qa:c58c0314",
    "svk-2023:qa:f8c0ac79",
    "svk-2024:qa:a9cea037",
]

APPROVED_ATTRIBUTION_CAP = 6    # Task-66 s14: attribution 16-18 = 6 approved + 12 anti-fab
MAX_NEW_ROWS_PER_SOURCE = 5

TARGETS = {
    "PRACTICE_EXPLANATION": 14,
    "STHANAKAVASI_TERMINOLOGY": 4,
    "GENERAL_JAIN_CONCEPT": 2,
    "PRAKRIT": 1,
    "SANSKRIT": 0,  # no eligible unit matches the IAST+Sanskrit-term scan
    "HINDI": 5,
    "GUJARATI": 4,
    "STHANAKAVASI_DISTINCTION": 4,
    "ABSTENTION_PAIRS": 4,
    "ANTI_FABRICATION": 12,  # 6 pairs (s14: "6-8 pairs false claim -> not recorded")
    "CANONICAL_NEW": 5,
}

# ---------------------------------------------------------------------------
# vocabulary
# ---------------------------------------------------------------------------
PRACTICE_PRIORITY = ["Pratikraman", "Samayik", "Avashyaka", "Kayotsarga", "Paryushan"]

PRACTICE_Q = [
    'What does "{title}" say about {practice}?',
    'How does "{title}" describe the practice of {practice}?',
    'In "{title}", how is {practice} explained?',
    'What explanation of {practice} is given in "{title}"?',
    'According to "{title}", what is {practice}?',
    'How is {practice} treated in "{title}"?',
]
PRACTICE_A = [
    'In "{title}", {practice} is described as follows: "{span}"',
    '"{title}" explains {practice} in these words: "{span}"',
    'On {practice}, "{title}" states: "{span}"',
    '{practice}, as presented in "{title}": "{span}"',
    'The text of "{title}" says of {practice}: "{span}"',
    'Here is how "{title}" presents {practice}: "{span}"',
]

TERM_Q = [
    'How does "{title}" explain the term "{term}"?',
    'What does "{title}" say about "{term}"?',
    'In "{title}", what is meant by "{term}"?',
    'How is the term "{term}" used in "{title}"?',
]
TERM_A = [
    '"{title}" writes of "{term}": "{span}"',
    'On "{term}", the text of "{title}" says: "{span}"',
    '"{title}" on "{term}": "{span}"',
    'The term "{term}" appears in "{title}" as follows: "{span}"',
]

HI_Q = [
    '"{title}" में {kw} के बारे में क्या कहा गया है?',
    '"{title}" में {kw} से संबंधित क्या लिखा गया है?',
]
HI_A = [
    '"{title}" के अनुसार: "{span}"',
    '{title} में {kw} के संदर्भ में यह कहा गया है: "{span}"',
    '{kw} के संदर्भ में "{title}" में लिखा गया है: "{span}"',
]
GU_Q = [
    '"{title}" માં {kw} વિશે શું કહેવામાં આવ્યું છે?',
    '"{title}" માં {kw} સંબંધિત શું લખાયેલ છે?',
]
GU_A = [
    '"{title}" મુજબ: "{span}"',
    '{title} માં {kw} ના સંદર્ભમાં આમ કહેવાયું છે: "{span}"',
    '{kw} ના સંદર્ભમાં "{title}" માં આમ લખાયું છે: "{span}"',
]

DIST_Q = [
    'How does "{title}" distinguish the Digambara from the Svetambara tradition?',
    'What difference between Digambara and Svetambara Jains does "{title}" describe?',
    'In "{title}", how are the Digambara and the Svetambara/Sthanakavasi contrasted?',
]
DIST_A = [
    '"{title}" states: "{span}"',
    'The contrast described in "{title}" is: "{span}"',
    'According to "{title}": "{span}"',
]

DISC_Q = [
    'Which sect does the catalog record for "{title}"?',
    'What sect is recorded for "{title}" in the source manifest?',
]
DISC_A = [
    'The catalog does not record a sect for "{title}" (sect: unknown; tradition: "{tradition}"). The source therefore does not establish a specifically Sthanakavasi, Svetambara or Digambara affiliation.',
    'For "{title}" the manifest gives sect: unknown and tradition: "{tradition}". The available catalog evidence is insufficient to classify the work as Sthanakavasi, Svetambara or Digambara.',
]

ABS_Q = {
    "composed": 'In which year was "{title}" composed?',
    "chapters": 'How many chapters does "{title}" contain?',
    "teacher": 'Who was the teacher of the author of "{title}"?',
    "place": 'Where was "{title}" written?',
}
ABS_A = {
    "composed": [
        '"{title}" does not state when it was composed. The catalog records only publication year: {facts}',
        'No composition date for "{title}" appears in this source; the manifest entry gives {facts}',
        'The available material does not establish a composition year for "{title}". What it does record: {facts}',
        'That detail is not recorded for "{title}" in this source: {facts}',
    ],
    "chapters": [
        'The structure of "{title}" is not stated as a chapter count in this source. The catalog records: {facts}',
        'This corpus does not give a number of chapters for "{title}". What is recorded instead: {facts}',
    ],
    "teacher": [
        'The sources do not name a teacher for the author of "{title}". Recorded instead: {facts}',
        'No teacher of the author is established for "{title}" in this material: {facts}',
    ],
    "place": [
        'The place of writing for "{title}" is not recorded in this source. The catalog records: {facts}',
        'This material does not identify where "{title}" was written: {facts}',
    ],
}
ANS_Q = {
    "published": 'In which year was "{title}" published?',
    "author": 'Who wrote "{title}"?',
    "publisher": 'Who published "{title}"?',
    "tradition": 'What tradition does the catalog record for "{title}"?',
    "sections": 'How many parts does the catalog or text of "{title}" list?',
}
ANS_A = {
    "published": [
        'The catalog dates "{title}" to {value}.',
        '"{title}" is recorded as published in {value}.',
    ],
    "author": [
        'The catalog credits {value} as the author of "{title}".',
        '"{title}" is credited to {value}.',
    ],
    "publisher": [
        'The catalog lists {value} as the publisher of "{title}".',
        '"{title}" was issued by {value}, according to the catalog.',
    ],
    "tradition": [
        'The catalog records tradition "{value}" for "{title}".',
        'For "{title}" the manifest records the tradition as {value}.',
    ],
    "sections": [
        'This source lists {value} for "{title}".',
        'According to the material, "{title}" has {value}.',
    ],
}

ANTIFAB_Q = {
    "publisher": 'Who published "{title}"?',
    "translator": 'Who translated "{title}"?',
    "author": 'Who is the author of "{title}"?',
}
ANTIFAB_A = {
    "publisher": [
        'The catalog does not record a publisher for "{title}". Any publisher name would be an invention. It does record: {facts}',
        'No publisher is listed for "{title}" in this source; the recorded facts are: {facts}',
        'A publisher for "{title}" is not identified anywhere in the catalog entry: {facts}',
    ],
    "translator": [
        'No translator is named for "{title}" in the catalog or the text. What is recorded: {facts}',
        'The catalog does not identify a translator of "{title}": {facts}',
    ],
    "author": [
        'The catalog does not record an author for "{title}". It would be wrong to supply a name. The recorded facts are: {facts}',
        'No author name appears for "{title}" in this source: {facts}',
    ],
}

SECT_Q = [
    'Is "{title}" a canonical scripture itself, or a work about one?',
    'How should "{title}" be classified: canonical text, edition, translation, or commentary?',
]
SECT_A_CANONICAL = [
    'The catalog classifies "{title}" as canonical scripture (knowledge layer: {knowledge_layer}); it is a canonical text rather than a work about one.',
    'Classified in the catalog as {knowledge_layer}: "{title}" is a canonical scripture itself, not a commentary on one.',
    'For "{title}" the manifest records knowledge layer {knowledge_layer}, so it is canonical, not a work about the canon.',
]

TERMS_GENERIC = ["ahimsa", "samyak", "kashaya", "moksha", "samsara", "karma", "diksha",
                 "arihant", "siddha", "tirthankara", "shramana", "sravaka", "upadhyaya",
                 "tapas", "dana", "sila", "jnana", "darshana", "charitra", "puja",
                 "ratnatraya", "kaivalya", "jiva", "pudgala", "dravya", "nirjara",
                 "samvara", "mithyatva", "avashyaka", "pratikraman"]
TERMS_STK = ["sthānakavāsī", "sthanakavasi", "sthānakavāsī", "upādhyāy", "upadhyay",
             "gani", "ācārya", "acharya", "śrāvaka", "sravaka", "śrāvikā", "muṇi",
             "muni", "dīkṣā", "diksha", "ganivarshi", "labdhisar"]

HI_KW = ["अहिंसा", "स्थानक", "दीक्षा", "महावीर", "सामायिक", "समयिक", "प्रतिक्रमण",
         "कायोत्सर्ग", "पर्युषण", "श्रावक", "आचार्य", "स्वेताम्बर", "आगम"]
GU_KW = ["અહિંસા", "સ્થાનક", "દીક્ષા", "મહાવીર", "સામાયિક", "સમયિક", "પ્રતિક્રમણ",
         "કાયોત્સર્ગ", "પર્યુષણ", "શ્રાવક", "આચાર્ય", "સ્વેતાંબર",
         "કર્મ", "મોક્ષ", "સંસાર", "આત્મા", "પુણ્ય", "તપ", "દાન",
         "જ્ઞાન", "ચારિત્ર", "ભગવાન", "સિદ્ધ", "તીર્થંકર", "શ્રમણ"]

YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20[0-2]\d)\b")
COMPOSED_RE = re.compile(r"\b(composed|written|dated)\b[^.]{0,60}\b(1[5-9]\d{2}|20[0-2]\d)\b", re.I)
CHAPTER_RE = re.compile(r"\b(\d{1,4})\s+(chapters|sections|parts|angas|adhyayas)\b", re.I)
TEACHER_RE = re.compile(r"\b(pupil of|disciple of|teacher:|taught by|guru:)\b", re.I)
PLACE_RE = re.compile(r"\b(printed|published|written|composed)\s+at\s+[A-Z]", re.I)
TRANSLATOR_RE = re.compile(r"\btranslated (?:by|from)\b|\btranslator\b", re.I)
PLACE_OF_WRITING_RE = re.compile(r"\bcomposed (?:at|in)\b[^.]{0,40}", re.I)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def opener3(answer: str) -> str:
    return gate.norm_opener(answer, 3)


def choose(seq: List, *seeds: str):
    return seq[int(digest_key(*seeds), 16) % len(seq)]


def manifest_facts(m: dict, keys: Tuple[str, ...]) -> str:
    parts = []
    for k in keys:
        v = (m.get(k) or "").strip()
        if v and v.lower() != "unknown":
            parts.append(f"{k}: {v}")
    return "; ".join(parts) if parts else "no further fields recorded"


def eligible_sources(rctx: RightsContext, frozen: set) -> List[str]:
    return sorted(sid for sid in rctx.allowed_sources() if sid not in frozen)


def pick_span(text: str, keyword: str, max_chars: int = 600,
              min_words: int = 6) -> Optional[str]:
    """Return a verbatim span containing keyword (whole sentence or neighbours)."""
    sents = sentence_split(text)
    kw = keyword.lower()
    for i, s in enumerate(sents):
        if kw in s.lower() and good_sentence(s, min_words=min_words):
            if len(s) <= max_chars:
                return s
            # trim to sentence window around keyword, still verbatim contiguous
            return s[:max_chars].rsplit(". ", 1)[0] + "." if ". " in s[:max_chars] else s[:max_chars]
    return None


def load_approved(frozen: set) -> Tuple[List[dict], dict]:
    gold = read_jsonl(GOLD_PATH)
    non_frozen = [r for r in gold if r.get("source_id") not in frozen]
    attr = [r for r in non_frozen if r["task_category"] == "source_citation"]
    canon = [r for r in non_frozen if r["task_category"] == "canonical_commentary_distinction"]
    abst = [r for r in non_frozen if r["task_category"] == "abstention"]

    # deterministic attribution selection: non-"The manifest records" openers
    # first, then digest order; cap per Task-66 s14.
    attr_sorted = sorted(
        attr,
        key=lambda r: (1 if opener3(r["answer"]) == "the manifest records" else 0,
                       digest_key("attr", r["example_id"])),
    )
    attr_kept = attr_sorted[:APPROVED_ATTRIBUTION_CAP]
    # 6 approved + 12 anti-fabrication rows (6 pairs) = 18 = top of s14 16-18.

    train_v1 = read_jsonl(TRAIN_V1_PATH)
    human = [r for r in train_v1
             if r.get("example_id") in set(HUMAN_IDS)
             and r.get("source_id") not in frozen]
    human.sort(key=lambda r: r["example_id"])

    selected = attr_kept + canon + abst + human
    # answer near-dup compression: the Task-63 dictionary-edition rows share
    # near-identical "relation_type edition_of" answers (Jaccard >= 0.80);
    # Task-66 s13 requires breaking such templates, so keep only the first.
    compressed, ndropped = [], []
    sh_a = []
    for r in selected:
        s = shingles(r["answer"])
        if any(jaccard(s, x) >= 0.80 for x in sh_a):
            ndropped.append(r["example_id"])
            continue
        sh_a.append(s)
        compressed.append(r)
    selected = compressed
    audit = {
        "gold_total": len(gold),
        "gold_frozen_excluded": len(gold) - len(non_frozen),
        "attr_total_non_frozen": len(attr),
        "attr_kept": len(attr_kept),
        "attr_dropped_by_cap": len(attr) - len(attr_kept),
        "canon_kept": len(canon),
        "abst_kept": len(abst),
        "human_kept": len(human),
        "approved_near_dup_dropped": ndropped,
        "selected_total": len(selected),
    }
    return selected, audit


def approved_origin(row: dict) -> str:
    return str(row.get("origin") or "task64")


def origin_builder(row: dict) -> str:
    o = row.get("origin")
    if isinstance(o, dict):
        return str(o.get("builder") or "")
    return str(o or "")


_QREG: List[str] = []


def q_ok(q: str, thr: float = 0.75) -> bool:
    """Question must not near-duplicate any previously built question."""
    if not _QREG:
        return True
    sh = shingles(q)
    return all(jaccard(sh, shingles(x)) < thr for x in _QREG)


def qreg_add(rows) -> None:
    _QREG.extend(r["question"] for r in rows)


def finalize_approved(row: dict) -> dict:
    out = dict(row)
    out["split"] = "train"
    out.setdefault("tags", [])
    out["sft02"] = {"selected_by": "task67", "source_row": "approved_v1_pool"}
    out["messages"] = make_messages(out["question"], out["answer"])
    return out


# ---------------------------------------------------------------------------
# new-row builders
# ---------------------------------------------------------------------------
def build_practice_rows(rctx, frozen, pool_by_source, corpus_index, per_source_count, used_ids):
    rows = []
    pool = [r for r in pool_by_source if r.get("practice")]
    # spread across practices: priority practices first, then rest, digest order
    def prio(r):
        p = r["practice"]
        pi = PRACTICE_PRIORITY.index(p) if p in PRACTICE_PRIORITY else 99
        return (pi, digest_key("practice", r["unit_id"] or r["example_id"]))
    pool.sort(key=prio)
    seen_practice: Counter = Counter()
    seen_source: Counter = Counter()
    practice_cycle = []
    # round-robin over practices for coverage
    by_p: Dict[str, List[dict]] = defaultdict(list)
    for r in pool:
        by_p[r["practice"]].append(r)
    order = PRACTICE_PRIORITY + sorted(p for p in by_p if p not in PRACTICE_PRIORITY)
    idx = {p: 0 for p in order}
    while len(rows) < TARGETS["PRACTICE_EXPLANATION"]:
        added = False
        for p in order:
            if len(rows) >= TARGETS["PRACTICE_EXPLANATION"]:
                break
            lst = by_p.get(p) or []
            while idx[p] < len(lst):
                cand = lst[idx[p]]
                idx[p] += 1
                sid = cand["source_id"]
                if sid in frozen or not rctx.allowed(sid):
                    continue
                if seen_source[sid] >= MAX_NEW_ROWS_PER_SOURCE:
                    continue
                if seen_practice[p] >= 3:
                    continue
                text = usable_unit_text(cand)
                span = pick_span(text, p, min_words=12)
                if not span or fold(p) not in fold(span):
                    continue
                if re.search(r"_{4,}", span) or span.rstrip().endswith("?"):
                    continue
                lead = fold(span.split()[0]) if span.split() else ""
                if lead in {"what", "how", "why", "when", "where", "does", "do",
                            "did", "is", "are", "can", "could", "which", "who"}:
                    continue
                # resolve the authoritative corpus record by span containment
                rec = next((r for r in corpus_index.get(sid, [])
                            if fold(span) in fold(usable_unit_text(r))), None)
                if rec is None:
                    continue
                uid = rec.get("id") or rec.get("unit_id")
                title = rctx.manifest_row(sid).get("title") or sid
                q = choose(PRACTICE_Q, "q", uid, p).format(title=title, practice=p)
                if not q_ok(q):
                    continue
                a = choose(PRACTICE_A, "a", uid, p).format(title=title, practice=p, span=span)
                row = build_row(
                    source_id=sid,
                    category="PRACTICE_EXPLANATION",
                    question=q,
                    answer=a,
                    language="en",
                    origin="task67_sft02:practice_pool",
                    evidence={"method": "span_in_unit_text", "unit_id": uid,
                              "span": span, "keyword": p},
                    rctx=rctx,
                    unit_type="practice",
                    tags=["practice", p.lower()],
                    extra={"practice": p},
                )
                rows.append(row)
                seen_practice[p] += 1
                seen_source[sid] += 1
                added = True
                break
        if not added:
            break
    return rows


def build_terminology_rows(rctx, frozen, corpus_index, per_source_count, used_ids):
    rows = []
    targets = [("STHANAKAVASI_TERMINOLOGY", TARGETS["STHANAKAVASI_TERMINOLOGY"]),
               ("GENERAL_JAIN_CONCEPT", TARGETS["GENERAL_JAIN_CONCEPT"]),
               ("PRAKRIT", TARGETS["PRAKRIT"]),
               ("SANSKRIT", TARGETS["SANSKRIT"])]
    seen_src: Counter = Counter()   # (cat, sid) -> rows
    term_seen: Counter = Counter()  # (cat, term) -> frame salt counter
    seen_tt: set = set()            # (cat, title, term) -> one row max
    iast = re.compile(r"[\u0101\u012b\u016b\u1e5b\u1e5d\u015b\u1e63\u1e47\u1e6d\u1e0d\u1e43\u1e41]")
    for cat, want in targets:
        got = 0
        for sid in sorted(corpus_index, key=lambda s: digest_key("term", s)):
            if got >= want:
                break
            if (sid in frozen or rctx.synthetic(sid)
                    or not rctx.allowed(sid) or seen_src[(cat, sid)] >= 2):
                continue
            mrow = rctx.manifest_row(sid)
            sect = (mrow.get("sect") or "").lower()
            recs = corpus_index[sid]
            for rec in sorted(recs, key=lambda r: digest_key("term2", str(r.get("id")))):
                if got >= want:
                    break
                uid = rec.get("id") or rec.get("unit_id")
                if uid in used_ids:
                    continue
                text = usable_unit_text(rec)
                if not text or len(text) > 4000:
                    continue
                lang = rec.get("language") or ""
                if cat == "STHANAKAVASI_TERMINOLOGY" and "sthana" not in sect:
                    continue
                if cat == "PRAKRIT" and lang != "pra":
                    continue
                if cat == "SANSKRIT":
                    if lang in ("gu", "hi") or not iast.search(text or ""):
                        continue
                if cat == "GENERAL_JAIN_CONCEPT" and lang not in ("en", "unknown"):
                    continue
                term_list = TERMS_STK if cat == "STHANAKAVASI_TERMINOLOGY" else TERMS_GENERIC
                span = None
                term_hit = None
                for s in sentence_split(text):
                    if not good_sentence(s, min_words=8):
                        continue
                    low = s.lower()
                    for t in term_list:
                        if re.search(r"\b" + re.escape(t) + r"\b", low):
                            span, term_hit = s, t
                            break
                    if span:
                        break
                if not span:
                    continue
                title = mrow.get("title") or sid
                tt = (cat, title, term_hit)
                if tt in seen_tt:
                    continue
                n_rep = term_seen[(cat, term_hit)]
                base_a = int(digest_key("ta", uid), 16) % len(TERM_A)
                base_q = int(digest_key("tq", uid, term_hit), 16) % len(TERM_Q)
                q, qidx = None, None
                for off in range(len(TERM_Q)):
                    idx = (base_q + off) % len(TERM_Q)
                    cand_q = TERM_Q[idx].format(title=title, term=term_hit)
                    if q_ok(cand_q):
                        q = cand_q
                        break
                if q is None:
                    continue
                a = TERM_A[(base_a + n_rep) % len(TERM_A)].format(
                    title=title, term=term_hit, span=span)
                row = build_row(
                    source_id=sid,
                    category=cat,
                    question=q,
                    answer=a,
                    language="en",
                    origin="task67_sft02:terminology",
                    evidence={"method": "span_in_unit_text", "unit_id": uid,
                              "span": span, "keyword": term_hit},
                    rctx=rctx,
                    unit_type="term",
                    tags=["terminology", term_hit],
                )
                rows.append(row)
                used_ids.add(uid)
                seen_src[(cat, sid)] += 1
                term_seen[(cat, term_hit)] += 1
                seen_tt.add(tt)
                got += 1
    return rows


def build_multilingual_rows(rctx, frozen, corpus_index, lang, category, qlist, alist, kws, want):
    rows = []
    seen_src: Counter = Counter()
    cands = []
    for sid in sorted(corpus_index, key=lambda s: digest_key("ml", lang, s)):
        if sid in frozen or rctx.synthetic(sid) or not rctx.allowed(sid):
            continue
        for rec in corpus_index[sid]:
            if (rec.get("language") or "") != lang:
                continue
            text = usable_unit_text(rec)
            lo = 60 if lang == "gu" else 300
            hi = 6000 if lang == "gu" else 3000
            if not text or not (lo <= len(text) <= hi):
                continue
            if not script_ok(text, lang):
                continue
            for kw in kws:
                mw = 5 if lang == "gu" else 8
                span = pick_span(text, kw, max_chars=500, min_words=mw)
                if span:
                    cands.append((sid, rec, kw, span))
                    break
    # spread: max 2 per source, one row per (source, keyword)
    seen_kw: set = set()
    for sid, rec, kw, span in cands:
        if len(rows) >= want:
            break
        if seen_src[sid] >= 2 or (sid, kw) in seen_kw:
            continue
        seen_kw.add((sid, kw))
        uid = rec.get("id") or rec.get("unit_id")
        title = rctx.manifest_row(sid).get("title") or sid
        # frame rotation until the answer clears the min-words gate
        base = int(digest_key("mframe", uid, kw), 16) % len(alist)
        q = choose(qlist, "mq", uid, kw).format(title=title, kw=kw)
        if not q_ok(q):
            continue
        a = None
        for off in range(len(alist)):
            cand_a = alist[(base + off) % len(alist)].format(
                title=title, kw=kw, span=span)
            if len(cand_a.split()) >= 14:
                a = cand_a
                break
        if a is None:
            continue
        row = build_row(
            source_id=sid,
            category=category,
            question=q,
            answer=a,
            language=lang,
            origin=f"task67_sft02:{lang}_corpus",
            evidence={"method": "span_in_unit_text", "unit_id": uid,
                      "span": span, "keyword": kw},
            rctx=rctx,
            unit_type="qa",
            tags=["multilingual", lang],
        )
        rows.append(row)
        seen_src[sid] += 1
    return rows


def build_distinction_rows(rctx, frozen, corpus_index):
    """Digambara / Svetambara / Sthanakavasi contrast rows.

    Organic contrast text is scarce: only 5 eligible units mention both
    sides anywhere. We therefore search a +/-2-sentence window (any
    language) rather than a single sentence, and take at most 2 rows per
    source. SVK-0037 (hi) windows are kept as fallback material.
    """
    cdig = re.compile(r"digambar|दिगंबर|दिगम्बर|દિગંબર", re.I)
    csvt = re.compile(r"svetambar|shvetambar|sth[āa]nak|स्वेताम्बर|श्वेताम्बर|स्थानक", re.I)
    cands = []
    per_src_cand: Counter = Counter()
    for sid in sorted(corpus_index, key=lambda s: digest_key("dist", s)):
        if sid in frozen or rctx.synthetic(sid) or not rctx.allowed(sid):
            continue
        for rec in corpus_index[sid]:
            if per_src_cand[sid] >= 2:
                break
            text = usable_unit_text(rec) or ""
            if not (200 <= len(text) <= 6000):
                continue
            sents = sentence_split(text)
            idx_d = [i for i, s in enumerate(sents) if cdig.search(s)]
            idx_c = [i for i, s in enumerate(sents) if csvt.search(s)]
            if not idx_d or not idx_c:
                continue
            best = min(((abs(i - j), i, j) for i in idx_d for j in idx_c),
                       key=lambda x: (x[0], x[1]))
            gap, i, j = best
            if gap > 6:
                continue
            lo_i, hi_i = min(i, j), max(i, j)
            window = " ".join(sents[max(0, lo_i - 1): hi_i + 2])
            if len(window) > 700:
                window = " ".join(sents[lo_i: hi_i + 1])
            if not (60 <= len(window) <= 700):
                continue
            if not good_sentence(window, min_words=5):
                continue
            cands.append((sid, rec.get("id") or rec.get("unit_id"),
                          window, rec.get("language") or "en", True))
            per_src_cand[sid] += 1
    # prefer windows carrying BOTH digambara and svetambar/sthana terms
    cands.sort(key=lambda c: (0 if (cdig.search(c[2]) and csvt.search(c[2])) else 1,
                              digest_key("dist2", c[1])))
    rows = []
    seen_src: Counter = Counter()
    for sid, uid, window, lang, _ in cands:
        if len(rows) >= 4:
            break
        if seen_src[sid] >= 2:
            continue
        title = rctx.manifest_row(sid).get("title") or sid
        base_q = int(digest_key("dq", uid), 16) % len(DIST_Q)
        q = None
        for off in range(len(DIST_Q)):
            cand_q = DIST_Q[(base_q + off) % len(DIST_Q)].format(title=title)
            if q_ok(cand_q):
                q = cand_q
                break
        if q is None:
            continue
        a = choose(DIST_A, "da", uid).format(title=title, span=window)
        if len(a.split()) < 12 or len(a) > 750:
            continue
        rows.append(build_row(
            source_id=sid,
            category="STHANAKAVASI_DISTINCTION",
            question=q,
            answer=a,
            language=lang if lang in ("en", "hi", "gu", "pra") else "en",
            origin="task67_sft02:contrast_text",
            evidence={"method": "span_in_unit_text", "unit_id": uid,
                      "span": window, "keyword": "digambara"},
            rctx=rctx,
            unit_type="distinction",
            tags=["sect_contrast"],
        ))
        seen_src[sid] += 1
    return rows


def build_sect_discipline_rows(rctx, frozen, eligible):
    rows = []
    unknown_sect = [s for s in eligible
                    if (rctx.manifest_row(s).get("sect") or "").upper() == "UNKNOWN"
                    and (rctx.manifest_row(s).get("tradition") or "").strip()]
    unknown_sect.sort(key=lambda s: digest_key("disc", s))
    for i, sid in enumerate(unknown_sect[:TARGETS["STHANAKAVASI_DISTINCTION"]]):
        if len(rows) >= 4:
            break
        mrow = rctx.manifest_row(sid)
        title = mrow.get("title") or sid
        tradition = mrow.get("tradition") or ""
        q = DISC_Q[i % len(DISC_Q)].format(title=title)
        if not q_ok(q):
            continue
        a = (DISC_A[i % len(DISC_A)]).format(title=title, tradition=tradition)
        rows.append(build_row(
            source_id=sid,
            category="STHANAKAVASI_DISTINCTION",
            question=q,
            answer=a,
            language="en",
            origin="task67_sft02:sect_discipline",
            evidence={"method": "manifest_fields",
                      "fields": {"sect": mrow.get("sect") or "",
                                 "tradition": tradition}},
            rctx=rctx,
            unit_type="distinction",
            tags=["sect_unknown_discipline"],
        ))
    return rows


def fact_state(rctx, sid: str, unit_texts: List[str]) -> dict:
    """Presence/absence of facts, verified against manifest + ALL source units."""
    m = rctx.manifest_row(sid)
    joined = " ".join(unit_texts)
    author = (m.get("author") or "").strip()
    year = (m.get("publication_year") or "").strip()
    publisher = (m.get("publisher") or "").strip()
    tradition = (m.get("tradition") or "").strip()
    return {
        "author": bool(author and author.lower() != "unknown"),
        "year": bool(year and year.lower() != "unknown" and YEAR_RE.search(year)),
        "publisher": bool(publisher and publisher.lower() != "unknown"),
        "tradition": bool(tradition and tradition.lower() != "unknown"),
        "composed": bool(COMPOSED_RE.search(joined)),
        "chapters": bool(CHAPTER_RE.search(joined)),
        "teacher": bool(TEACHER_RE.search(joined)),
        "place_written": bool(PLACE_OF_WRITING_RE.search(joined)),
        "translator_named": bool(TRANSLATOR_RE.search(joined)),
        "_manifest": m,
        "_chapters": (lambda ch: (ch.group(1) + " " + ch.group(2)) if ch else None)(CHAPTER_RE.search(joined)),
    }


def build_calibration_pairs(rctx, frozen, corpus_index, per_source_count):
    """Abstention rows as answerable/unanswerable contrast pairs (Phase 3F)."""
    unans_rows: List[dict] = []
    ans_rows: List[dict] = []
    pair_meta = []
    src_states: Dict[str, dict] = {}
    for sid in sorted(corpus_index, key=lambda s: digest_key("cal", s)):
        if sid in frozen or not rctx.allowed(sid) or per_source_count[sid] >= MAX_NEW_ROWS_PER_SOURCE:
            continue
        texts = [t for t in (usable_unit_text(r) for r in corpus_index[sid]) if t]
        if not texts:
            continue
        src_states[sid] = fact_state(rctx, sid, texts)
    facts_list = list(src_states.items())

    def facts_phrase(st, exclude: Optional[str] = None) -> str:
        m = st["_manifest"]
        parts = []
        for k, label in (("author", "author"), ("year", "publication year"),
                         ("publisher", "publisher"), ("tradition", "tradition")):
            if k == exclude:
                continue
            if st.get(k):
                v = m.get({"author": "author", "year": "publication_year",
                           "publisher": "publisher", "tradition": "tradition"}[k])
                parts.append(f"{label}: {v}")
        return "; ".join(parts) if parts else "no further fields recorded"

    pairs_spec = [
        ("composed", "published"),
        ("chapters", "sections"),
        ("teacher", "author"),
        ("place", "publisher"),
        ("composed", "author"),
        ("place", "published"),
    ]
    ans_key_of = {"published": "year", "author": "author", "publisher": "publisher",
                  "sections": "chapters", "tradition": "tradition"}
    unans_key_of = {"composed": "composed", "chapters": "chapters",
                    "teacher": "teacher", "place": "place_written"}
    used_sources = set()
    used_qs: List[str] = []
    used_titles: List[str] = []
    pairs_built = 0

    def _fits(text: str, pool: List[str], thr: float) -> bool:
        sh = shingles(text)
        return all(jaccard(sh, shingles(o)) < thr for o in pool)

    for i, (unans_stem, ans_stem) in enumerate(pairs_spec):
        if pairs_built >= TARGETS["ABSTENTION_PAIRS"]:
            break
        ans_key = ans_key_of[ans_stem]
        unans_key = unans_key_of[unans_stem]
        ans_cands = [(s, st) for s, st in facts_list
                     if s not in used_sources and st.get(ans_key)]
        unans_cands = [(s, st) for s, st in facts_list
                       if s not in used_sources and not st.get(unans_key)]
        pair_id = f"abstain-pair-{pairs_built + 1:02d}"
        built = False
        for sid_a, st_a in ans_cands[:14]:
            if built:
                break
            m_a = st_a["_manifest"]
            title_a = m_a.get("title") or sid_a
            if ans_stem == "published":
                value = m_a.get("publication_year")
            elif ans_stem == "author":
                value = m_a.get("author")
            elif ans_stem == "publisher":
                value = m_a.get("publisher")
            elif ans_stem == "tradition":
                value = m_a.get("tradition")
            else:
                value = st_a.get("_chapters")
            if not value:
                continue
            q_a = ANS_Q[ans_stem].format(title=title_a)
            if (not _fits(q_a, used_qs, 0.75) or not q_ok(q_a)
                    or not _fits(title_a, used_titles, 0.6)):
                continue
            for sid_u, st_u in unans_cands[:14]:
                if sid_u == sid_a or built:
                    continue
                m_u = st_u["_manifest"]
                title_u = m_u.get("title") or sid_u
                q_u = ABS_Q[unans_stem].format(title=title_u)
                if (not _fits(q_u, used_qs, 0.75) or not q_ok(q_u)
                        or not _fits(title_u, used_titles, 0.6)):
                    continue

                # answerable member
                a = (choose(ANS_A[ans_stem], "aa", sid_a, ans_stem).format(title=title_a, value=value)
                     + " The catalog entry also records: " + facts_phrase(st_a, exclude=ans_key))
                if ans_key == "chapters":
                    ans_evidence = {"method": "unit_presence",
                                    "pattern_key": "chapter_count_in_text"}
                else:
                    mfield = {"year": "publication_year"}.get(ans_key, ans_key)
                    ans_evidence = {"method": "manifest_fields",
                                    "fields": {mfield: value}}
                ans_rows.append(build_row(
                    source_id=sid_a,
                    category="ABSTENTION/INSUFFICIENT_EVIDENCE",
                    question=q_a, answer=a, language="en",
                    origin="task67_sft02:calibration_answerable",
                    evidence=ans_evidence,
                    rctx=rctx, unit_type="calibration",
                    tags=["abstention_contrast", "answerable", pair_id],
                    extra={"contrast_pair_id": pair_id, "pair_group": pair_id},
                ))

                # unanswerable member
                facts = facts_phrase(st_u)
                a_u = choose(ABS_A[unans_stem], "ua", sid_u, unans_stem).format(
                    title=title_u, facts=facts)
                absent = []
                if unans_stem == "composed" and not st_u["composed"]:
                    absent.append("composed_date_in_text")
                if unans_stem == "chapters" and not st_u["chapters"]:
                    absent.append("chapter_count_in_text")
                if unans_stem == "teacher" and not st_u["teacher"]:
                    absent.append("teacher_cue_in_text")
                if unans_stem == "place" and not st_u["place_written"]:
                    absent.append("place_of_writing_in_text")
                unans_rows.append(build_row(
                    source_id=sid_u,
                    category="ABSTENTION/INSUFFICIENT_EVIDENCE",
                    question=q_u, answer=a_u, language="en",
                    origin="task67_sft02:calibration_unanswerable",
                    evidence={"method": "unit_absence", "unit_ids": [],
                              "absent_patterns": absent,
                              "present_fields": {k: (m_u.get(k) or "") for k in
                                                 ("author", "publication_year", "tradition")
                                                 if (m_u.get(k) or "").strip()}},
                    rctx=rctx, unit_type="calibration",
                    tags=["abstention_contrast", "unanswerable", pair_id],
                    extra={"contrast_pair_id": pair_id, "pair_group": pair_id},
                ))
                used_sources.add(sid_a)
                used_sources.add(sid_u)
                used_qs += [q_a, q_u]
                used_titles += [title_a, title_u]
                pair_meta.append({"pair_id": pair_id, "unanswerable_source": sid_u,
                                  "answerable_source": sid_a,
                                  "stems": [unans_stem, ans_stem]})
                pairs_built += 1
                built = True
    return unans_rows + ans_rows, pair_meta


def build_antifabrication_rows(rctx, frozen, corpus_index, per_source_count):
    """Anti-fabrication pairs: a false-attribution presupposition row plus a
    plain question about the same missing attribute, both answered with the
    mechanically-verified "not recorded" correction (Task-66 s14: 6-8 pairs
    false claim -> 'not recorded in source').

    The presupposition uses a REAL author/publisher value belonging to a
    DIFFERENT eligible source, so no new names are invented and the answer
    explicitly retracts the claim.
    """
    slots = ["publisher", "translator", "author"]
    slot_key = {"publisher": "publisher", "translator": "translator_named",
                "author": "author"}
    attempts = []
    for sid in sorted(corpus_index, key=lambda s: digest_key("fab", s)):
        if sid in frozen or rctx.synthetic(sid) or not rctx.allowed(sid):
            continue
        texts = [t for t in (usable_unit_text(r) for r in corpus_index[sid]) if t]
        if not texts:
            continue
        st = fact_state(rctx, sid, texts)
        missing = [s for s in slots if not st.get(slot_key[s])]
        if missing:
            attempts.append((sid, st, missing))

    # pool of real attribution values from other eligible sources
    other_authors, other_pubs = [], []
    for sid in sorted(corpus_index, key=lambda s: digest_key("fabv", s)):
        m = rctx.manifest_row(sid)
        a = (m.get("author") or "").strip()
        if a and a.lower() != "unknown":
            other_authors.append(a)
        p_ = (m.get("publisher") or "").strip()
        if p_ and p_.lower() != "unknown":
            other_pubs.append(p_)

    rows = []
    seen_src: Counter = Counter()
    seen_slot: Counter = Counter()
    pairs_built = 0
    plain_q = {"publisher": ANTIFAB_Q["publisher"],
               "translator": ANTIFAB_Q["translator"],
               "author": ANTIFAB_Q["author"]}
    claim_q = {
        "publisher": 'Is "{title}" a work published by {claim}? What does the catalog record?',
        "translator": 'Is "{title}" a translation by {claim}? What does the catalog record?',
        "author": 'Is "{title}" written by {claim}? What does the catalog record?',
    }
    claim_a = {
        "publisher": ['No. The catalog does not record a publisher for "{title}"; naming {claim} would be a fabrication. What is recorded: {facts}', ],
        "translator": ['No. No translator is named for "{title}" in the catalog or the text; {claim} is not associated with this work in any recorded field. Recorded: {facts}', ],
        "author": ['No. The catalog records no author for "{title}". Attributing it to {claim} would be an invention. The recorded facts are: {facts}', ],
    }
    plain_a = ANTIFAB_A

    def facts_of(st):
        m = st["_manifest"]
        out = []
        for k, label in (("author", "author"), ("year", "publication year"),
                         ("tradition", "tradition"), ("publisher", "publisher")):
            if st.get(k):
                v = m.get({"author": "author", "year": "publication_year",
                           "publisher": "publisher", "tradition": "tradition"}[k])
                out.append(f"{label}: {v}")
        return "; ".join(out) if out else "no further fields recorded"

    for sid, st, missing in attempts:
        if pairs_built >= TARGETS["ANTI_FABRICATION"] // 2:
            break
        if seen_src[sid] >= 1:
            continue
        m = st["_manifest"]
        title = m.get("title") or sid
        slot = missing[0]
        if seen_slot[slot] >= 3:
            alt = [s for s in missing if seen_slot[s] < 3]
            if not alt:
                continue
            slot = alt[0]
        pool = other_pubs if slot == "publisher" else other_authors
        pool = [v for v in pool if v]
        if not pool:
            continue
        claim = pool[int(digest_key("claim", sid, slot), 16) % len(pool)]
        facts_str = facts_of(st)
        pair_id = f"antifab-pair-{pairs_built + 1:02d}"

        q_c = claim_q[slot].format(title=title, claim=claim)
        if not q_ok(q_c):
            continue
        a_c = claim_a[slot][0].format(title=title, claim=claim, facts=facts_str)
        rows.append(build_row(
            source_id=sid, category="SOURCE_ATTRIBUTION",
            question=q_c, answer=a_c, language="en",
            origin="task67_sft02:anti_fabrication",
            evidence={"method": "manifest_absence",
                      "absent_fields": {slot: "absent"},
                      "present_fields": {k: (m.get(k) or "") for k in
                                         ("author", "publication_year", "tradition")
                                         if st.get({"author": "author",
                                                    "publication_year": "year",
                                                    "tradition": "tradition"}.get(k, k))}},
            rctx=rctx, unit_type="attribution",
            tags=["anti_fabrication", "unknown_attribution", slot,
                  "false_presupposition"],
            extra={"attribution_slot_missing": slot, "pair_group": pair_id,
                   "false_claim_value": claim},
        ))

        q_p = plain_q[slot].format(title=title)
        if not q_ok(q_p):
            continue
        a_p = choose(plain_a[slot], "fa", sid, slot).format(title=title, facts=facts_str)
        rows.append(build_row(
            source_id=sid, category="SOURCE_ATTRIBUTION",
            question=q_p, answer=a_p, language="en",
            origin="task67_sft02:anti_fabrication",
            evidence={"method": "manifest_absence",
                      "absent_fields": {slot: "absent"},
                      "present_fields": {k: (m.get(k) or "") for k in
                                         ("author", "publication_year", "tradition")
                                         if st.get({"author": "author",
                                                    "publication_year": "year",
                                                    "tradition": "tradition"}.get(k, k))}},
            rctx=rctx, unit_type="attribution",
            tags=["anti_fabrication", "unknown_attribution", slot],
            extra={"attribution_slot_missing": slot, "pair_group": pair_id},
        ))
        seen_slot[slot] += 1
        seen_src[sid] += 1
        pairs_built += 1
    return rows


def build_canonical_new_rows(rctx, frozen, corpus_index, approved_canon):
    """Canonical-positive contrast members for the approved edition/translation rows."""
    rows = []
    # find canonical-knowledge-layer sources
    canon_srcs = [s for s in sorted(set(s for _, s in approved_canon),
                                    key=lambda x: digest_key("cn", x))
                  if rctx.knowledge_layer(s) == "CANONICAL_SCRIPTURE" and s not in frozen
                  and rctx.allowed(s)]
    if not canon_srcs:
        canon_srcs = [s for s in sorted(corpus_index, key=lambda x: digest_key("cn", x))
                      if rctx.allowed(s) and s not in frozen
                      and rctx.knowledge_layer(s) == "CANONICAL_SCRIPTURE"]
    got = 0
    used = set()
    for sid in canon_srcs:
        if got >= TARGETS["CANONICAL_NEW"]:
            break
        if sid in used:
            continue
        m = rctx.manifest_row(sid)
        title = m.get("title") or sid
        kl = rctx.knowledge_layer(sid)
        # pick a representative unit as evidence anchor
        uid = None
        for rec in sorted(corpus_index.get(sid, []), key=lambda r: digest_key("cu", str(r.get("id")))):
            t = usable_unit_text(rec)
            if t and len(t) >= 100:
                uid = rec.get("id") or rec.get("unit_id")
                break
        if uid is None:
            continue
        q = SECT_Q[got % len(SECT_Q)].format(title=title)
        if not q_ok(q):
            continue
        a = choose(SECT_A_CANONICAL, "ca", sid, q).format(title=title, knowledge_layer=kl)
        rows.append(build_row(
            source_id=sid,
            category="CANONICAL_VS_COMMENTARY",
            question=q, answer=a, language="en",
            origin="task67_sft02:canonical_positive",
            evidence={"method": "manifest_fields", "fields": {"knowledge_layer":
                      (rctx.manifest_row(sid).get("knowledge_layer") or "")}},
            rctx=rctx, unit_type="canonical",
            tags=["canonical_contrast", "canonical_positive"],
            knowledge_layer=kl,
            canonical_status="CANONICAL",
            extra={"contrast_pair_role": "canonical_positive"},
        ))
        used.add(sid)
        got += 1
    return rows


# ---------------------------------------------------------------------------
# gates
# ---------------------------------------------------------------------------
def row_gates(rows, rctx, frozen_sources, frozen_questions, decisions=None):
    problems = []
    for row in rows:
        sid = row.get("source_id")
        if sid in frozen_sources:
            problems.append(f"{row['example_id']}: frozen source {sid}")
        if sid not in rctx.allowed_sources():
            problems.append(f"{row['example_id']}: rights not allowed ({rctx.status(sid)})")
        if (row.get("rights_status") or "") not in ALLOWED_RIGHTS:
            problems.append(f"{row['example_id']}: rights_status {row.get('rights_status')}")
        for issue in text_issues(row["answer"]):
            problems.append(f"{row['example_id']}: answer {issue}")
        for issue in text_issues(row["question"]):
            if issue != "too_short":
                problems.append(f"{row['example_id']}: question {issue}")
        if len(row["answer"]) > 750:
            problems.append(f"{row['example_id']}: answer too long ({len(row['answer'])})")
        if len(row["question"]) > 320:
            problems.append(f"{row['example_id']}: question too long ({len(row['question'])})")
        if not re.match(r"^[a-z0-9_-]+:[a-z0-9_-]+:[a-f0-9]{8}$", row["example_id"]):
            problems.append(f"{row['example_id']}: bad example_id pattern")
        # frozen question similarity
        fq = shingles(row["question"])
        for f in frozen_questions:
            if jaccard(fq, f) >= 0.80:
                problems.append(f"{row['example_id']}: question near-dup of frozen benchmark")
                break
        # repeated sentence inside one answer
        sents = [fold(s) for s in sentence_split(row["answer"]) if len(s.split()) >= 5]
        if len(sents) != len(set(sents)):
            problems.append(f"{row['example_id']}: repeated sentence inside answer")
    return problems


def verify_grounding(rows, rctx, units_by_id, corpus_index):
    """Re-runnable grounding checks for every row (method recorded in evidence)."""
    problems = []
    for row in rows:
        ev = row.get("evidence") or {}
        # approved rows carry task64-style evidence; they are verified by the
        # Task-64 grounding machinery in the Task-67 validator, not here.
        if not origin_builder(row).startswith("task67"):
            continue
        method = ev.get("method")
        if method == "span_in_unit_text":
            uid = ev.get("unit_id")
            rec = units_by_id.get(uid)
            if not rec:
                # fall back: find via source index
                rec = next((r for r in corpus_index.get(row["source_id"], [])
                            if (r.get("id") or r.get("unit_id")) == uid), None)
            if not rec:
                problems.append(f"{row['example_id']}: unit {uid} not found")
                continue
            text = usable_unit_text(rec)
            if fold(ev.get("span") or "") not in fold(text):
                problems.append(f"{row['example_id']}: span not in unit text")
        elif method == "manifest_fields":
            m = rctx.manifest_row(row["source_id"])
            for k, v in (ev.get("fields") or {}).items():
                mv = str(m.get(k) or "")
                if v and fold(mv) != fold(str(v)):
                    problems.append(f"{row['example_id']}: manifest field {k} mismatch")
        elif method == "manifest_absence":
            m = rctx.manifest_row(row["source_id"])
            for k in (ev.get("absent_fields") or {}):
                if k == "translator":
                    texts = " ".join(usable_unit_text(r)
                                     for r in corpus_index.get(row["source_id"], []))
                    if TRANSLATOR_RE.search(texts):
                        problems.append(f"{row['example_id']}: translator cue present in text")
                    continue
                if k == "publisher" and (m.get("publisher") or "").strip().lower() not in ("", "unknown"):
                    problems.append(f"{row['example_id']}: publisher present but claimed absent")
                if k == "author" and (m.get("author") or "").strip().lower() not in ("", "unknown"):
                    problems.append(f"{row['example_id']}: author present but claimed absent")
        elif method == "unit_presence":
            if (ev.get("pattern_key") == "chapter_count_in_text"):
                texts = " ".join(usable_unit_text(r)
                                 for r in corpus_index.get(row["source_id"], []))
                if not CHAPTER_RE.search(texts):
                    problems.append(f"{row['example_id']}: chapter count claimed present but absent")
        elif method == "unit_absence":
            # absence patterns must not appear in the row's own source units
            texts = " ".join(usable_unit_text(r) for r in corpus_index.get(row["source_id"], []))
            for pat in (ev.get("absent_patterns") or []):
                regex = {"composed_date_in_text": COMPOSED_RE,
                         "chapter_count_in_text": CHAPTER_RE,
                         "teacher_cue_in_text": TEACHER_RE,
                         "place_of_writing_in_text": PLACE_OF_WRITING_RE}.get(pat)
                if regex and regex.search(texts):
                    problems.append(f"{row['example_id']}: pattern {pat} actually present")
        else:
            problems.append(f"{row['example_id']}: unknown grounding method {method!r}")
    return problems


def dedup(rows):
    """Exact + near-duplicate removal on questions AND answers.

    Rows carrying a `pair_group` are atomic: dropping one member drops the
    whole contrast pair (an abstention pair with one side missing would break
    the calibration design). Approved rows come first in the list, so they
    win ties against newer rows.
    """
    kept, dropped = [], []
    seen_q, seen_a = {}, {}
    sh_q: Dict[str, set] = {}
    sh_a: Dict[str, set] = {}
    broken_groups: set = set()

    def drop(row, reason):
        dropped.append((row["example_id"], reason))
        g = row.get("pair_group")
        if g:
            broken_groups.add(g)

    for row in rows:
        qk, ak = fold(row["question"]), fold(row["answer"])
        if qk in seen_q:
            drop(row, "exact_duplicate_question")
            continue
        if ak in seen_a:
            drop(row, "exact_duplicate_answer")
            continue
        sq, sa = shingles(row["question"]), shingles(row["answer"])
        if any(jaccard(sq, s) >= 0.80 for s in sh_q.values()):
            drop(row, "near_duplicate_question")
            continue
        if any(jaccard(sa, s) >= 0.80 for s in sh_a.values()):
            drop(row, "near_duplicate_answer")
            continue
        kept.append(row)
        seen_q[qk] = row["example_id"]
        seen_a[ak] = row["example_id"]
        sh_q[row["example_id"]] = sq
        sh_a[row["example_id"]] = sa

    if broken_groups:
        kept2 = []
        for r in kept:
            if r.get("pair_group") in broken_groups:
                dropped.append((r["example_id"], "pair_member_dropped"))
            else:
                kept2.append(r)
        kept = kept2
    return kept, dropped


def assign_split(rows) -> Tuple[List[dict], List[dict], dict]:
    """Deterministic source-level split with pair integrity.

    * sources linked by a contrast pair (calibration / anti-fabrication)
      form one component so a pair can never be split across train/eval;
    * components containing contrast pairs are TRAIN-LOCKED: the pairs are
      the calibration mechanism and must be seen during training (eval
      abstention comes from approved rows, mirroring the SFT-01 protocol);
    * coverage: every REQUIRED_EVAL_COVERAGE category must appear in eval,
      chosen by densest-component then smallest then digest order;
    * size fill to max(MIN_EVAL_ROWS, EVAL_FRACTION * n).
    """
    by_src: Dict[str, List[dict]] = defaultdict(list)
    for r in rows:
        by_src[r["source_id"]].append(r)
    parent = {s: s for s in by_src}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    locked_components = set()
    for r in rows:
        if r.get("pair_group"):
            srcs = [x["source_id"] for x in rows
                    if x.get("pair_group") == r["pair_group"]]
            for s in srcs[1:]:
                union(srcs[0], s)
            locked_components.add(find(r["source_id"]))
    # recompute locks after unions
    locked_roots = set()
    for r in rows:
        if r.get("pair_group"):
            locked_roots.add(find(r["source_id"]))

    comp_rows: Dict[str, List[dict]] = defaultdict(list)
    comp_of_src = {s: find(s) for s in by_src}
    for r in rows:
        comp_rows[comp_of_src[r["source_id"]]].append(r)

    order = sorted(comp_rows, key=lambda c: digest_key(SEED, c))
    required = set(REQUIRED_EVAL_COVERAGE)
    target = max(MIN_EVAL_ROWS, int(round(EVAL_FRACTION * len(rows))))
    eval_comps: List[str] = []
    eval_set: set = set()
    covered, eval_rows_n = set(), 0

    def cats_of(comp):
        return {r["category"] for r in comp_rows[comp]}

    # pass 1: coverage over unlocked components (densest first)
    for cat in sorted(required):
        if cat in covered:
            continue
        cands = [c for c in order
                 if c not in eval_comps and c not in locked_roots
                 and cat in cats_of(c)]
        cands.sort(key=lambda c: (-sum(1 for r in comp_rows[c]
                                       if r["category"] == cat),
                                  len(comp_rows[c]),
                                  digest_key(SEED + "|cov", c)))
        if not cands:
            continue
        comp = cands[0]
        eval_comps.append(comp)
        eval_set.update(r["source_id"] for r in comp_rows[comp])
        eval_rows_n += len(comp_rows[comp])
        covered |= cats_of(comp)
    # pass 2: size fill (smallest unlocked components first)
    fill = sorted((c for c in order
                   if c not in eval_comps and c not in locked_roots),
                  key=lambda c: (len(comp_rows[c]), digest_key(SEED + "|fill", c)))
    for comp in fill:
        if eval_rows_n >= target:
            break
        eval_comps.append(comp)
        eval_set.update(r["source_id"] for r in comp_rows[comp])
        eval_rows_n += len(comp_rows[comp])

    train_rows, eval_rows = [], []
    for r in sorted(rows, key=lambda r: r["example_id"]):
        if r["source_id"] in eval_set:
            rr = dict(r); rr["split"] = "validation"
            eval_rows.append(rr)
        else:
            rr = dict(r); rr["split"] = "train"
            train_rows.append(rr)
    split_info = {
        "seed": SEED,
        "method": ("source-level, sha256(seed|source_id) order; union-find "
                   "pair components (pairs train-locked); densest-coverage "
                   "then smallest size fill"),
        "eval_target_rows": target,
        "eval_sources": sorted(eval_set),
        "train_sources": sorted(set(by_src) - eval_set),
        "eval_fraction_target": EVAL_FRACTION,
        "eval_rows": len(eval_rows),
        "train_rows": len(train_rows),
        "coverage_required": sorted(required),
        "coverage_achieved": sorted({r["category"] for r in eval_rows} & required),
        "coverage_missing": sorted(required - {r["category"] for r in eval_rows}),
        "pair_components_train_locked": sorted(
            {r["source_id"] for r in rows if r.get("pair_group")}),
    }
    return train_rows, eval_rows, split_info


def pair_stats(rows, pair_meta, prefix="abstain-"):
    counts = Counter(r.get("pair_group") for r in rows
                     if str(r.get("pair_group") or "").startswith(prefix))
    return {
        "built": len(pair_meta),
        "intact_after_dedup": sum(1 for c in counts.values() if c == 2),
        "broken": sorted(g for g, c in counts.items() if c != 2),
        "detail": pair_meta,
    }


def build_all() -> Tuple[List[dict], List[dict], dict]:
    _QREG.clear()
    frozen = load_frozen_sources()
    if frozen_sha256() != FROZEN_EVAL_SHA256:
        raise SystemExit("frozen benchmark hash mismatch - aborting")
    rctx = RightsContext()
    eligible = [s for s in eligible_sources(rctx, frozen)
                if s not in SYNTHETIC_SOURCES]

    # corpus index for eligible sources (one pass)
    corpus_index = corpus_units_by_source(set(eligible))
    units_by_id = {}
    for recs in corpus_index.values():
        for rec in recs:
            units_by_id[rec.get("id") or rec.get("unit_id")] = rec

    pool = read_jsonl(POOL_PATH)
    pool = [r for r in pool if r["source_id"] in set(eligible)]

    frozen_questions = [shingles(c["question"]) for c in read_jsonl(
        os.path.join(ROOT, "data", "evaluation", "dapt01_eval_cases.jsonl"))]

    approved, audit = load_approved(frozen)
    rows = [finalize_approved(r) for r in approved]
    qreg_add(rows)

    per_source: Counter = Counter(r["source_id"] for r in rows)
    used_ids: set = set()

    practice_rows = build_practice_rows(rctx, frozen, pool, corpus_index, per_source, used_ids)
    rows += practice_rows
    qreg_add(practice_rows)
    term_rows = build_terminology_rows(rctx, frozen, corpus_index, per_source, used_ids)
    rows += term_rows
    qreg_add(term_rows)
    hi_rows = build_multilingual_rows(rctx, frozen, corpus_index, "hi", "HINDI",
                                      HI_Q, HI_A, HI_KW, TARGETS["HINDI"])
    gu_rows = build_multilingual_rows(rctx, frozen, corpus_index, "gu", "GUJARATI",
                                      GU_Q, GU_A, GU_KW, TARGETS["GUJARATI"])
    rows += hi_rows + gu_rows
    qreg_add(hi_rows + gu_rows)
    dist_rows = build_distinction_rows(rctx, frozen, corpus_index)
    rows += dist_rows
    qreg_add(dist_rows)
    disc_rows = build_sect_discipline_rows(rctx, frozen, eligible)
    rows += disc_rows
    qreg_add(disc_rows)
    cal_rows, pair_meta = build_calibration_pairs(rctx, frozen, corpus_index, per_source)
    rows += cal_rows
    qreg_add(cal_rows)
    fab_rows = build_antifabrication_rows(rctx, frozen, corpus_index, per_source)
    rows += fab_rows
    qreg_add(fab_rows)
    approved_canon = [(r["question"], r["source_id"]) for r in rows
                      if r["category"] == "CANONICAL_VS_COMMENTARY"
                      and not origin_builder(r).startswith("task67")]
    canon_new = build_canonical_new_rows(rctx, frozen, corpus_index, approved_canon)
    rows += canon_new
    qreg_add(canon_new)

    # --- gates -------------------------------------------------------------
    problems = row_gates(rows, rctx, frozen, frozen_questions)
    grounding_problems = verify_grounding(rows, rctx, units_by_id, corpus_index)
    if problems or grounding_problems:
        for p in (problems + grounding_problems)[:40]:
            print("GATE:", p)
        raise SystemExit(f"row gates failed: {len(problems)} issues, "
                         f"{len(grounding_problems)} grounding issues")

    rows, dropped = dedup(rows)
    if dropped:
        print("DEDUP dropped:", dropped)

    gate_report = gate.measure(rows)
    if gate_report["level"] == "FAIL":
        for f in gate_report["flags"]:
            print("TEMPLATE FAIL:", f)
        raise SystemExit("anti-template gate FAILED")

    train_rows, eval_rows, split_info = assign_split(rows)

    # stats
    all_rows = train_rows + eval_rows
    def dist(vals):
        vals = sorted(vals)
        n = len(vals)
        if not n:
            return {}
        return {"n": n, "min": vals[0], "p25": vals[n // 4], "median": vals[n // 2],
                "p75": vals[(3 * n) // 4], "max": vals[-1],
                "mean": round(sum(vals) / n, 1)}

    def counter(rows_, key):
        return dict(Counter(str(r.get(key) or "UNKNOWN") for r in rows_).most_common())

    stats = {
        "task": 67,
        "seed": SEED,
        "frozen_sha256": frozen_sha256(),
        "frozen_sources_excluded": sorted(frozen),
        "approved_audit": audit,
        "totals": {"train": len(train_rows), "eval": len(eval_rows),
                   "total": len(all_rows)},
        "category_counts": counter(all_rows, "category"),
        "task_category_counts": counter(all_rows, "task_category"),
        "language_counts": counter(all_rows, "language"),
        "sect_counts": {k: v for k, v in sorted(
            Counter((rctx.manifest_row(r["source_id"]).get("sect") or "UNKNOWN")
                    for r in all_rows).items())},
        "knowledge_layer_counts": counter(all_rows, "knowledge_layer"),
        "source_counts": counter(all_rows, "source_id"),
        "distinct_sources": len({r["source_id"] for r in all_rows}),
        "answer_len": dist([len(r["answer"]) for r in all_rows]),
        "answer_len_by_category": {c: dist([len(r["answer"]) for r in all_rows
                                            if r["category"] == c])
                                   for c in sorted({r["category"] for r in all_rows})},
        "question_opener_counts": dict(Counter(
            gate.norm_opener(r["question"], 4) for r in all_rows).most_common(8)),
        "wh_question_counts": dict(Counter(
            (r["question"].split() or [""])[0].lower().rstrip("?:,") for r in all_rows
        ).most_common(12)),
        "attribution_rows": sum(1 for r in all_rows if r["category"] == "SOURCE_ATTRIBUTION"),
        "abstention_rows": sum(1 for r in all_rows
                               if r["category"] == "ABSTENTION/INSUFFICIENT_EVIDENCE"),
        "abstention_answerable": sum(1 for r in all_rows if "answerable" in r.get("tags", [])
                                     and "unanswerable" not in r.get("tags", [])),
        "abstention_unanswerable": sum(1 for r in all_rows if "unanswerable" in r.get("tags", [])),
        "abstention_pairs": pair_stats(all_rows, pair_meta),
        "antifab_pairs_intact": pair_stats(all_rows, [], prefix="antifab-")["intact_after_dedup"],
        "practice_rows": sum(1 for r in all_rows if "practice" in r.get("tags", [])),
        "practice_breakdown": dict(Counter(r.get("practice") for r in all_rows
                                           if "practice" in r.get("tags", [])).most_common()),
        "terminology_rows": sum(1 for r in all_rows if "terminology" in r.get("tags", [])),
        "anti_fabrication_rows": sum(1 for r in all_rows if "anti_fabrication" in r.get("tags", [])),
        "multilingual_rows": sum(1 for r in all_rows if "multilingual" in r.get("tags", [])),
        "sect_contrast_rows": sum(1 for r in all_rows if "sect_contrast" in r.get("tags", [])
                                  or "sect_unknown_discipline" in r.get("tags", [])),
        "canonical_rows": sum(1 for r in all_rows if r["category"] == "CANONICAL_VS_COMMENTARY"),
        "gate_report": gate_report,
        "split": split_info,
        "leakage": {
            "shared_sources_train_eval": sorted(
                {r["source_id"] for r in train_rows} & {r["source_id"] for r in eval_rows}),
            "shared_example_ids": sorted(
                {r["example_id"] for r in train_rows} & {r["example_id"] for r in eval_rows}),
            "frozen_sources_in_dataset": sorted(
                {r["source_id"] for r in all_rows} & frozen),
            "dedup_dropped": dropped,
        },
        "row_gate_problems": problems,
        "grounding_problems": grounding_problems,
        "targets": TARGETS,
        "origin_method_counts": dict(Counter(
            str((r.get("origin") or {}).get("method") if isinstance(r.get("origin"), dict)
                else "legacy") for r in all_rows).most_common()),
        "synthetic_sources_excluded": sorted(SYNTHETIC_SOURCES),
    }
    return train_rows, eval_rows, stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=None, help="override output dir (determinism tests)")
    args = ap.parse_args(argv)
    train_rows, eval_rows, stats = build_all()
    out_train, out_eval, out_stats = OUT_TRAIN, OUT_EVAL, OUT_STATS
    if args.out_dir:
        out_train = os.path.join(args.out_dir, "sft_train_v2.jsonl")
        out_eval = os.path.join(args.out_dir, "sft_eval_v2.jsonl")
        out_stats = os.path.join(args.out_dir, "build_stats.json")
    write_jsonl(out_train, train_rows)
    write_jsonl(out_eval, eval_rows)
    write_json(out_stats, stats)
    print(f"train={len(train_rows)} eval={len(eval_rows)} "
          f"total={len(train_rows) + len(eval_rows)}")
    print(f"gate={stats['gate_report']['level']} "
          f"flags={stats['gate_report']['flags']}")
    print(f"coverage_missing={stats['split']['coverage_missing']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
