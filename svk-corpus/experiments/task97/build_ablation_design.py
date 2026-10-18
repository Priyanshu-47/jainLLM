"""Task 97 — build the case037 ablation design matrix (NO model calls).

Constructs every planned cell's exact evidence blocks and prompt strings from
the pinned Task-74 hybrid ranking (byte-verified against Task-94), using only
authentic corpus text. Extended cells re-enable each unit's own real tail
(same text the Task-94 D arm saw); nothing is fabricated or reordered.

Writes experiments/task97/cell_specs.json and data/reports/task97_ablation_design.json.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

CASES_PATH = REPO / "data" / "evaluation" / "dapt01_eval_cases.jsonl"
TASK94_JSONL = REPO / "experiments" / "task94" / "task94_ab_results.jsonl"
TASK92_SCRIPT = REPO / "experiments" / "task92" / "run_task92_replay.py"
TASK74_QUERIES = REPO / "data" / "evaluation" / "task74_queries_input.jsonl"
DENSE_DIR = REPO / "experiments" / "task74" / "dense_index"
POLICY_PATH = REPO / "configs" / "policy.toml"
OUT_CELLS = REPO / "experiments" / "task97" / "cell_specs.json"
OUT_DESIGN = REPO / "data" / "reports" / "task97_ablation_design.json"

EID = "DAPT01EVAL-037"
TAIL_UNITS = {"E2": 2, "E5": 5, "E10": 10}   # evidence_id -> index
CELL_DEFS = [  # (cell_id, extend set)
    ("B_t500_original", frozenset()),
    ("D_t2000_original", frozenset({"E2", "E5", "E10"})),
    ("X_E2only", frozenset({"E2"})),
    ("X_E5only", frozenset({"E5"})),
    ("X_E10only", frozenset({"E10"})),
    ("X_E5E10", frozenset({"E5", "E10"})),
    ("X_E2E5", frozenset({"E2", "E5"})),
    ("X_E2E10", frozenset({"E2", "E10"})),
]
TOKEN_EST_DIVISOR = 4


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    from svk_corpus.generation.answer import EvidenceItem, build_prompt
    from svk_corpus.retrieval.api import load_retrieval_policy
    from svk_corpus.retrieval.service import (RetrievalService,
                                              load_dense_index)

    OUT_CELLS.parent.mkdir(parents=True, exist_ok=True)
    policy_sha = sha256_file(POLICY_PATH)
    cases = {c["example_id"]: c for c in load_jsonl(CASES_PATH)}
    t94 = {r["example_id"] + "_" + r["arm"]: r
           for r in load_jsonl(TASK94_JSONL)
           if r.get("kind") != "arm_validation"}
    t92 = load_module("task92_replay", TASK92_SCRIPT)

    print("[97] building retrieval service + verifying dense index...")
    policy = load_retrieval_policy(REPO)
    svc = RetrievalService.from_repo(policy, REPO)
    dense = load_dense_index(DENSE_DIR, svc.docs,
                             verify_file_sha=True, verify_alignment=True)
    qrows = load_jsonl(TASK74_QUERIES)
    qemb = np.load(DENSE_DIR / "queries_emb.f32.npy")
    qmap = {r["question"]: qemb[i] for i, r in enumerate(qrows)}
    case = cases[EID]
    qvec = qmap[case["question"]]
    top10, *_ = t92.hybrid_full_list(svc, dense, qvec, case["question"])

    # base item fields from authentic docs
    base_items = []
    for i, res in enumerate(top10[:10], 1):
        d = res.doc
        base_items.append({
            "evidence_id": f"E{i}", "text_id": d.text_id,
            "source_id": d.source_id, "title": d.title,
            "full_text": d.text or "", "citation": d.citation,
            "score": float(res.score), "rank": int(res.rank),
            "channel": str(res.channel),
            "sect": getattr(d, "sect", "") or "",
            "religious_scope": getattr(d, "religious_scope", "") or "",
            "knowledge_layer": getattr(d, "knowledge_layer", "") or "",
            "teacher_or_author": getattr(d, "teacher_or_author", "") or "",
        })

    # byte-verify against task94 B/D evidence
    b_stored = t94[EID + "_B"]["evidence"]
    d_stored = t94[EID + "_D"]["evidence"]
    for bi, be, de in zip(base_items, b_stored, d_stored):
        assert bi["text_id"] == be["text_id"] == de["text_id"]
        assert bi["full_text"].startswith(be["text"])
        assert de["text"] == bi["full_text"][:2000]

    question = case["question"]
    cells = {}
    for cell_id, extend in CELL_DEFS:
        items_meta, texts = [], []
        for bi in base_items:
            eid = bi["evidence_id"]
            trunc = 2000 if eid in extend else 500
            text = bi["full_text"][:trunc]
            texts.append(text)
            items_meta.append({
                "evidence_id": eid, "text_id": bi["text_id"],
                "chars": len(text), "trunc": trunc,
                "extended_in_this_cell": eid in extend,
                "full_text_len": len(bi["full_text"]),
            })
        ev_items = []
        for bi, text in zip(base_items, texts):
            fields = {k: bi[k] for k in
                      ("evidence_id", "text_id", "source_id", "title",
                       "citation", "score", "rank", "channel", "sect",
                       "religious_scope", "knowledge_layer",
                       "teacher_or_author")}
            fields["text"] = text
            ev_items.append(EvidenceItem(**fields))
        prompt = build_prompt(question, ev_items)
        cells[cell_id] = {
            "extend": sorted(extend),
            "evidence": items_meta,
            "prompt_chars": len(prompt),
            "prompt_token_estimate": len(prompt) // TOKEN_EST_DIVISOR,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "evidence_text_total_chars": sum(len(t) for t in texts),
        }
        print(f"    {cell_id}: extend={sorted(extend)} "
              f"chars={cells[cell_id]['prompt_chars']} "
              f"tok~{cells[cell_id]['prompt_token_estimate']}")

    # sanity: B and D cells must equal task94 prompts
    b_ok = cells["B_t500_original"]["prompt_sha256"] == hashlib.sha256(
        t94[EID + "_B"]["prompt"].encode()).hexdigest()
    d_ok = cells["D_t2000_original"]["prompt_sha256"] == hashlib.sha256(
        t94[EID + "_D"]["prompt"].encode()).hexdigest()
    print(f"    B cell matches task94: {b_ok}; D cell matches task94: {d_ok}")

    # per-tail deltas
    tails = {}
    for bi in base_items:
        eid = bi["evidence_id"]
        if eid in TAIL_UNITS:
            b_txt = bi["full_text"][:500]
            d_txt = bi["full_text"][:2000]
            tails[eid] = {
                "text_id": bi["text_id"],
                "b_chars": len(b_txt), "full_chars": len(d_txt),
                "delta_chars": len(d_txt) - len(b_txt),
                "delta_token_est": (len(d_txt) - len(b_txt))
                // TOKEN_EST_DIVISOR,
                "tail_preview": d_txt[500:500 + 120].replace("\n", " "),
                "tail_mentions_terapanth_or_founding":
                    any(w in d_txt[500:].casefold()
                        for w in ("terapanth", "terapantha", "founded",
                                  "1658", "1741", "birbhan")),
            }

    payload = {
        "task": "task97",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "case_id": EID,
        "question": question,
        "policy_sha256": policy_sha,
        "dense_verified": bool(getattr(dense, "verified", False)),
        "prompt_verification": {
            "B_cell_byte_equal_task94": b_ok,
            "D_cell_byte_equal_task94": d_ok,
        },
        "tails": tails,
        "cells": cells,
        "model_calls": 0,
    }
    OUT_CELLS.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                         encoding="utf-8")
    print(f"[97] cells -> {OUT_CELLS.relative_to(REPO)}")
    return 0 if (b_ok and d_ok) else 2


if __name__ == "__main__":
    raise SystemExit(main())
