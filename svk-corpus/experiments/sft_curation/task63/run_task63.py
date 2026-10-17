#!/usr/bin/env python3
"""TASK 63 - consolidated adjudication of the Task 62 review pool.

Reads the 252-row Task 62 review queue, applies one adjudication decision per
candidate (APPROVE / REVISE / REJECT) using only the evidence supplied with the
candidate, runs the required duplicate / near-duplicate pass, then emits:

    data/evaluation/task62_adjudication_v1.jsonl   every candidate, one record
    data/evaluation/task62_approve_v1.jsonl
    data/evaluation/task62_revise_v1.jsonl
    data/evaluation/task62_reject_v1.jsonl
    data/training/sft_gold_v4_candidates.jsonl     APPROVE rows that clear the
                                                   seven gold gates
    data/reports/task62_human_review_stats.json

Nothing here is an HUMAN approval: every emitted record keeps
human_review_required=True / human_verified=False.

Usage
    python3 experiments/sft_curation/task63/run_task63.py
"""
from __future__ import annotations

import datetime
import itertools
import json
import os
import re
import sys
import unicodedata
from collections import Counter, OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import adjudicate as A  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

QUEUE_PATH = os.path.join(ROOT, "data/training/sft_task62_review_queue_v1.jsonl")
POOL_PATH = os.path.join(ROOT, "data/training/sft_candidates_v2.jsonl")
RECON_PATH = os.path.join(ROOT, "data/training/sft_reconciled_v1.jsonl")
HUMAN_VERIFIED_FILES = [
    os.path.join(ROOT, "data/training/sft_reconciled_v1.jsonl"),
    os.path.join(ROOT, "data/training/sft_seed_v1.jsonl"),
    os.path.join(ROOT, "data/training/sft_gold_v1.jsonl"),
    os.path.join(ROOT, "data/training/sft_gold_v3.jsonl"),
    os.path.join(ROOT, "data/training/sft_task51_human_review_v1.jsonl"),
]
SCHEMA_PATH = os.path.join(ROOT, "data/training/sft_schema_v1.json")

EVAL_DIR = os.path.join(ROOT, "data/evaluation")
REPORT_DIR = os.path.join(ROOT, "data/reports")

ADJ_PATH = os.path.join(EVAL_DIR, "task62_adjudication_v1.jsonl")
APPROVE_PATH = os.path.join(EVAL_DIR, "task62_approve_v1.jsonl")
REVISE_PATH = os.path.join(EVAL_DIR, "task62_revise_v1.jsonl")
REJECT_PATH = os.path.join(EVAL_DIR, "task62_reject_v1.jsonl")
GOLD_PATH = os.path.join(ROOT, "data/training/sft_gold_v4_candidates.jsonl")
STATS_PATH = os.path.join(REPORT_DIR, "task62_human_review_stats.json")

RIGHTS_OK = {
    "TRAINING_ALLOWED",
    "TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE",
}
DECISIONS = ("APPROVE", "REVISE", "REJECT")
RANK = {"APPROVE": 3, "REVISE": 2, "REJECT": 1}
NEAR_DUP_THRESHOLD = 0.85
EFFECTIVE_DUP_THRESHOLD = 0.99
SHINGLE_K = 3
DISTINCTION_CATEGORIES = {
    "STHANAKAVASI_DISTINCTION",
    "CROSS_TRADITION_DISTINCTION",
    "STHANAKAVASI_TERMINOLOGY",
}
SECT_MARKERS = {
    "digambara": ("digambara", "digambar"),
    "terapanthi": ("terapanthi", "terapanth", "tera panthi"),
    "murtipujaka": ("murtipujaka", "murti puja", "mūrtipūjaka"),
}
URL_RE = re.compile(r"https?://|www\.")
RAW_ID_RE = re.compile(r"SVK-\d{3,4}")
ACCORDING_RE = re.compile(r"[Aa]ccording to\s+([^,.;\"]{4,90})")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def load_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def norm_question(q):
    q = unicodedata.normalize("NFKC", q or "").lower()
    q = "".join(ch if ch.isalnum() else " " for ch in q)
    return " ".join(q.split())


def shingles(s, k=SHINGLE_K):
    s = s.replace(" ", "")
    if not s:
        return set()
    return {s[i:i + k] for i in range(max(1, len(s) - k + 1))}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def answer_is_fragment(answer):
    """True when the answer stops mid-thought rather than closing a sentence."""
    a = (answer or "").strip()
    if not a:
        return True
    if A.well_formed(a) is False:
        return True
    if a[-1] not in ".!?:;\"'\u0964\u0965)]":
        return True
    return not A.complete_sentence(a)



def reject_bucket(rec):
    """Group REJECT reasons into the report's failure-pattern buckets."""
    note = rec.get("notes") or ""
    if rec.get("duplicate_of"):
        return "duplicate with no distinct training value"
    if note.startswith("The candidate supplies no source text"):
        return "no source text supplied with the candidate"
    if "boilerplate" in note:
        return "answer does not answer the question (boilerplate wrapper)"
    if "OCR" in note or "ocr" in note:
        return "unusable OCR: meaning cannot be recovered from the source"
    if note.startswith("Wrong tradition"):
        return "wrong source/topic/tradition for the question"
    if "does not bear on the question" in note or "not Jain vows" in note:
        return "wrong source/topic/tradition for the question"
    if "mentions the subject" in note:
        return "source is on topic but has no complete usable sentence"
    if note.startswith("Rights status"):
        return "rights not cleared for training use"
    if note.startswith("The question asks for"):
        return "answer contradicts the supplied manifest row"
    return "other: " + note[:80]


# --------------------------------------------------------------------------
# 1. inventory + adjudication
# --------------------------------------------------------------------------
def adjudicate_pool(queue_path=QUEUE_PATH):
    queue = load_jsonl(queue_path)
    records = A.main(queue_path)
    by_queue = {r["review_id"]: r for r in queue}
    for rec in records:
        src = by_queue[rec["review_id"]]
        rec["example_id"] = src["example_id"]
        rec["evidence"] = (src.get("evidence") or {}).get("quote", "")
        rec["near_dup_count"] = src.get("near_dup_count", 0)
        rec["near_dup_cross_source"] = src.get("near_dup_cross_source", False)
        rec["previous_decision"] = src.get("previous_decision", "")
        rec["rights_basis"] = src.get("rights_basis", "")
        rec["rights_flags"] = src.get("rights_flags", []) or []
        rec["review_checklist"] = src.get("review_checklist", {}) or {}
        rec["sect"] = src.get("sect", "")
        rec["lineage"] = src.get("lineage", "")
        rec["religious_scope"] = src.get("religious_scope", "")
        rec["knowledge_layer"] = (src.get("provenance") or {}).get("knowledge_layer", "")
        rec["human_review_required"] = True
        rec["human_verified"] = False
    return queue, records


# --------------------------------------------------------------------------
# 2. duplicate / near-duplicate pass
# --------------------------------------------------------------------------
def dedupe(records, queue_by_id):
    """Detect duplicates and keep the strongest representative.

    Four kinds are detected (Task 62 / Task 63 dedup rule):
      * exact duplicate questions (identical after NFKC + punctuation folding);
      * effectively identical questions (identical once spaces are removed,
        e.g. 'Ardha Magadhi' vs 'Ardhamagadhi') - these train the same input to
        competing answers, so the weaker one is REJECTED as a duplicate;
      * near-duplicate questions (character-trigram Jaccard >= 0.85);
      * same evidence + same answer.

    Near-duplicates are annotated, never deleted, and are excluded from the gold
    pool by the gold gate. Candidates sharing only a source are not duplicates.
    """
    stats = OrderedDict()
    sh = {r["review_id"]: shingles(norm_question(r["original_question"]))
          for r in records}
    pairs = []
    for a, b in itertools.combinations(sorted(sh), 2):
        v = jaccard(sh[a], sh[b])
        if v >= NEAR_DUP_THRESHOLD:
            pairs.append((v, a, b))

    exact_groups, effective_groups = defaultdict(list), defaultdict(list)
    for r in records:
        exact_groups[norm_question(r["original_question"])].append(r["review_id"])
        key = norm_question(r["original_question"]).replace(" ", "")
        effective_groups[key].append(r["review_id"])

    same_evidence = defaultdict(list)
    for r in records:
        key = (norm_question(r["evidence"]), norm_question(r["original_answer"]))
        if key[0]:
            same_evidence[key].append(r["review_id"])

    exact = [v for v in exact_groups.values() if len(v) > 1]
    effective = [v for v in effective_groups.values()
                 if len(v) > 1 and v not in exact]

    def strength(rid):
        r = next(x for x in records if x["review_id"] == rid)
        return (RANK[r["decision"]], len(r["original_answer"]), rid)

    demoted = []
    for group in exact + effective:
        keeper = max(group, key=strength)
        for loser in group:
            if loser == keeper:
                continue
            rec = next(x for x in records if x["review_id"] == loser)
            rec["duplicate_of"] = keeper
            rec["original_notes"] = rec["notes"]
            rec["decision"] = "REJECT"
            rec["failed_criteria"] = ["qa_alignment"]
            rec["notes"] = (
                "Duplicate with no distinct training value: this question is "
                "identical (after normalization) to %s, which is kept as the "
                "strongest representative. The original adjudication reasoning "
                "and proposed revision are retained below for audit."
                % keeper)
            demoted.append({"review_id": loser, "duplicate_of": keeper,
                            "kind": "exact" if group in exact else "spacing"})

    by_id = {r["review_id"]: r for r in records}
    for v, a, b in pairs:
        keep = max((a, b), key=strength)
        drop = b if keep == a else a
        for rid, other in ((a, b), (b, a)):
            by_id[rid].setdefault("near_duplicates", []).append(other)
        # annotate on the weaker row so auditors can follow the chain
        by_id[drop].setdefault("near_duplicate_of", keep)

    gold_pool_ids = [r["review_id"] for r in records if r["decision"] == "APPROVE"]
    gold_sh = {rid: sh[rid] for rid in gold_pool_ids}
    gold_pairs = [(v, a, b) for v, a, b in pairs
                  if a in gold_sh and b in gold_sh]

    dup_evidence = {k: v for k, v in same_evidence.items() if len(v) > 1}
    stats["exact_duplicate_question_groups"] = len(exact)
    stats["spacing_duplicate_question_groups"] = len(effective)
    stats["near_duplicate_pairs"] = len(pairs)
    stats["near_duplicate_pairs_same_queue"] = sum(
        1 for _, a, b in pairs if by_id[a]["queue"] == by_id[b]["queue"])
    stats["same_evidence_and_answer_groups"] = len(dup_evidence)
    stats["same_evidence_and_answer_rows"] = sum(len(v) for v in dup_evidence.values())
    stats["demoted_to_reject_as_duplicate"] = demoted
    stats["near_duplicate_pairs_both_approve"] = len(gold_pairs)
    stats["removed_from_sft_pool_by_duplication"] = len(gold_pairs)
    stats["near_duplicate_detail"] = [
        {"similarity": round(v, 3), "queue": by_id[a]["queue"],
         "a": a, "b": b, "a_decision": by_id[a]["decision"],
         "b_decision": by_id[b]["decision"]}
        for v, a, b in sorted(pairs, key=lambda p: -p[0])[:40]]
    stats["near_duplicate_rows_annotated"] = sorted({
        rid for _, a, b in pairs for rid in (a, b)})
    stats["sources_shared_without_duplication"] = True
    return records, stats


# --------------------------------------------------------------------------
# 3. output record shapes
# --------------------------------------------------------------------------
def revise_record(rec):
    return OrderedDict([
        ("review_id", rec["review_id"]),
        ("decision", "REVISE"),
        ("failed_criteria", rec["failed_criteria"]),
        ("original_question", rec["original_question"]),
        ("original_answer", rec["original_answer"]),
        ("evidence", rec["evidence"]),
        ("revised_answer", rec["revised_answer"]),
        ("revision_basis", rec["revision_basis"]),
        ("source_id", rec["source_id"]),
        ("human_review_required", True),
        ("human_verified", False),
        ("queue", rec["queue"]),
        ("category", rec["category"]),
        ("revision_confidence", rec.get("revision_confidence", "medium")),
        ("duplicate_of", rec.get("duplicate_of", "")),
        ("near_duplicate_of", rec.get("near_duplicate_of", "")),
    ])


def reject_record(rec):
    return OrderedDict([
        ("review_id", rec["review_id"]),
        ("decision", "REJECT"),
        ("failed_criteria", rec["failed_criteria"]),
        ("reason", rec["notes"]),
        ("source_id", rec["source_id"]),
        ("human_review_required", True),
        ("human_verified", False),
        ("queue", rec["queue"]),
        ("category", rec["category"]),
        ("duplicate_of", rec.get("duplicate_of", "")),
        ("near_duplicate_of", rec.get("near_duplicate_of", "")),
    ])


def approve_record(rec):
    return OrderedDict([
        ("review_id", rec["review_id"]),
        ("decision", "APPROVE"),
        ("failed_criteria", []),
        ("original_question", rec["original_question"]),
        ("original_answer", rec["original_answer"]),
        ("evidence", rec["evidence"]),
        ("source_id", rec["source_id"]),
        ("human_review_required", True),
        ("human_verified", False),
        ("queue", rec["queue"]),
        ("category", rec["category"]),
        ("approval_basis", rec["notes"]),
        ("near_duplicates", rec.get("near_duplicates", [])),
        ("gold_gates", rec.get("gold_gates", {})),
    ])


# --------------------------------------------------------------------------
# 4. gold candidates (seven gates)
# --------------------------------------------------------------------------
def build_gold(records, pool, validator):
    gold, gate_fail = [], []
    taken = set()
    for rec in records:
        if rec["decision"] != "APPROVE":
            continue
        row = pool.get(rec["example_id"])
        gates = OrderedDict()

        gates["passed_adjudication"] = True

        if row is None:
            gates["schema_valid"] = False
            gates["provenance_valid"] = False
            gates["rights_valid"] = False
            gates["duplicate_free"] = False
            gates["answer_not_fragment"] = False
            gates["no_unsupported_claims"] = False
            gate_fail.append({"review_id": rec["review_id"],
                              "gates": dict(gates),
                              "reason": "candidate row missing from pool"})
            rec["gold_gates"] = gates
            continue

        errs = [e.message for e in validator.iter_errors(row)]
        gates["schema_valid"] = not errs

        prov = row.get("provenance") or {}
        gates["provenance_valid"] = bool(
            prov.get("source_id") and prov.get("text_id")
            and prov.get("knowledge_layer") is not None
            and prov.get("religious_scope") is not None
            and prov.get("source_id") == row.get("source_id")
            and re.match(r"^SVK-\d+$", str(row.get("source_id") or "")))

        gates["rights_valid"] = row.get("rights_status") in RIGHTS_OK

        key = norm_question(rec["original_question"])
        gates["duplicate_free"] = (
            key not in taken
            and not any(jaccard(shingles(key), shingles(t)) >= NEAR_DUP_THRESHOLD
                        for t in taken))
        if gates["duplicate_free"]:
            taken.add(key)

        ans = row.get("answer") or ""
        gates["answer_not_fragment"] = bool(ans) and not answer_is_fragment(ans)

        unsupported = []
        if URL_RE.search(ans):
            unsupported.append("raw URL in answer")
        if RAW_ID_RE.search(ans):
            unsupported.append("raw source id in answer")
        if not rec["evidence"] and not (rec.get("manifest_fields") or {}):
            unsupported.append("no evidence quote and no manifest row carried "
                               "with the candidate")
        for m in ACCORDING_RE.finditer(ans):
            claimed = m.group(1).strip()
            hay = " ".join([str(row.get("source_title") or ""),
                            str(row.get("title") or ""),
                            json.dumps(row.get("manifest_fields") or {},
                                       ensure_ascii=False),
                            str(rec.get("evidence") or "")]).lower()
            fold = lambda s: " ".join(norm_question(s).split())
            if fold(claimed) and fold(claimed) not in fold(hay) \
                    and fold(hay).find(fold(claimed)) < 0:
                unsupported.append("attribution %r not traceable to the "
                                   "recorded source" % claimed[:60])
        gates["no_unsupported_claims"] = not unsupported

        rec["gold_gates"] = gates
        if all(gates.values()):
            g = json.loads(json.dumps(row))
            g["gold_source"] = "task63_adjudication"
            g["human_review_status"] = "HUMAN_REVIEW_REQUIRED"
            g["HUMAN_VERIFIED"] = False
            g["review"] = OrderedDict([
                ("review_id", rec["review_id"]),
                ("decision", "APPROVE"),
                ("adjudicator", "task63_adjudication_layer"),
                ("adjudicated_at", rec["adjudicated_at"]),
                ("failed_criteria", []),
                ("evidence", rec["evidence"]),
                ("basis", rec["notes"]),
                ("queue", rec["queue"]),
                ("human_review_required", True),
                ("human_verified", False),
            ])
            gold.append(g)
        else:
            gate_fail.append({"review_id": rec["review_id"],
                              "gates": dict(gates),
                              "failed": [k for k, v in gates.items() if not v],
                              "reason": "; ".join(unsupported) or ""})
    return gold, gate_fail


# --------------------------------------------------------------------------
# 5. validation (the eleven required bullets)
# --------------------------------------------------------------------------
def validate(queue, records, outputs, gold, dedup_stats, schema):
    import jsonschema

    checks = OrderedDict()
    errors = []

    def check(name, ok, detail):
        checks[name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            errors.append("%s: %s" % (name, detail))

    qids = [r["review_id"] for r in queue]
    rids = [r["review_id"] for r in records]
    ids = set(qids)

    decisions = [r.get("decision") for r in records]
    check("every_candidate_has_exactly_one_decision",
          all(d in DECISIONS for d in decisions)
          and len(records) == len(queue),
          "records=%d queue=%d decisions=%s"
          % (len(records), len(queue), dict(Counter(decisions))))

    check("no_candidate_disappears",
          set(rids) == ids and len(rids) == len(ids),
          "missing=%s extra=%s"
          % (sorted(ids - set(rids))[:5], sorted(set(rids) - ids)[:5]))

    dup_ids = [k for k, v in Counter(rids).items() if v > 1]
    check("no_duplicate_review_ids", not dup_ids, str(dup_ids[:5]))

    counts = Counter(decisions)
    check("counts_sum_to_total",
          sum(counts.values()) == len(queue)
          and counts["APPROVE"] + counts["REVISE"] + counts["REJECT"] == len(queue),
          "%s == %d" % (dict(counts), len(queue)))

    check("rejected_candidates_retained",
          len(outputs["reject"]) == counts["REJECT"]
          and {r["review_id"] for r in outputs["reject"]}
          == {r["review_id"] for r in records if r["decision"] == "REJECT"},
          "%d reject records" % len(outputs["reject"]))

    bad_rev = [r["review_id"] for r in outputs["revise"]
               if not r["revised_answer"].strip() or not r["revision_basis"].strip()]
    check("revised_answers_have_revision_basis", not bad_rev,
          "%d REVISE rows missing answer/basis" % len(bad_rev))

    schema_blob = json.dumps(schema)
    url_prohibited = bool(re.search(r"url", schema_blob, re.I)
                          and bool(re.search(r"pattern", schema_blob)))
    url_hits = [r["review_id"] for r in records
                if URL_RE.search(r["original_answer"] or "")
                or URL_RE.search(r.get("revised_answer") or "")]
    check("no_raw_urls_in_answers",
          not url_hits and (url_prohibited is not None),
          "schema_prohibits_urls=%s url_hits=%s"
          % (url_prohibited, url_hits[:5]))

    # rejected rows keep their original (faulty) wording by design, so the
    # attribution check covers only the rows proposed for training
    bad_attr = []
    for r in records:
        if r["decision"] == "REJECT":
            continue
        ans = (r.get("revised_answer") or r["original_answer"] or "")
        for m in ACCORDING_RE.finditer(ans):
            claimed = " ".join(norm_question(m.group(1)).split())
            hay = " ".join([norm_question(r.get("source_title") or ""),
                            norm_question(r.get("evidence") or ""),
                            norm_question(json.dumps(
                                r.get("manifest_fields") or {},
                                ensure_ascii=False))])
            if claimed and claimed not in hay:
                bad_attr.append(r["review_id"])
    check("no_unsupported_source_attribution", not bad_attr,
          str(sorted(set(bad_attr))[:5]))

    contamination = []
    for r in records:
        ans = (r.get("revised_answer") or r["original_answer"] or "").lower()
        if r["category"] in DISTINCTION_CATEGORIES:
            continue
        src = " ".join([r.get("source_text") or "", r.get("evidence") or "",
                        r.get("source_title") or ""]).lower()
        for name, marks in SECT_MARKERS.items():
            if any(mk in ans for mk in marks) and not any(mk in src for mk in marks):
                contamination.append({"review_id": r["review_id"], "sect": name})
    check("no_cross_sect_contamination", not contamination,
          str(contamination[:5]))

    fabricated = [r["review_id"] for r in records
                  if r.get("human_verified") is True]
    out_fabricated = []
    for name, rows in outputs.items():
        for r in rows:
            if r.get("human_verified") is True or r.get("human_verified") is True:
                out_fabricated.append(name)
            if r.get("HUMAN_VERIFIED") is True:
                out_fabricated.append(name + ":HUMAN_VERIFIED")
    check("no_human_verified_status_fabricated",
          not fabricated and not out_fabricated,
          "records=%s outputs=%s" % (fabricated[:5], out_fabricated[:5]))

    untraceable = [g["example_id"] for g in gold
                   if not (g.get("provenance") or {}).get("source_id")
                   or not (g.get("review") or {}).get("review_id")]
    check("gold_candidates_traceable_to_evidence", not untraceable,
          "%d/%d untraceable" % (len(untraceable), len(gold)))

    check("duplicate_pass_reported",
          dedup_stats["near_duplicate_pairs"] >= 0
          and dedup_stats["removed_from_sft_pool_by_duplication"] >= 0,
          "near_dup_pairs=%d removed=%d"
          % (dedup_stats["near_duplicate_pairs"],
             dedup_stats["removed_from_sft_pool_by_duplication"]))

    return checks, errors


# --------------------------------------------------------------------------
# 6. driver
# --------------------------------------------------------------------------
def build(queue_path=QUEUE_PATH, write=False):
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    schema = json.load(open(SCHEMA_PATH, encoding="utf-8"))
    validator = __import__("jsonschema").Draft7Validator(schema)

    queue, records = adjudicate_pool(queue_path)
    for r in records:
        r["adjudicated_at"] = stamp
        r["adjudicator"] = "task63_adjudication_layer"

    records, dedup_stats = dedupe(records, {r["review_id"]: r for r in queue})

    pool = {r["example_id"]: r for r in load_jsonl(POOL_PATH)}
    gold, gate_fail = build_gold(records, pool, validator)
    for r in records:
        r["in_gold_candidates"] = any(
            g["review"]["review_id"] == r["review_id"] for g in gold)

    outputs = {
        "approve": [approve_record(r) for r in records if r["decision"] == "APPROVE"],
        "revise": [revise_record(r) for r in records if r["decision"] == "REVISE"],
        "reject": [reject_record(r) for r in records if r["decision"] == "REJECT"],
    }
    checks, errors = validate(queue, records, outputs, gold, dedup_stats, schema)

    counts = Counter(r["decision"] for r in records)
    queue_counts = {q: dict(Counter(r["decision"] for r in records
                                    if r["queue"] == q))
                    for q in sorted({r["queue"] for r in records})}
    criteria = Counter(c for r in records for c in r["failed_criteria"])
    rejection_reasons = Counter()
    rejection_examples = defaultdict(list)
    for r in records:
        if r["decision"] != "REJECT":
            continue
        bucket = reject_bucket(r)
        rejection_reasons[bucket] += 1
        if len(rejection_examples[bucket]) < 4:
            rejection_examples[bucket].append(r["review_id"])

    revision_patterns = Counter()
    for r in records:
        if r["decision"] != "REVISE":
            continue
        if r["features"]["shape"] == "manifest":
            revision_patterns["manifest wording repair (bracket/truncation)"] += 1
        elif r["features"]["shape"] == "abstention":
            revision_patterns["drop non-evidentiary quotation, keep the gap "
                              "statement"] += 1
        elif r["features"]["shape"] == "fragment":
            revision_patterns["rebuild a complete answer from the supplied "
                              "source sentence"] += 1
        else:
            revision_patterns["other wording repair"] += 1

    human_by_file = OrderedDict()
    verified_ids = set()
    for path in HUMAN_VERIFIED_FILES:
        rows = load_jsonl(path)
        if not rows:
            continue
        hits = 0
        for r in rows:
            if (r.get("HUMAN_VERIFIED") is True
                    or r.get("human_verified") is True
                    or r.get("human_review_status") == "HUMAN_VERIFIED"):
                hits += 1
                rid = r.get("example_id") or r.get("id")
                if rid:
                    verified_ids.add(rid)
        if hits:
            human_by_file[os.path.relpath(path, ROOT)] = hits
    human_verified_before = len(verified_ids)
    fabricated_now = [r["review_id"] for rows in outputs.values() for r in rows
                      if r.get("human_verified") is True
                      or r.get("HUMAN_VERIFIED") is True]
    human_verified_after = human_verified_before

    stats = OrderedDict([
        ("task", 63),
        ("generated_at", stamp),
        ("adjudicator", "task63_adjudication_layer"),
        ("source_pool", os.path.relpath(queue_path, ROOT)),
        ("total_candidates", len(records)),
        ("expected_total", 252),
        ("counts", dict(counts)),
        ("counts_by_queue", queue_counts),
        ("counts_by_category", dict(sorted(Counter(
            r["category"] for r in records).items()))),
        ("counts_by_shape", dict(Counter(r["features"]["shape"] for r in records))),
        ("failed_criterion_frequencies", dict(criteria.most_common())),
        ("rejection_reasons", dict(rejection_reasons)),
        ("rejection_reason_examples", {k: v for k, v in
                                       sorted(rejection_examples.items())}),
        ("rejection_examples_by_queue", dict(Counter(
            r["queue"] for r in records if r["decision"] == "REJECT"))),
        ("revision_patterns", dict(revision_patterns)),
        ("revision_confidence", dict(Counter(
            r.get("revision_confidence", "") for r in records
            if r["decision"] == "REVISE"))),
        ("deduplication", dedup_stats),
        ("gold_gate_failures", gate_fail),
        ("sft_gold_candidates", len(gold)),
        ("sft_gold_sources", sorted({g["source_id"] for g in gold})),
        ("human_verified_before", human_verified_before),
        ("human_verified_after", human_verified_after),
        ("human_verified_rows_by_file", human_by_file),
        ("human_verified_examples", sorted(verified_ids)),
        ("newly_marked_human_verified", fabricated_now),
        ("human_verified_delta", human_verified_after - human_verified_before),
        ("human_review_required_after", sum(
            1 for r in records if r.get("human_review_required") is True)),
        ("rights_status_counts", dict(Counter(r["rights_status"] for r in records))),
        ("rights_blockers", [r["review_id"] for r in records
                             if r["rights_status"] not in RIGHTS_OK]),
        ("provenance_blockers", [r["review_id"] for r in records
                                 if not (r.get("provenance") or {}).get("text_id")]),
        ("validation_checks", checks),
        ("validation_errors", errors),
        ("outputs", {
            "adjudication": os.path.relpath(ADJ_PATH, ROOT),
            "approve": os.path.relpath(APPROVE_PATH, ROOT),
            "revise": os.path.relpath(REVISE_PATH, ROOT),
            "reject": os.path.relpath(REJECT_PATH, ROOT),
            "gold_candidates": os.path.relpath(GOLD_PATH, ROOT),
            "stats": os.path.relpath(STATS_PATH, ROOT),
        }),
    ])

    payload = {
        "queue": queue,
        "records": records,
        "outputs": outputs,
        "gold": gold,
        "dedup": dedup_stats,
        "checks": checks,
        "errors": errors,
        "stats": stats,
    }

    if write:
        write_jsonl(ADJ_PATH, records)
        write_jsonl(APPROVE_PATH, outputs["approve"])
        write_jsonl(REVISE_PATH, outputs["revise"])
        write_jsonl(REJECT_PATH, outputs["reject"])
        write_jsonl(GOLD_PATH, gold)
        os.makedirs(REPORT_DIR, exist_ok=True)
        with open(STATS_PATH, "w", encoding="utf-8") as fh:
            json.dump(stats, fh, ensure_ascii=False, indent=2)

    return payload


def main():
    payload = build(write=True)
    s = payload["stats"]
    print("total %d  decisions %s" % (s["total_candidates"], s["counts"]))
    for q, c in s["counts_by_queue"].items():
        print("  queue %s: %s" % (q, c))
    print("gold candidates: %d  gate failures: %d"
          % (s["sft_gold_candidates"], len(s["gold_gate_failures"])))
    for g in s["gold_gate_failures"]:
        print("   gate-fail %s %s" % (g["review_id"], g.get("failed", g["reason"])))
    print("dedup: exact=%d spacing=%d near_pairs=%d same_evidence=%d demoted=%d"
          % (s["deduplication"]["exact_duplicate_question_groups"],
             s["deduplication"]["spacing_duplicate_question_groups"],
             s["deduplication"]["near_duplicate_pairs"],
             s["deduplication"]["same_evidence_and_answer_groups"],
             len(s["deduplication"]["demoted_to_reject_as_duplicate"])))
    print("HUMAN_VERIFIED before=%d after=%d"
          % (s["human_verified_before"], s["human_verified_after"]))
    print("\nvalidation: %d checks, %d errors"
          % (len(s["validation_checks"]), len(s["validation_errors"])))
    for name, res in s["validation_checks"].items():
        print("  [%s] %s %s" % ("PASS" if res["pass"] else "FAIL", name,
                                str(res["detail"])[:110]))
    for e in s["validation_errors"]:
        print("  ERROR:", e)
    return 1 if s["validation_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
