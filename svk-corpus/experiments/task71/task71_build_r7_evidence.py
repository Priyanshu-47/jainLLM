"""TASK 71 Phase 2 — R7 evidence window (EVIDENCE_K=10, TEXT_TRUNC=1000).

Reuses the frozen Task-69 builder (experiments/task69/build_rag_evidence.py)
byte-for-byte for retrieval, canonical contract, context rendering and
evidence scoring, changing ONLY the experiment-only R7 configuration:

    EVIDENCE_K  5 -> 10      (passages handed to the model)
    TEXT_TRUNC  500 -> 1000  (chars per passage in the prompt context)

TOP_K, POOL, MAX_METADATA_FILL, BM25 parameters, reranker policy,
normalization, context renderer, contract validator and score_task60
evidence scoring are untouched. The Task-69 files are never overwritten —
outputs go to data/evaluation/task71_r7_*.

After building, asserts the Phase-2 hard gate: the retrieved-config diff vs
data/evaluation/task69_retrieval_metrics.json must be exactly
{evidence_k: 5->10, text_trunc: 500->1000}, else STOP.

Outputs
  data/evaluation/task71_r7_evidence.jsonl
  data/evaluation/task71_r7_prompts.jsonl
  data/evaluation/task71_r7_metrics.json
"""

from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVAL = REPO / "data" / "evaluation"

TASK69_METRICS = EVAL / "task69_retrieval_metrics.json"
OUT_EVIDENCE = EVAL / "task71_r7_evidence.jsonl"
OUT_PROMPTS = EVAL / "task71_r7_prompts.jsonl"
OUT_METRICS = EVAL / "task71_r7_metrics.json"

R7_EVIDENCE_K = 10
R7_TEXT_TRUNC = 1000
TASK69_EVIDENCE_K = 5
TASK69_TEXT_TRUNC = 500
EXPECTED_CONFIG_DIFF = {"evidence_k", "text_trunc"}

FROZEN_SHA = "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    sys.path.insert(0, str(REPO / "experiments" / "task69"))
    m = importlib.import_module("build_rag_evidence")

    # --- freeze-verify inputs, then apply ONLY the R7 diff ---
    if sha256_file(EVAL / "dapt01_eval_cases.jsonl") != FROZEN_SHA:
        raise SystemExit("STOP: frozen benchmark sha mismatch before build")
    if (m.EVIDENCE_K, m.TEXT_TRUNC) != (TASK69_EVIDENCE_K, TASK69_TEXT_TRUNC):
        raise SystemExit(
            f"STOP: Task-69 builder constants drifted: "
            f"{(m.EVIDENCE_K, m.TEXT_TRUNC)} != (5, 500)"
        )

    m.EVIDENCE_K = R7_EVIDENCE_K
    m.TEXT_TRUNC = R7_TEXT_TRUNC
    # truncate() binds its default at def-time -> rebind the name so every
    # call site (truncate(res["text"])) uses the R7 limit.
    _orig_truncate = m.truncate
    m.truncate = lambda text, limit=R7_TEXT_TRUNC: _orig_truncate(text, R7_TEXT_TRUNC)
    m.OUT_EVIDENCE = OUT_EVIDENCE
    m.OUT_PROMPTS = OUT_PROMPTS
    m.OUT_METRICS = OUT_METRICS

    rc = m.main()
    if rc != 0:
        raise SystemExit(f"builder failed rc={rc}")

    # --- relabel the metrics payload (builder writes Task-69 labels) ---
    payload = json.loads(OUT_METRICS.read_text(encoding="utf-8"))
    payload["task"] = (
        "TASK 71 — R7 governed retrieval (EVIDENCE_K=10, TEXT_TRUNC=1000) "
        "over frozen Task-60 queries"
    )
    payload["variant"] = "R7 (Task-70 variant: evidence window k5->k10 + trunc 500->1000)"
    payload["builder"] = (
        "experiments/task69/build_rag_evidence.py reused via "
        "experiments/task71/task71_build_r7_evidence.py (constants patched only)"
    )

    # --- Phase 2 hard gate: config diff vs Task-69 must be exactly R7 ---
    t69 = json.loads(TASK69_METRICS.read_text(encoding="utf-8"))
    cfg69, cfg71 = t69["config"], payload["config"]
    keys = set(cfg69) | set(cfg71)
    diff = {
        k: {"task69": cfg69.get(k), "task71": cfg71.get(k)}
        for k in sorted(keys)
        if cfg69.get(k) != cfg71.get(k)
    }
    if set(diff) != EXPECTED_CONFIG_DIFF:
        raise SystemExit(f"STOP: config diff not limited to R7 keys: {diff}")
    if diff["evidence_k"] != {"task69": TASK69_EVIDENCE_K, "task71": R7_EVIDENCE_K}:
        raise SystemExit(f"STOP: evidence_k diff wrong: {diff['evidence_k']}")
    if diff["text_trunc"] != {"task69": TASK69_TEXT_TRUNC, "task71": R7_TEXT_TRUNC}:
        raise SystemExit(f"STOP: text_trunc diff wrong: {diff['text_trunc']}")
    payload["config_diff_vs_task69"] = diff
    payload["config_diff_verified"] = True

    # --- prompt-side invariants: 10 items everywhere, new context shas ---
    prompt_rows = [
        json.loads(ln)
        for ln in OUT_PROMPTS.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    t69_prompts = {
        json.loads(ln)["example_id"]: json.loads(ln)
        for ln in (EVAL / "task69_rag_prompts.jsonl").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    }
    if len(prompt_rows) != 47:
        raise SystemExit(f"STOP: expected 47 prompt rows, got {len(prompt_rows)}")
    for r in prompt_rows:
        if r["n_evidence_items"] != R7_EVIDENCE_K:
            raise SystemExit(f"STOP: {r['example_id']} n_evidence_items != 10")
        if r["context_sha256"] == t69_prompts[r["example_id"]]["context_sha256"]:
            raise SystemExit(f"STOP: {r['example_id']} context identical to Task-69")

    OUT_METRICS.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    agg = payload["aggregate"]
    print(f"R7 config diff verified: {json.dumps(diff)}")
    print(f"CONFIG_DIFF_GATE_PASS evidence_k=10 text_trunc=1000 n_prompts={len(prompt_rows)}")
    print(f"wrote {OUT_EVIDENCE.relative_to(REPO)} ({len(prompt_rows)})")
    print(f"wrote {OUT_PROMPTS.relative_to(REPO)} ({len(prompt_rows)})")
    print(f"wrote {OUT_METRICS.relative_to(REPO)}")
    print(
        "r7 aggregate:",
        json.dumps(
            {
                "evidence_answer_score_mean": agg["evidence_answer_score_mean"],
                "evidence_answer_score_full": agg["evidence_answer_score_full"],
                "source_recall_at_10": agg["source_recall_at_10"],
                "unit_hit_at_10": agg["unit_hit_at_10"],
                "context_chars_median": agg["context_chars_median"],
                "contract_violations": len(agg["contract_violations"]),
                "abstention_evidence_forbidden_hits": agg["abstention_evidence_forbidden_hits"],
            }
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
