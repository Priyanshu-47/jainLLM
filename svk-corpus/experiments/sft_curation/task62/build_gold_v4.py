#!/usr/bin/env python3
"""TASK 62 stage 2: build sft_gold_v4 from human review decisions.

Inputs
    data/training/sft_human_review_v2.jsonl   human decisions (APPROVE/REVISE/REJECT)
    data/training/sft_task62_review_queue_v1.jsonl
    data/training/sft_candidates_v2.jsonl     authoritative candidate records
    data/training/sft_reconciled_v1.jsonl     prior HUMAN_VERIFIED rows
    prior review logs                         to decide which prior rows still stand

Outputs
    data/training/sft_gold_v4.jsonl
    data/training/sft_gold_v4_{train,validation,test}.jsonl
    data/training/task62_gold_build.json      machine-readable stats for the report

Rules
    * Only human APPROVE decisions and prior rows whose decision history still
      stands enter gold. Nothing is auto-approved; the script never invents a
      decision.
    * Candidate source records are never modified - gold rows are copies.
    * Splits are source-level and deterministic: no source ever appears in two
      splits, and no near-duplicate question pair (J>=0.85) straddles splits.
"""
import hashlib
import json
import math
import os
import re
import unicodedata
from collections import Counter, OrderedDict, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# optional overrides so the builder can be exercised against a scratch review
# file without ever touching the real human-review output
OUT_DIR = os.environ.get("TASK62_GOLD_DIR") or os.path.join(ROOT, "data/training")

QUEUE = os.path.join(ROOT, "data/training/sft_task62_review_queue_v1.jsonl")
POOL = os.path.join(ROOT, "data/training/sft_candidates_v2.jsonl")
RECON = os.path.join(ROOT, "data/training/sft_reconciled_v1.jsonl")
REVIEWS = os.environ.get("TASK62_REVIEW_PATH") or os.path.join(
    ROOT, "data/training/sft_human_review_v2.jsonl")
SCHEMA = os.path.join(ROOT, "data/training/sft_schema_v1.json")
AUDIT = os.path.join(ROOT, "data/training/sft_audit_v1.json")
EVAL_CASES = os.path.join(ROOT, "data/evaluation/dapt01_eval_cases.jsonl")

GOLD = os.path.join(OUT_DIR, "sft_gold_v4.jsonl")
SPLITS = {s: os.path.join(OUT_DIR, "sft_gold_v4_%s.jsonl" % s)
          for s in ("train", "validation", "test")}
STATS = os.path.join(OUT_DIR, "task62_gold_build.json")

PRIOR_LOGS = [
    os.path.join(ROOT, "data/training/sft_human_review_results_v1.jsonl"),
    os.path.join(ROOT, "data/training/sft_revision_human_review_v1.jsonl"),
    os.path.join(ROOT, "data/training/sft_task51_human_review_v1.jsonl"),
]

RIGHTS_OK = {
    "TRAINING_ALLOWED",
    "TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE",
}
NEAR_DUP_THRESHOLD = 0.85
SHINGLE_K = 3
# quality_flags values that a human approval has resolved
RESOLVED_FLAGS = {"needs_review", "synthetic_unverified"}


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


def new_example_id(source_id, question, answer, taken):
    sid = (source_id or "unknown").lower()
    base = hashlib.sha256((question + "||" + answer).encode("utf-8")).hexdigest()[:8]
    eid = "%s:qa:%s" % (sid, base)
    n = 0
    while eid in taken:
        n += 1
        seed = hashlib.sha256((question + "||" + answer + "||%d" % n)
                              .encode("utf-8")).hexdigest()[:8]
        eid = "%s:qa:%s" % (sid, seed)
    return eid


# --------------------------------------------------------------------------
# 1. review state
# --------------------------------------------------------------------------
def load_reviews():
    """example_id -> latest review record (the v2 file is rewritten atomically)."""
    state = {}
    for rec in load_jsonl(REVIEWS):
        if rec.get("example_id"):
            state[rec["example_id"]] = rec
    return state


def prior_final_decisions():
    """review_ref -> chronological decision list from the append-only review logs."""
    seq = defaultdict(list)
    for path in PRIOR_LOGS:
        for i, rec in enumerate(load_jsonl(path)):
            ref = (rec.get("candidate_id") or rec.get("example_id")
                   or rec.get("review_id") or "")
            ts = rec.get("reviewed_at") or rec.get("review_timestamp") or ""
            seq[ref].append((ts or "1970-01-00", i, rec.get("decision", "")))
    for ref in seq:
        seq[ref].sort()
    return seq


def prior_final_decision(ref, seq):
    decisions = [d for _, _, d in seq.get(ref, []) if d]
    return decisions[-1] if decisions else ""


# --------------------------------------------------------------------------
# 2. row construction
# --------------------------------------------------------------------------
def gold_row_from_candidate(pool_row, review, reviewer):
    """Copy a candidate record into a gold record carrying the human decision."""
    row = json.loads(json.dumps(pool_row))
    answer = row["answer"]
    if review.get("answer_edited") and review.get("reviewed_answer"):
        answer = review["reviewed_answer"]
        row["answer"] = answer
        row["messages"] = [
            {"role": "user", "content": row["question"]},
            {"role": "assistant", "content": answer},
        ]
    row["quality_flags"] = [f for f in row.get("quality_flags", [])
                            if f not in RESOLVED_FLAGS]
    row["human_review_status"] = "HUMAN_VERIFIED"
    row["HUMAN_VERIFIED"] = True
    row["curation_class"] = "HUMAN_VERIFIED_APPROVED"
    row["gold_source"] = "task62_review"
    origin = dict(row.get("origin") or {})
    origin.setdefault("method", "synthetic_qa_generation")
    origin["reviewer"] = review.get("reviewer") or reviewer
    origin["confidence"] = "high"
    row["origin"] = origin
    rubric = review.get("review_rubric") or {}
    row["review"] = OrderedDict([
        ("review_id", review.get("review_id")),
        ("decision", "APPROVE"),
        ("reviewer", review.get("reviewer") or reviewer),
        ("review_timestamp", review.get("review_timestamp")),
        ("feedback", review.get("feedback", "")),
        ("answer_edited", bool(review.get("answer_edited"))),
        ("queue", review.get("queue") or ""),
        ("rubric_pass", sorted(k for k, v in rubric.items() if v == "PASS")),
        ("rubric_fail", sorted(k for k, v in rubric.items() if v == "FAIL")),
        ("rubric_not_assessed", sorted(k for k, v in rubric.items()
                                        if v not in ("PASS", "FAIL", "N/A"))),
    ])
    return row


def normalize_prior_row(prior_row, taken, decision_basis):
    """Make a prior HUMAN_VERIFIED row schema-valid without touching its content."""
    row = json.loads(json.dumps(prior_row))
    legacy_id = row.get("example_id", "")
    non_enum = [f for f in (row.get("quality_flags") or [])
                if f not in {"needs_review", "low_confidence", "conflicting_info",
                             "ocr_noisy", "translation_uncertain",
                             "synthetic_unverified"}]
    enum_flags = [f for f in (row.get("quality_flags") or []) if f not in non_enum]

    sid = row.get("source_id") or "unknown"
    new_id = new_example_id(sid, row["question"], row["answer"], taken)

    row["legacy_example_id"] = legacy_id
    row["original_example_id"] = legacy_id
    row["example_id"] = new_id
    row["quality_flags"] = [f for f in enum_flags if f not in RESOLVED_FLAGS]
    if non_enum:
        row["quality_flags_notes"] = non_enum
        notes = row.get("audit_notes") or []
        if isinstance(notes, str):
            notes = [notes]
        notes = list(notes) + ["quality_flags moved to quality_flags_notes "
                               "for schema v1 compliance: " + n for n in non_enum]
        row["audit_notes"] = notes

    prov = row.get("provenance") or {}
    if prov.get("source_quality") == "UNMEASURED":
        prov["source_quality"] = "UNKNOWN"
        row.setdefault("quality_flags_notes", []).append(
            "provenance.source_quality 'UNMEASURED' -> 'UNKNOWN' (schema enum)")
        row["provenance"] = prov

    row["human_review_status"] = "HUMAN_VERIFIED"
    row["HUMAN_VERIFIED"] = True
    row["gold_source"] = "prior_verified"
    row["review"] = decision_basis
    return row


# --------------------------------------------------------------------------
# 3. split assignment
# --------------------------------------------------------------------------
def preferred_split(rows_for_source):
    order = {"test": 0, "validation": 1, "train": 2,
             "unassigned_not_in_domain_train": 3}
    cands = [r.get("split_candidate") or "train" for r in rows_for_source]
    return sorted(cands, key=lambda c: order.get(c, 4))[0]


def assign_splits(gold_rows, eval_sources):
    """Deterministic source-level split with size-aware, auditable enlargement."""
    by_source = defaultdict(list)
    for r in gold_rows:
        by_source[r["source_id"]].append(r)
    total = len(gold_rows)

    pref = {sid: preferred_split(rs) for sid, rs in by_source.items()}
    test_src = {sid for sid, p in pref.items() if p == "test"}
    val_src = {sid for sid, p in pref.items() if p == "validation"}
    train_src = {sid for sid, p in pref.items() if p not in ("test", "validation")}

    def count(srcs):
        return sum(len(by_source[s]) for s in srcs)

    target = max(8, int(math.ceil(0.10 * total)))
    moved_test, moved_val = [], []

    def room(target_rows, current):
        return (current < target_rows
                and count(train_src) >= int(math.ceil(0.60 * total)))

    # enlarge from domain-train sources that the Task 60 evaluation never used,
    # smallest sources first so training keeps the bulk of the material
    eligible = sorted((s for s in train_src if s not in eval_sources),
                      key=lambda s: (len(by_source[s]), s))
    for sid in list(eligible):
        if not room(target, count(test_src)):
            break
        train_src.discard(sid)
        test_src.add(sid)
        moved_test.append({"source_id": sid, "rows": len(by_source[sid])})
    for sid in list(eligible):
        if sid in test_src or not room(target, count(val_src)):
            break
        train_src.discard(sid)
        val_src.add(sid)
        moved_val.append({"source_id": sid, "rows": len(by_source[sid])})

    split_of = {}
    for s in test_src:
        split_of[s] = "test"
    for s in val_src:
        split_of[s] = "validation"
    for s in train_src:
        split_of[s] = "train"

    def as_domain_split(p):
        if p == "test":
            return "test"
        if p == "validation":
            return "validation"
        return "train"

    for r in gold_rows:
        r["split_origin"] = ("domain_split"
                             if split_of[r["source_id"]] == as_domain_split(pref[r["source_id"]])
                             else "enlarged_from_domain_train")
        r["split"] = split_of[r["source_id"]]

    return {
        "targets": {"test": target, "validation": target},
        "enlarged_test": moved_test,
        "enlarged_validation": moved_val,
        "source_split": {s: split_of[s] for s in sorted(split_of)},
        "domain_pref_counts": dict(Counter(pref.values())),
    }


# --------------------------------------------------------------------------
# 4. validation
# --------------------------------------------------------------------------
def validate(gold_rows, reviews, prior_basis, eval_sources):
    import jsonschema
    schema = json.load(open(SCHEMA, encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)
    errors, warnings = [], []
    checks = OrderedDict()

    def check(name, ok, detail=""):
        checks[name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            errors.append("%s: %s" % (name, detail))

    # schema
    bad = [(r["example_id"], "; ".join(e.message[:90] for e in validator.iter_errors(r)))
           for r in gold_rows if not validator.is_valid(r)]
    check("schema_valid", not bad, "%d invalid: %s" % (len(bad), bad[:3]))

    # human verified
    not_ver = [r["example_id"] for r in gold_rows
               if r.get("HUMAN_VERIFIED") is not True
               or r.get("human_review_status") != "HUMAN_VERIFIED"]
    check("all_human_verified", not not_ver, "%d rows: %s" % (len(not_ver), not_ver[:3]))

    # every row has an approval basis
    no_basis = [r["example_id"] for r in gold_rows
                if r.get("gold_source") not in ("task62_review", "prior_verified")]
    check("every_row_has_approval_basis", not no_basis, str(no_basis[:5]))

    approved = {eid for eid, rec in reviews.items() if rec.get("decision") == "APPROVE"}
    bad_basis = []
    for r in gold_rows:
        if r["gold_source"] == "task62_review" and r["example_id"] not in approved:
            bad_basis.append(r["example_id"])
        if r["gold_source"] == "prior_verified":
            rev = r.get("review", {})
            stands = (rev.get("basis") == "prior_history_still_stand"
                      and rev.get("final_prior_decision") == "APPROVE")
            readjudicated = (rev.get("basis") == "queue_R_re_adjudicated"
                             and rev.get("decision") == "APPROVE")
            if not (stands or readjudicated):
                bad_basis.append(r["example_id"])
    check("no_rejected_or_revise_only_rows", not bad_basis, str(bad_basis[:5]))

    # provenance
    no_prov = [r["example_id"] for r in gold_rows
               if not r.get("provenance") or not r["provenance"].get("source_id")]
    check("provenance_present", not no_prov, str(no_prov[:5]))

    # rights
    bad_rights = [(r["example_id"], r.get("rights_status")) for r in gold_rows
                  if r.get("rights_status") not in RIGHTS_OK]
    check("rights_pass", not bad_rights, str(bad_rights[:5]))

    # uniqueness
    ids = Counter(r["example_id"] for r in gold_rows)
    dups = [k for k, v in ids.items() if v > 1]
    check("unique_example_ids", not dups, str(dups[:5]))

    qs = Counter(norm_question(r["question"]) for r in gold_rows)
    dupq = [k[:70] for k, v in qs.items() if v > 1]
    check("unique_questions", not dupq, str(dupq[:5]))

    # split integrity
    id_split = defaultdict(set)
    src_split = defaultdict(set)
    for r in gold_rows:
        id_split[r["example_id"]].add(r["split"])
        src_split[r["source_id"]].add(r["split"])
    leak_ex = [k for k, v in id_split.items() if len(v) > 1]
    leak_src = [k for k, v in src_split.items() if len(v) > 1]
    check("no_example_leakage", not leak_ex, str(leak_ex[:5]))
    check("no_source_leakage", not leak_src, str(leak_src[:5]))
    check("split_values_valid",
          all(r["split"] in ("train", "validation", "test") for r in gold_rows),
          str(Counter(r["split"] for r in gold_rows)))

    # near-duplicate questions must not straddle splits
    ns = [shingles(norm_question(r["question"])) for r in gold_rows]
    cross = []
    for i in range(len(gold_rows)):
        for j in range(i + 1, len(gold_rows)):
            if gold_rows[i]["split"] == gold_rows[j]["split"]:
                continue
            if jaccard(ns[i], ns[j]) >= NEAR_DUP_THRESHOLD:
                cross.append((gold_rows[i]["example_id"], gold_rows[j]["example_id"]))
    check("no_neardup_across_splits", not cross, str(cross[:5]))

    # messages shape
    bad_msg = [r["example_id"] for r in gold_rows
               if len(r.get("messages") or []) != 2
               or r["messages"][0].get("role") != "user"
               or r["messages"][1].get("role") != "assistant"
               or r["messages"][1].get("content") != r.get("answer")]
    check("messages_match_answer", not bad_msg, str(bad_msg[:5]))

    # answers free of raw ids / urls (warning only: prior human-approved rows stand)
    for r in gold_rows:
        a = r.get("answer", "")
        if re.search(r"SVK-\d{4}", a) or "http://" in a or "https://" in a:
            warnings.append("%s: answer contains a raw id or URL" % r["example_id"])

    # DAPT-01 evaluation source overlap (known limitation, not an error)
    overlap = Counter()
    for r in gold_rows:
        if r["source_id"] in eval_sources:
            overlap[r["split"]] += 1
    checks["dapt01_eval_source_overlap"] = {
        "pass": True,
        "detail": {k: v for k, v in sorted(overlap.items())},
    }
    return checks, errors, warnings


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main():
    queue = load_jsonl(QUEUE)
    pool = {r["example_id"]: r for r in load_jsonl(POOL)}
    prior_rows = load_jsonl(RECON)
    reviews = load_reviews()
    seq = prior_final_decisions()

    eval_sources = set()
    for case in load_jsonl(EVAL_CASES):
        eval_sources |= set(re.findall(r"SVK-\d{3,4}", json.dumps(case)))
    print("pool=%d queue=%d prior=%d reviews=%d eval_sources=%d"
          % (len(pool), len(queue), len(prior_rows), len(reviews), len(eval_sources)))

    excluded, pending, approved_rows = [], [], []
    for qr in queue:
        eid = qr["example_id"]
        rec = reviews.get(eid)
        if rec is None:
            pending.append({"example_id": eid, "queue": qr["queue"],
                            "question": qr["question"]})
            continue
        dec = rec.get("decision")
        if dec == "APPROVE":
            src = pool.get(eid)
            if src is None:
                excluded.append({"example_id": eid, "decision": dec,
                                 "reason": "candidate row missing from pool"})
                continue
            approved_rows.append(gold_row_from_candidate(src, rec, rec.get("reviewer")))
        else:
            excluded.append({"example_id": eid, "decision": dec,
                             "queue": qr["queue"], "question": qr["question"],
                             "feedback": rec.get("feedback", ""),
                             "rubric_fail": sorted(k for k, v in
                                                   (rec.get("review_rubric") or {}).items()
                                                   if v == "FAIL")})

    # ---- prior HUMAN_VERIFIED rows -------------------------------------
    taken = set(pool) | {r["example_id"] for r in approved_rows}
    prior_in, prior_out = [], []
    for p in prior_rows:
        ref = p.get("review_ref") or p["example_id"]
        final = prior_final_decision(ref, seq)
        t62 = reviews.get(p["example_id"])
        if t62 is not None:
            basis = "queue_R_re_adjudicated"
            decision = t62.get("decision")
        else:
            basis = "prior_history_still_stand"
            decision = final
        ok_history = decision == "APPROVE"
        ok_rights = p.get("rights_status") in RIGHTS_OK
        if not ok_history or not ok_rights:
            prior_out.append({
                "example_id": p["example_id"], "review_ref": ref,
                "final_prior_decision": final,
                "task62_decision": t62.get("decision") if t62 else None,
                "rights_status": p.get("rights_status"),
                "included": False,
                "reason": ("rights not cleared: %s" % p.get("rights_status"))
                          if not ok_rights else
                          ("decision history does not stand: final=%s" % (final or "none")),
            })
            continue
        basis_rec = OrderedDict([
            ("review_id", t62.get("review_id") if t62 else None),
            ("decision", "APPROVE"),
            ("reviewer", t62.get("reviewer") if t62 else "HUMAN_REVIEWER (prior task)"),
            ("review_timestamp", t62.get("review_timestamp") if t62 else None),
            ("feedback", t62.get("feedback", "") if t62 else ""),
            ("answer_edited", bool(t62.get("answer_edited")) if t62 else False),
            ("queue", t62.get("queue", "") if t62 else ""),
            ("basis", basis),
            ("final_prior_decision", final),
            ("prior_decisions", [d for _, _, d in seq.get(ref, [])]),
        ])
        if t62 is not None and t62.get("decision") == "APPROVE":
            if t62.get("answer_edited") and t62.get("reviewed_answer"):
                p = json.loads(json.dumps(p))
                p["answer"] = t62["reviewed_answer"]
                p["messages"] = [{"role": "user", "content": p["question"]},
                                 {"role": "assistant", "content": p["answer"]}]
            row = normalize_prior_row(p, taken, basis_rec)
            row["review"]["queue"] = t62.get("queue", "")
            row["review"]["reviewer"] = t62.get("reviewer")
            prior_in.append(row)
        else:
            prior_in.append(normalize_prior_row(p, taken, basis_rec))
        taken.add(prior_in[-1]["example_id"])

    # ---- merge, dedupe -------------------------------------------------
    gold = approved_rows + prior_in
    seen_q, dup_removed = {}, []
    deduped = []
    for r in gold:
        key = norm_question(r["question"])
        if key in seen_q:
            dup_removed.append({"example_id": r["example_id"],
                                "duplicate_of": seen_q[key]})
            continue
        seen_q[key] = r["example_id"]
        deduped.append(r)
    gold = deduped

    split_info = assign_splits(gold, eval_sources)

    # ---- validate + write ---------------------------------------------
    checks, errors, warnings = validate(gold, reviews,
                                        {r["example_id"]: r["review"] for r in prior_in},
                                        eval_sources)

    os.makedirs(OUT_DIR, exist_ok=True)
    write_jsonl(GOLD, gold)
    for s, path in SPLITS.items():
        write_jsonl(path, [r for r in gold if r["split"] == s])

    # near-duplicate census over the final gold set
    ns = [shingles(norm_question(r["question"])) for r in gold]
    pairs = []
    for i in range(len(gold)):
        for j in range(i + 1, len(gold)):
            v = jaccard(ns[i], ns[j])
            if v >= NEAR_DUP_THRESHOLD:
                pairs.append({"similarity": round(v, 3),
                              "same_source": gold[i]["source_id"] == gold[j]["source_id"],
                              "a": gold[i]["example_id"], "b": gold[j]["example_id"],
                              "split": gold[i]["split"]})

    decisions = Counter(rec.get("decision") for rec in reviews.values())
    stats = OrderedDict([
        ("task", 62),
        ("generated_at", __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat()),
        ("queue_rows", len(queue)),
        ("reviewed", len(reviews)),
        ("pending", len(pending)),
        ("decisions", dict(decisions)),
        ("queue_decisions", {q: dict(Counter(
            reviews[r["example_id"]].get("decision")
            for r in queue if r["queue"] == q and r["example_id"] in reviews))
            for q in sorted({r["queue"] for r in queue})}),
        ("queue_sizes", dict(Counter(r["queue"] for r in queue))),
        ("approved_from_pool", len(approved_rows)),
        ("prior_verified_included", len(prior_in)),
        ("prior_verified_excluded", prior_out),
        ("duplicates_removed", dup_removed),
        ("excluded", excluded),
        ("pending_rows", pending),
        ("gold_total", len(gold)),
        ("gold_by_split", dict(Counter(r["split"] for r in gold))),
        ("gold_by_source_split", split_info["source_split"]),
        ("split_info", split_info),
        ("gold_by_category", dict(sorted(Counter(r.get("category", "") for r in gold).items()))),
        ("gold_by_language", dict(sorted(Counter(str(r.get("language", "")) for r in gold).items()))),
        ("gold_by_task_category", dict(sorted(Counter(r.get("task_category", "") for r in gold).items()))),
        ("gold_by_rights", dict(sorted(Counter(r.get("rights_status", "") for r in gold).items()))),
        ("gold_by_origin_method", dict(sorted(Counter(
            (r.get("origin") or {}).get("method", "") for r in gold).items()))),
        ("gold_sources", len({r["source_id"] for r in gold})),
        ("gold_source_list", sorted({r["source_id"] for r in gold})),
        ("eval_source_overlap", dict(sorted(Counter(
            r["split"] for r in gold if r["source_id"] in eval_sources).items()))),
        ("eval_source_overlap_total", sum(1 for r in gold
                                          if r["source_id"] in eval_sources)),
        ("answer_edited_count", sum(1 for r in gold
                                    if r.get("review", {}).get("answer_edited"))),
        ("near_dup_pairs", len(pairs)),
        ("near_dup_cross_source", sum(1 for p in pairs if not p["same_source"])),
        ("near_dup_pairs_detail", sorted(pairs, key=lambda p: -p["similarity"])[:40]),
        ("validation_checks", checks),
        ("validation_errors", errors),
        ("validation_warnings", sorted(set(warnings))),
        ("eval_sources", sorted(eval_sources)),
    ])
    with open(STATS, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, ensure_ascii=False, indent=2)

    print("\ndecisions: %s  pending=%d" % (dict(decisions), len(pending)))
    print("gold rows: %d  splits=%s  sources=%d"
          % (len(gold), stats["gold_by_split"], stats["gold_sources"]))
    print("prior verified: in=%d out=%d" % (len(prior_in), len(prior_out)))
    for p in prior_out:
        print("   excluded %s -> %s" % (p["example_id"], p["reason"]))
    print("near-dup pairs: %d (cross-source %d)"
          % (len(pairs), stats["near_dup_cross_source"]))
    print("\nvalidation: %d checks, %d errors, %d warnings"
          % (len(checks), len(errors), len(set(warnings))))
    for name, res in checks.items():
        print("  [%s] %s %s" % ("PASS" if res["pass"] else "FAIL", name,
                                str(res["detail"])[:110]))
    for e in errors:
        print("  ERROR:", e)
    print("\nwrote %s (+ train/validation/test)" % os.path.relpath(GOLD, ROOT))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
