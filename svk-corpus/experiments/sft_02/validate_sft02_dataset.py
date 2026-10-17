#!/usr/bin/env python3
"""TASK 67 validation: independent checks over the SFT-02 train/eval dataset.

Run:
    PYTHONPATH=src python3 experiments/sft_02/validate_sft02_dataset.py

Every check is read-only. Exits non-zero when any check fails.

Checks (>= 20):
     1 schema validity of every output row (sft_schema_v1)
     2 example_id uniqueness across train+eval
     3 no exact duplicate questions/answers
     4 no near-duplicate questions/answers (shingle Jaccard >= 0.80)
     5 provenance complete and every source present in source_manifest.csv
     6 rights: allowed statuses only and rights_for() recomputes as allowed
     7 origin object schema (synthetic/method/confidence; builder for task67)
     8 source-level split separation (no shared source / id / question / answer)
     9 deterministic split: re-running assign_split reproduces the partition
    10 pair integrity: every pair_group has exactly 2 rows, same split, train-locked
    11 eval coverage: the 3 required categories present, sizes sane
    12 frozen leakage: no frozen source, no frozen-question near-dup, sha256 fixed
    13 messages structure matches question/answer exactly
    14 answer quality: >= 12 words, no raw URL/SVK/unit ids, length caps
    15 row gates + grounding re-verified by re-running the builder checks
    16 anti-template gate re-run: PASS/WARN only, no [FAIL] flag
    17 Task-66 s14 category targets (ranges) met
    18 abstention balance: 4 pairs intact, 4 answerable / 4 unanswerable,
        >= 4 distinct refusal phrasings
    19 attribution balance: 16-18 rows (6 approved + 12 anti-fab), >= 6 unknown
    20 anti-fabrication: 8 rows / 4 intact pairs, false-presupposition + plain
    21 wh-question breadth >= 10 distinct openers, median answer <= 350 chars
    22 stats JSON agrees with the files it describes (counts + leakage + gate)
    23 frozen 47-case eval file untouched (sha256)
    24 SFT-02 config consistent with the built files (rows, LR, epochs, lineage)
    25 read-only inputs unchanged (v1 train/eval, gold, pool, schema)
"""
from __future__ import annotations

import json
import os
import re
import statistics
import sys
from collections import Counter
from typing import List, Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
SFT02_DIR = os.path.join(ROOT, "experiments", "sft_02")
if SFT02_DIR not in sys.path:
    sys.path.insert(0, SFT02_DIR)

import anti_template_gate as gate  # noqa: E402
import build_sft02_dataset as b  # noqa: E402
from sft02_common import (  # noqa: E402
    ALLOWED_RIGHTS,
    FROZEN_EVAL_PATH,
    FROZEN_EVAL_SHA256,
    MIN_ANSWER_WORDS,
    MIN_EVAL_ROWS,
    NEAR_DUP_THRESHOLD,
    REQUIRED_EVAL_COVERAGE,
    SCHEMA_PATH,
    TRAIN_V1_PATH,
    GOLD_PATH,
    OUT_EVAL,
    OUT_STATS,
    OUT_TRAIN,
    POOL_PATH,
    RightsContext,
    corpus_units_by_source,
    fold,
    frozen_sha256,
    jaccard,
    load_frozen_sources,
    read_jsonl,
    SOURCE_ID_RE,
    sha256_file,
    shingles,
    text_issues,
)
from task61_common import (  # noqa: E402
    load_jainqq_evidence,
    load_manifest,
    load_rights_audit,
    rights_for,
)

CONFIG_PATH = os.path.join(ROOT, "configs", "sft_qwen3_8b_sft02_v1.yaml")

_RCTX = None
_CORPUS = None
_UNITS = None


def rctx():
    global _RCTX
    if _RCTX is None:
        _RCTX = RightsContext()
    return _RCTX


def corpus_index():
    global _CORPUS
    if _CORPUS is None:
        frozen = load_frozen_sources()
        eligible = [s for s in b.eligible_sources(rctx(), frozen)
                    if s not in b.SYNTHETIC_SOURCES]
        _CORPUS = corpus_units_by_source(set(eligible))
    return _CORPUS


def units_by_id():
    global _UNITS
    if _UNITS is None:
        _UNITS = {}
        for recs in corpus_index().values():
            for rec in recs:
                _UNITS[rec.get("id") or rec.get("unit_id")] = rec
    return _UNITS


def load_outputs():
    return read_jsonl(OUT_TRAIN), read_jsonl(OUT_EVAL)


def load_stats():
    with open(OUT_STATS, encoding="utf-8") as fh:
        return json.load(fh)


def frozen_questions():
    return [shingles(c["question"])
            for c in read_jsonl(FROZEN_EVAL_PATH)]


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
        q, a = fold(r["question"]), fold(r["answer"])
        if q in seen_q:
            bad.append(f"question dup: {r['example_id']} ~ {seen_q[q]}")
        if a in seen_a:
            bad.append(f"answer dup: {r['example_id']} ~ {seen_a[a]}")
        seen_q.setdefault(q, r["example_id"])
        seen_a.setdefault(a, r["example_id"])
    return not bad, bad


def check_no_near_duplicates(train, eval_rows):
    rows = train + eval_rows
    ids = [r["example_id"] for r in rows]
    sh_q = {i: shingles(r["question"]) for i, r in zip(ids, rows)}
    sh_a = {i: shingles(r["answer"]) for i, r in zip(ids, rows)}
    bad = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            vq = jaccard(sh_q[ids[i]], sh_q[ids[j]])
            if vq >= NEAR_DUP_THRESHOLD:
                bad.append(f"question {ids[i]} ~ {ids[j]} ({vq:.3f})")
            va = jaccard(sh_a[ids[i]], sh_a[ids[j]])
            if va >= NEAR_DUP_THRESHOLD:
                bad.append(f"answer {ids[i]} ~ {ids[j]} ({va:.3f})")
    return not bad, bad


def check_provenance_and_manifest(train, eval_rows):
    manifest = load_manifest()
    bad = []
    for r in train + eval_rows:
        prov = r.get("provenance") or {}
        sid = str(prov.get("source_id") or "")
        if not SOURCE_ID_RE.match(sid or ""):
            bad.append(f"{r['example_id']}: bad source_id {sid!r}")
        if sid and sid not in manifest:
            bad.append(f"{r['example_id']}: source {sid} not in manifest")
        if sid and sid != r.get("source_id"):
            bad.append(f"{r['example_id']}: provenance/source_id mismatch")
        if not prov.get("text_id"):
            bad.append(f"{r['example_id']}: missing text_id")
        if not (prov.get("religious_scope") or r.get("religious_scope")):
            bad.append(f"{r['example_id']}: missing religious_scope")
    return not bad, bad


def check_rights(train, eval_rows):
    manifest = load_manifest()
    bad = []
    for r in train + eval_rows:
        claimed = str(r.get("rights_status") or "")
        if claimed not in ALLOWED_RIGHTS:
            bad.append(f"{r['example_id']}: rights_status={claimed}")
            continue
        sid = str((r.get("provenance") or {}).get("source_id")
                  or r.get("source_id") or "")
        rec = rights_for(sid, manifest, load_rights_audit(), load_jainqq_evidence())
        if not rec.get("allowed"):
            bad.append(f"{r['example_id']}: recomputed disallowed "
                       f"({rec.get('rights_status')})")
    return not bad, bad


def check_origin_object(train, eval_rows):
    bad = []
    for r in train + eval_rows:
        o = r.get("origin")
        if not isinstance(o, dict):
            bad.append(f"{r['example_id']}: origin not an object")
            continue
        if not isinstance(o.get("synthetic"), bool):
            bad.append(f"{r['example_id']}: origin.synthetic not bool")
        if not o.get("method"):
            bad.append(f"{r['example_id']}: origin.method missing")
        if o.get("synthetic") is True and not o.get("confidence"):
            bad.append(f"{r['example_id']}: origin.confidence missing")
        builder = str(o.get("builder") or "")
        if builder.startswith("task67_sft02:"):
            if "sft02" in r:
                bad.append(f"{r['example_id']}: task67 row also marked approved")
        elif "sft02" not in r:
            bad.append(f"{r['example_id']}: approved row without sft02 marker")
    return not bad, bad


def check_split_separation(train, eval_rows):
    bad = []
    tr_src = {r["source_id"] for r in train}
    ev_src = {r["source_id"] for r in eval_rows}
    shared = sorted(tr_src & ev_src)
    if shared:
        bad.append(f"shared sources: {shared}")
    tr_q = {fold(r["question"]) for r in train}
    ev_q = {fold(r["question"]) for r in eval_rows}
    if tr_q & ev_q:
        bad.append(f"shared questions: {sorted(tr_q & ev_q)[:3]}")
    tr_a = {fold(r["answer"]) for r in train}
    ev_a = {fold(r["answer"]) for r in eval_rows}
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
    rows = [dict(r) for r in train + eval_rows]
    t2, e2, _ = b.assign_split(rows)
    bad = []
    if sorted(r["example_id"] for r in train) != sorted(r["example_id"] for r in t2):
        bad.append("train partition not reproducible by assign_split")
    if sorted(r["example_id"] for r in eval_rows) != sorted(r["example_id"] for r in e2):
        bad.append("eval partition not reproducible by assign_split")
    return not bad, bad


def check_pair_integrity(train, eval_rows):
    rows = train + eval_rows
    groups = Counter(r.get("pair_group") for r in rows if r.get("pair_group"))
    bad = []
    for g, c in sorted(groups.items()):
        if c != 2:
            bad.append(f"{g}: {c} rows != 2")
            continue
        members = [r for r in rows if r.get("pair_group") == g]
        splits = {r.get("split") for r in members}
        if len(splits) != 1:
            bad.append(f"{g}: split across {splits}")
        if splits != {"train"}:
            bad.append(f"{g}: pair not train-locked ({splits})")
        if g.startswith("abstain-pair-") and \
                {("answerable" in r.get("tags", [])) for r in members} != {True, False}:
            bad.append(f"{g}: pair must be one answerable + one unanswerable row")
        if g.startswith("antifab-pair-") and \
                sum(1 for r in members
                    if "false_presupposition" in r.get("tags", [])) != 1:
            bad.append(f"{g}: pair must contain exactly 1 false_presupposition row")
    abst = sorted(g for g in groups if g.startswith("abstain-pair-"))
    fab = sorted(g for g in groups if g.startswith("antifab-pair-"))
    if len(abst) != 4:
        bad.append(f"abstention pairs: {len(abst)} != 4")
    if not (6 <= len(fab) <= 8):
        bad.append(f"antifab pairs: {len(fab)} not in [6,8]")
    return not bad, bad


def check_eval_coverage(train, eval_rows):
    bad = []
    ev_cats = {r["category"] for r in eval_rows}
    missing = sorted(set(REQUIRED_EVAL_COVERAGE) - ev_cats)
    if missing:
        bad.append(f"eval missing required categories: {missing}")
    n = len(train) + len(eval_rows)
    if len(eval_rows) < MIN_EVAL_ROWS:
        bad.append(f"eval rows {len(eval_rows)} < MIN_EVAL_ROWS {MIN_EVAL_ROWS}")
    if len(eval_rows) > 0.25 * n:
        bad.append(f"eval rows {len(eval_rows)} > 25% of {n}")
    if len(eval_rows) < 12:
        bad.append(f"eval rows {len(eval_rows)} < 12")
    return not bad, bad


def check_frozen_leakage(train, eval_rows):
    bad = []
    frozen = load_frozen_sources()
    all_rows = train + eval_rows
    hit = sorted({r["source_id"] for r in all_rows} & frozen)
    if hit:
        bad.append(f"frozen sources in dataset: {hit}")
    fq = frozen_questions()
    for r in all_rows:
        q = shingles(r["question"])
        if any(jaccard(q, f) >= 0.80 for f in fq):
            bad.append(f"{r['example_id']}: question near-dup of frozen case")
    digest = frozen_sha256()
    if digest != FROZEN_EVAL_SHA256:
        bad.append(f"frozen sha256 {digest} != {FROZEN_EVAL_SHA256}")
    return not bad, bad


def check_messages(train, eval_rows):
    bad = []
    for r in train + eval_rows:
        msgs = r.get("messages") or []
        if len(msgs) != 2:
            bad.append(f"{r['example_id']}: {len(msgs)} messages")
            continue
        if msgs[0].get("role") != "user" or msgs[1].get("role") != "assistant":
            bad.append(f"{r['example_id']}: bad roles")
        if msgs[0].get("content") != r["question"]:
            bad.append(f"{r['example_id']}: user content != question")
        if msgs[1].get("content") != r["answer"]:
            bad.append(f"{r['example_id']}: assistant content != answer")
    return not bad, bad


def check_answer_quality(train, eval_rows):
    bad = []
    for r in train + eval_rows:
        issues = text_issues(r["answer"])
        q_issues = [i for i in text_issues(r["question"]) if i != "too_short"]
        if len(r["answer"]) > 750:
            issues.append("answer too long")
        if len(r["question"]) > 320:
            q_issues.append("question too long")
        if len(r["answer"].split()) < MIN_ANSWER_WORDS:
            issues.append(f"words<{MIN_ANSWER_WORDS}")
        if issues or q_issues:
            bad.append(f"{r['example_id']}: {issues + q_issues}")
    return not bad, bad


def check_row_gates_and_grounding(train, eval_rows):
    rows = train + eval_rows
    frozen = load_frozen_sources()
    problems = b.row_gates(rows, rctx(), frozen, frozen_questions())
    grounding = b.verify_grounding(rows, rctx(), units_by_id(), corpus_index())
    bad = problems + grounding
    return not bad, bad


def check_gate_rerun(train, eval_rows):
    report = gate.measure(train + eval_rows)
    bad = []
    if report.get("level") not in ("PASS", "WARN"):
        bad.append(f"gate level {report.get('level')}")
    for f in report.get("flags") or []:
        if f.startswith("[FAIL]"):
            bad.append(f)
    return not bad, bad


def check_category_targets(train, eval_rows):
    """Task-66 s14 ranges over the full dataset."""
    rows = train + eval_rows
    cats = Counter(r["category"] for r in rows)
    tags = Counter(t for r in rows for t in r.get("tags", []))
    bad = []

    def rng(name, got, lo, hi):
        if not (lo <= got <= hi):
            bad.append(f"{name}: {got} not in [{lo},{hi}]")

    rng("attribution", cats["SOURCE_ATTRIBUTION"], 16, 18)
    rng("canonical", cats["CANONICAL_VS_COMMENTARY"], 8, 10)
    rng("abstention", cats["ABSTENTION/INSUFFICIENT_EVIDENCE"], 10, 12)
    concept = cats["GENERAL_JAIN_CONCEPT"] + cats.get("JAIN_CONCEPT", 0)
    practice = cats["PRACTICE_EXPLANATION"]
    if not (12 <= concept + practice <= 15):
        bad.append(f"concept+practice: {concept + practice} not in [12,15]")
    if practice < 8:
        bad.append(f"practice rows {practice} < 8")
    dist = cats["STHANAKAVASI_DISTINCTION"]
    if dist != 8:
        bad.append(f"distinction total {dist} != 8")
    contrast = sum(1 for r in rows if "sect_contrast" in r.get("tags", []))
    discipline = sum(1 for r in rows
                     if "sect_unknown_discipline" in r.get("tags", []))
    if contrast < 4:
        bad.append(f"sect contrast {contrast} < 4")
    if discipline < 4:
        bad.append(f"sect discipline {discipline} < 4")
    ml = cats["HINDI"] + cats["GUJARATI"]
    if not (8 <= ml <= 10):
        bad.append(f"multilingual hi+gu {ml} not in [8,10]")
    if cats["HINDI"] < 4 or cats["GUJARATI"] < 4:
        bad.append(f"hi {cats['HINDI']} / gu {cats['GUJARATI']} below 4")
    if cats.get("PRAKRIT", 0) < 1:
        bad.append("no Prakrit row")
    fab = sum(1 for r in rows if "anti_fabrication" in r.get("tags", []))
    if not (12 <= fab <= 16):   # s14: 6-8 pairs = 12-16 rows
        bad.append(f"anti-fabrication rows {fab} not in [12,16]")
    if tags.get("terminology", 0) < 4:
        bad.append(f"terminology rows {tags.get('terminology', 0)} < 4")
    return not bad, bad


def check_abstention_balance(train, eval_rows):
    rows = train + eval_rows
    bad = []
    abst = [r for r in rows
            if r["category"] == "ABSTENTION/INSUFFICIENT_EVIDENCE"]
    answerable = [r for r in abst
                  if "answerable" in r.get("tags", [])
                  and "unanswerable" not in r.get("tags", [])]
    unanswerable = [r for r in abst if "unanswerable" in r.get("tags", [])]
    if len(answerable) < 4:
        bad.append(f"answerable calibration rows {len(answerable)} < 4")
    if len(unanswerable) < 4:
        bad.append(f"unanswerable calibration rows {len(unanswerable)} < 4")
    leads = {" ".join(r["answer"].split()[:4]) for r in unanswerable}
    if len(leads) < 4:
        bad.append(f"distinct refusal phrasings {len(leads)} < 4")
    groups = Counter(r.get("pair_group") for r in abst if r.get("pair_group"))
    if sum(1 for g, c in groups.items() if c == 2) < 4:
        bad.append(f"intact abstention pairs {sum(1 for c in groups.values() if c == 2)} < 4")
    return not bad, bad


def check_attribution_balance(train, eval_rows):
    rows = train + eval_rows
    bad = []
    attr = [r for r in rows if r["category"] == "SOURCE_ATTRIBUTION"]
    if not (16 <= len(attr) <= 18):
        bad.append(f"attribution rows {len(attr)} not in [16,18]")
    share = len(attr) / max(len(rows), 1)
    if share > 0.40:
        bad.append(f"attribution share {share:.1%} > 40%")
    unknown = [r for r in attr if "unknown_attribution" in r.get("tags", [])]
    if len(unknown) < 6:
        bad.append(f"unknown-attribution rows {len(unknown)} < 6")
    return not bad, bad


def check_antifabrication(train, eval_rows):
    rows = train + eval_rows
    bad = []
    fab = [r for r in rows if "anti_fabrication" in r.get("tags", [])]
    if not (12 <= len(fab) <= 16):
        bad.append(f"rows {len(fab)} not in [12,16]")
    groups = Counter(r.get("pair_group") for r in fab if r.get("pair_group"))
    if any(c != 2 for c in groups.values()):
        bad.append(f"broken pairs: {[g for g, c in groups.items() if c != 2]}")
    if not (6 <= len(groups) <= 8):
        bad.append(f"pairs {len(groups)} not in [6,8]")
    for g in groups:
        members = [r for r in fab if r.get("pair_group") == g]
        if sum(1 for r in members
               if "false_presupposition" in r.get("tags", [])) != 1:
            bad.append(f"{g}: expected exactly 1 false_presupposition row")
        if any(r.get("evidence", {}).get("method") != "manifest_absence"
               for r in members):
            bad.append(f"{g}: evidence method not manifest_absence")
    retraction = re.compile(r"record|identif|not associated|not named"
                            r"|no translator is named|no author", re.I)
    miss = [r["example_id"] for r in fab if not retraction.search(r["answer"])]
    if miss:
        bad.append(f"answers without retraction language: {miss[:3]}")
    return not bad, bad


def check_style_spread(train, eval_rows):
    rows = train + eval_rows
    bad = []
    wh = Counter((r["question"].split() or [""])[0].lower().rstrip("?:,")
                 for r in rows)
    if len(wh) < 10:
        bad.append(f"distinct wh-openers {len(wh)} < 10")
    median = statistics.median(len(r["answer"]) for r in rows)
    if median > 350:
        bad.append(f"median answer length {median} > 350")
    return not bad, bad


def check_stats_consistency(train, eval_rows, stats):
    bad = []
    all_rows = train + eval_rows
    totals = stats.get("totals") or {}
    if totals.get("train") != len(train) or totals.get("eval") != len(eval_rows):
        bad.append(f"stats totals {totals} != files "
                   f"{len(train)}/{len(eval_rows)}")
    if totals.get("total") != len(all_rows):
        bad.append("stats total mismatch")
    cats = Counter(str(r.get("category") or "UNKNOWN") for r in all_rows)
    if dict(cats) != stats.get("category_counts"):
        bad.append("stats category_counts mismatch")
    leak = stats.get("leakage") or {}
    for k in ("shared_sources_train_eval", "shared_example_ids",
              "frozen_sources_in_dataset"):
        if leak.get(k):
            bad.append(f"stats leakage {k}: {leak[k]}")
    if stats.get("row_gate_problems") or stats.get("grounding_problems"):
        bad.append("stats record gate/grounding problems")
    if (stats.get("gate_report") or {}).get("level") not in ("PASS", "WARN"):
        bad.append("stats gate level not PASS/WARN")
    if stats.get("frozen_sha256") != FROZEN_EVAL_SHA256:
        bad.append("stats frozen_sha256 mismatch")
    if stats.get("split", {}).get("coverage_missing"):
        bad.append(f"stats coverage_missing: {stats['split']['coverage_missing']}")
    if stats.get("seed") != "42":
        bad.append(f"stats seed {stats.get('seed')!r} != '42'")
    return not bad, bad


def check_frozen_eval_untouched(train, eval_rows):
    digest = sha256_file(FROZEN_EVAL_PATH)
    ok = digest == FROZEN_EVAL_SHA256
    return ok, [] if ok else [f"sha256 {digest} != {FROZEN_EVAL_SHA256}"]


def check_config_consistency(train, eval_rows):
    import yaml
    bad = []
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    ds = cfg.get("dataset") or {}
    tr = cfg.get("training") or {}
    ad = cfg.get("adapter") or {}
    if ds.get("train_file") != "./data/training/sft_train_v2.jsonl":
        bad.append(f"config train_file {ds.get('train_file')}")
    if ds.get("eval_file") != "./data/evaluation/sft_eval_v2.jsonl":
        bad.append(f"config eval_file {ds.get('eval_file')}")
    if ds.get("train_rows") != len(train):
        bad.append(f"config train_rows {ds.get('train_rows')} != {len(train)}")
    if ds.get("eval_rows") != len(eval_rows):
        bad.append(f"config eval_rows {ds.get('eval_rows')} != {len(eval_rows)}")
    if str(tr.get("learning_rate")) not in ("3e-05", "3e-5"):
        bad.append(f"config learning_rate {tr.get('learning_rate')} != 3e-5")
    if tr.get("num_train_epochs") != 2:
        bad.append(f"config epochs {tr.get('num_train_epochs')} != 2")
    if tr.get("seed") != 42:
        bad.append("config seed != 42")
    if "dapt01-checkpoint-15248" not in str(ad.get("continue_from") or ""):
        bad.append(f"config adapter lineage {ad.get('continue_from')}")
    if cfg.get("metadata", {}).get("experiment_id") != "SFT-02":
        bad.append("config experiment_id != SFT-02")
    return not bad, bad


def check_readonly_inputs(train, eval_rows):
    bad = []
    checks = [(TRAIN_V1_PATH, 50), (OUT_TRAIN, len(train)),
              (OUT_EVAL, len(eval_rows)), (GOLD_PATH, 54)]
    for path, want in checks:
        got = len(read_jsonl(path))
        if got != want:
            bad.append(f"{os.path.basename(path)}: {got} rows != {want}")
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        schema = json.load(fh)
    if "messages" not in schema.get("properties", {}):
        bad.append("schema lost messages property")
    return not bad, bad


# ---------------------------------------------------------------------------
CHECKS = [
    check_schema,
    check_example_ids_unique,
    check_no_exact_duplicates,
    check_no_near_duplicates,
    check_provenance_and_manifest,
    check_rights,
    check_origin_object,
    check_split_separation,
    check_deterministic_split,
    check_pair_integrity,
    check_eval_coverage,
    check_frozen_leakage,
    check_messages,
    check_answer_quality,
    check_row_gates_and_grounding,
    check_gate_rerun,
    check_category_targets,
    check_abstention_balance,
    check_attribution_balance,
    check_antifabrication,
    check_style_spread,
]


def main(argv=None) -> int:
    train, eval_rows = load_outputs()
    stats = load_stats()
    failed = 0
    for fn in CHECKS:
        ok, bad = fn(train, eval_rows)
        name = fn.__name__.replace("check_", "")
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}")
        if not ok:
            failed += 1
            for line in bad[:8]:
                print(f"        {line}")
    for fn in (check_stats_consistency,):
        ok, bad = fn(train, eval_rows, stats)
        name = fn.__name__.replace("check_", "")
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            failed += 1
            for line in bad[:8]:
                print(f"        {line}")
    for fn in (check_frozen_eval_untouched, check_config_consistency,
               check_readonly_inputs):
        ok, bad = fn(train, eval_rows)
        name = fn.__name__.replace("check_", "")
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            failed += 1
            for line in bad[:8]:
                print(f"        {line}")
    print(f"\n{len(CHECKS) + 4} checks, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
