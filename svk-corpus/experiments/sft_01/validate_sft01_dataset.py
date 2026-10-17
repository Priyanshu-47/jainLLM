#!/usr/bin/env python3
"""TASK 64 validation: independent checks over the SFT-01 train/eval dataset.

Run:
    python3 experiments/sft_01/validate_sft01_dataset.py

Every check is read-only. Exits non-zero when any check fails.

Checks (>= 14):
     1 schema validity of every output row (sft_schema_v1)
     2 example_id uniqueness across train+eval
     3 no exact duplicate questions/answers
     4 no near-duplicate questions (shingle Jaccard >= 0.80)
     5 provenance complete and every source present in source_manifest.csv
     6 rights: allowed statuses only and rights_for() recomputes as allowed
     7 source-level split separation (no shared source / id / question / answer)
     8 deterministic split: re-running assign_split reproduces the partition
     9 no Task 63 REJECT/REVISE record in either output
    10 messages structure matches question/answer exactly
    11 answer quality: >= 12 words, terminal punctuation, no raw URL/SVK/unit ids
    12 grounding re-verified against evidence / corpus units
    13 sect / knowledge_layer / tradition / religious_scope vs manifest
    14 HUMAN_VERIFIED integrity: 8 in, 5 selected, 3 Task-63-REJECT excluded,
        0 newly created, no row upgraded to HUMAN_VERIFIED
    15 frozen 47-case eval file untouched (sha256)
    16 stats JSON agrees with the files it describes (counts + file hashes)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
SFT01_DIR = os.path.join(ROOT, "experiments", "sft_01")
TASK61_DIR = os.path.join(ROOT, "experiments", "sft_curation", "task61")
for _p in (SFT01_DIR, TASK61_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import build_sft01_dataset as b  # noqa: E402
from task61_common import load_rights_audit, load_jainqq_evidence, load_manifest, rights_for  # noqa: E402

SCHEMA_PATH = b.SCHEMA_PATH
TRAIN_PATH = b.OUT_TRAIN
EVAL_PATH = b.OUT_EVAL
STATS_PATH = b.OUT_STATS
FROZEN_EVAL_PATH = b.FROZEN_EVAL_PATH
ALLOWED_RIGHTS = b.ALLOWED_RIGHTS


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_outputs():
    train = b.read_jsonl(TRAIN_PATH)
    eval_rows = b.read_jsonl(EVAL_PATH)
    return train, eval_rows


def load_stats():
    with open(STATS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------
def check_schema(train, eval_rows):
    import jsonschema
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        schema = json.load(fh)
    v = jsonschema.Draft7Validator(schema)
    bad = []
    for row in train + eval_rows:
        errs = [f"{e.json_path}:{e.message[:80]}" for e in v.iter_errors(row)]
        if errs:
            bad.append(f"{row.get('example_id')} {errs[:2]}")
    return not bad, bad


def check_example_ids_unique(train, eval_rows):
    ids = [r["example_id"] for r in train + eval_rows]
    dup = [k for k, c in Counter(ids).items() if c > 1]
    return not dup, dup


def check_no_exact_duplicates(train, eval_rows):
    seen_q, seen_a, bad = {}, {}, []
    for r in train + eval_rows:
        q, a = b.fold(r["question"]), b.fold(r["answer"])
        if q in seen_q:
            bad.append(f"question dup: {r['example_id']} ~ {seen_q[q]}")
        if a in seen_a:
            bad.append(f"answer dup: {r['example_id']} ~ {seen_a[a]}")
        seen_q.setdefault(q, r["example_id"])
        seen_a.setdefault(a, r["example_id"])
    return not bad, bad


def check_no_near_duplicates(train, eval_rows):
    rows = train + eval_rows
    sh = {r["example_id"]: b.shingles(r["question"]) for r in rows}
    ids = [r["example_id"] for r in rows]
    bad = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            v = b.jaccard(sh[ids[i]], sh[ids[j]])
            if v >= b.NEAR_DUP_THRESHOLD:
                bad.append(f"{ids[i]} ~ {ids[j]} ({v:.3f})")
    return not bad, bad


def check_provenance_and_manifest(train, eval_rows):
    manifest = load_manifest()
    bad = []
    for r in train + eval_rows:
        prov = r.get("provenance") or {}
        sid = str(prov.get("source_id") or "")
        if not b.SOURCE_ID_RE.match(sid):
            bad.append(f"{r['example_id']}: bad source_id {sid!r}")
        if sid and sid not in manifest:
            bad.append(f"{r['example_id']}: source {sid} not in manifest")
        if not prov.get("text_id"):
            bad.append(f"{r['example_id']}: missing text_id")
        if not (prov.get("religious_scope") or r.get("religious_scope")):
            bad.append(f"{r['example_id']}: missing religious_scope")
    return not bad, bad


def check_rights(train, eval_rows):
    manifest = load_manifest()
    audit = load_rights_audit()
    jainqq = load_jainqq_evidence()
    bad = []
    for r in train + eval_rows:
        claimed = str(r.get("rights_status") or "")
        if claimed not in ALLOWED_RIGHTS:
            bad.append(f"{r['example_id']}: rights_status={claimed}")
            continue
        sid = str((r.get("provenance") or {}).get("source_id") or r.get("source_id") or "")
        rec = rights_for(sid, manifest, audit, jainqq)
        if not rec.get("allowed"):
            bad.append(f"{r['example_id']}: recomputed disallowed ({rec.get('rights_status')})")
    return not bad, bad


def check_split_separation(train, eval_rows):
    bad = []
    tr_src = {r["source_id"] for r in train}
    ev_src = {r["source_id"] for r in eval_rows}
    shared = sorted(tr_src & ev_src)
    if shared:
        bad.append(f"shared sources: {shared}")
    tr_q = {b.fold(r["question"]) for r in train}
    ev_q = {b.fold(r["question"]) for r in eval_rows}
    if tr_q & ev_q:
        bad.append(f"shared questions: {sorted(tr_q & ev_q)[:3]}")
    tr_a = {b.fold(r["answer"]) for r in train}
    ev_a = {b.fold(r["answer"]) for r in eval_rows}
    if tr_a & ev_a:
        bad.append("shared answers between splits")
    for r in train:
        if r.get("split") != "train":
            bad.append(f"{r['example_id']}: split={r.get('split')!r} in train file")
    for r in eval_rows:
        if r.get("split") != "validation":
            bad.append(f"{r['example_id']}: split={r.get('split')!r} in eval file")
    return not bad, bad


def check_deterministic_split(train, eval_rows):
    rows = train + eval_rows
    t2, e2, _ = b.assign_split(rows)
    got_t = sorted(r["example_id"] for r in train)
    got_e = sorted(r["example_id"] for r in eval_rows)
    exp_t = sorted(r["example_id"] for r in t2)
    exp_e = sorted(r["example_id"] for r in e2)
    bad = []
    if got_t != exp_t:
        bad.append("train partition not reproducible by assign_split")
    if got_e != exp_e:
        bad.append("eval partition not reproducible by assign_split")
    if {r["source_id"] for r in train} & {r["source_id"] for r in eval_rows}:
        bad.append("source leakage")
    return not bad, bad


def check_no_task63_reject_revise(train, eval_rows):
    decisions = b.load_task63_decisions()
    rows = train + eval_rows
    ids = {r["example_id"] for r in rows}
    ids |= {r["sft01"].get("original_id") for r in rows if r["sft01"].get("original_id")}
    bad = sorted(ids & set(decisions))
    return not bad, [f"adjudicated record present: {i} ({decisions[i]['decision']})"
                     for i in bad]


def check_messages(train, eval_rows):
    bad = []
    for r in train + eval_rows:
        msgs = r.get("messages") or []
        if len(msgs) != 2:
            bad.append(f"{r['example_id']}: {len(msgs)} messages")
            continue
        if msgs[0].get("role") != "user" or msgs[1].get("role") != "assistant":
            bad.append(f"{r['example_id']}: bad roles {msgs[0].get('role')}/{msgs[1].get('role')}")
        if msgs[0].get("content") != r["question"]:
            bad.append(f"{r['example_id']}: user content != question")
        if msgs[1].get("content") != r["answer"]:
            bad.append(f"{r['example_id']}: assistant content != answer")
        if not str(msgs[0].get("content") or "").strip():
            bad.append(f"{r['example_id']}: empty question")
        if not str(msgs[1].get("content") or "").strip():
            bad.append(f"{r['example_id']}: empty answer")
    return not bad, bad


def check_answer_quality(train, eval_rows):
    bad = []
    for r in train + eval_rows:
        issues = b.answer_issues(r)
        if issues:
            bad.append(f"{r['example_id']}: {issues}")
    return not bad, bad


def check_grounding(train, eval_rows):
    manifest = b.load_source_manifest_raw()
    unit_cache = {}
    bad = []
    for r in train + eval_rows:
        sid = str((r.get("provenance") or {}).get("source_id") or "")
        ok, method, detail = b.grounding_check(r, manifest.get(sid), unit_cache)
        if not ok:
            bad.append(f"{r['example_id']}: {method} {detail}")
        extra = ""
        if r["sft01"]["input"] == "human_verified":
            key = (r["example_id"], tuple(b.linked_unit_ids(r)))
            extra = " ".join(unit_cache.get(key, {}).values())
        ok, detail = b.attribution_check(r, manifest.get(sid), extra)
        if not ok:
            bad.append(f"{r['example_id']}: attribution {detail}")
    return not bad, bad


def check_metadata_consistency(train, eval_rows):
    manifest = b.load_source_manifest_raw()
    bad = []
    for r in train + eval_rows:
        sid = str((r.get("provenance") or {}).get("source_id") or "")
        issues = b.consistency_issues(r, manifest.get(sid))
        if issues:
            bad.append(f"{r['example_id']}: {issues}")
    return not bad, bad


def check_human_verified_integrity(train, eval_rows, stats):
    hv = stats.get("human_verified", {})
    bad = []
    if hv.get("input") != 8:
        bad.append(f"human input {hv.get('input')} != 8")
    if hv.get("selected") != 5:
        bad.append(f"human selected {hv.get('selected')} != 5")
    if hv.get("excluded") != 3:
        bad.append(f"human excluded {hv.get('excluded')} != 3")
    if hv.get("newly_created") != 0:
        bad.append("newly_created != 0")
    expected_excluded = {
        "SFT-SEED-CAND-SVK-0038-unknown",
        "SFT-SEED-CAND-SVK-2025-SVK-2025",
        "SFT-SEED-CAND-SVK-2029-SVK-2029",
    }
    if set(hv.get("excluded_ids") or []) != expected_excluded:
        bad.append(f"excluded_ids mismatch: {hv.get('excluded_ids')}")
    decisions = b.load_task63_decisions()
    if not expected_excluded <= set(decisions):
        bad.append("excluded ids are not the Task-63 REJECT set")
    rows = train + eval_rows
    out_human = [r for r in rows if r["sft01"]["input"] == "human_verified"]
    if len(out_human) != 5:
        bad.append(f"outputs contain {len(out_human)} human rows != 5")
    upgraded = [r["example_id"] for r in rows
                if r["sft01"]["input"] == "task63_approve"
                and (r.get("human_review_status") == "HUMAN_VERIFIED"
                     or r.get("HUMAN_VERIFIED") is True)]
    if upgraded:
        bad.append(f"status upgraded to HUMAN_VERIFIED: {upgraded[:3]}")
    for r in out_human:
        if r.get("human_review_status") != "HUMAN_VERIFIED":
            bad.append(f"{r['example_id']}: pre-existing status not preserved")
    return not bad, bad


def check_frozen_eval_untouched(train, eval_rows):
    digest = sha256_file(FROZEN_EVAL_PATH)
    ok = digest == b.FROZEN_EVAL_SHA256
    return ok, [] if ok else [f"sha256 {digest} != {b.FROZEN_EVAL_SHA256}"]


def check_stats_consistency(train, eval_rows, stats):
    bad = []
    if stats.get("selected_total") != len(train) + len(eval_rows):
        bad.append("selected_total != train+eval rows")
    if stats.get("splits", {}).get("train") != len(train):
        bad.append("stats train count mismatch")
    if stats.get("splits", {}).get("eval") != len(eval_rows):
        bad.append("stats eval count mismatch")
    out = stats.get("outputs", {})
    if out.get("train_sha256") != sha256_file(TRAIN_PATH):
        bad.append("train file sha256 != stats")
    if out.get("eval_sha256") != sha256_file(EVAL_PATH):
        bad.append("eval file sha256 != stats")
    if out.get("train_rows") != len(train) or out.get("eval_rows") != len(eval_rows):
        bad.append("stats output row counts mismatch")
    if stats.get("inputs", {}).get("total") != 62:
        bad.append("inputs total != 62")
    if stats.get("exclusions") != {"TASK63_REJECT": 3}:
        bad.append(f"unexpected exclusions: {stats.get('exclusions')}")
    if stats.get("schema", {}).get("valid") is not True:
        bad.append("stats schema.valid is not true")
    leak = stats.get("leakage_checks") or {}
    for k, v in leak.items():
        if v:
            bad.append(f"leakage in stats: {k}={v}")
    if not stats.get("frozen_eval", {}).get("sha256_matches_expected"):
        bad.append("stats frozen_eval hash mismatch")
    return not bad, bad


CHECKS = [
    ("schema validity", check_schema),
    ("example_id uniqueness", check_example_ids_unique),
    ("no exact duplicate questions/answers", check_no_exact_duplicates),
    ("no near-duplicate questions", check_no_near_duplicates),
    ("provenance + source manifest", check_provenance_and_manifest),
    ("rights (recorded + recomputed)", check_rights),
    ("source-level split separation", check_split_separation),
    ("deterministic split reproducibility", check_deterministic_split),
    ("no Task-63 REJECT/REVISE record", check_no_task63_reject_revise),
    ("messages match question/answer", check_messages),
    ("answer quality + no raw ids/urls", check_answer_quality),
    ("metadata consistency vs manifest", check_metadata_consistency),
    ("HUMAN_VERIFIED integrity", None),          # special: needs stats
    ("frozen 47-case eval untouched", None),     # special: no row args
    ("stats JSON consistency", None),            # special: needs stats
    ("grounding + attribution re-verified", check_grounding),
]


def main(argv=None):
    train, eval_rows = load_outputs()
    stats = load_stats()
    failures = 0
    for name, fn in CHECKS:
        if name == "HUMAN_VERIFIED integrity":
            ok, bad = check_human_verified_integrity(train, eval_rows, stats)
        elif name == "frozen 47-case eval untouched":
            ok, bad = check_frozen_eval_untouched(train, eval_rows)
        elif name == "stats JSON consistency":
            ok, bad = check_stats_consistency(train, eval_rows, stats)
        else:
            ok, bad = fn(train, eval_rows)
        status = "PASS" if ok else "FAIL"
        failures += 0 if ok else 1
        print(f"  [{status}] {name}" + ("" if ok else f" -> {bad[:3]}"))
    print(f"TASK 64 validation: {len(CHECKS) - failures}/{len(CHECKS)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
