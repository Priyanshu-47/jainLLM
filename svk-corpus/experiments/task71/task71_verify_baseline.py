"""TASK 71 Phase 3 — baseline reproduction gate (STOP if it does not reproduce).

Compares the freshly generated Phase-3 BASE+RAG run against the frozen
Task-69 BASE+RAG results:

  frozen : data/evaluation/task69_base_rag_results.jsonl
  fresh  : data/evaluation/task71_baseline_base_rag_results.jsonl

Byte-exact per case on: answer, input_prompt_sha256,
evidence_context_sha256, new_tokens, prompt_style, decoding, seed,
system_prompt, n_evidence_items. decode_seconds is timing-only and is
excluded (recorded separately). Row count and order must match.

Output
  data/evaluation/task71_baseline_check.json

Exit codes
  0 = reproduction verified (gate PASS)
  3 = reproduction mismatch (gate FAIL -> STOP, do not proceed)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVAL = REPO / "data" / "evaluation"

FROZEN = EVAL / "task69_base_rag_results.jsonl"
FRESH = EVAL / "task71_baseline_base_rag_results.jsonl"
OUT = EVAL / "task71_baseline_check.json"

TASK69_PROMPTS_SHA = "00096f61a4a2aea525b2f1bfe71449b626bc17a60073e4b4e9dac05f6edd5b8e"
BYTE_FIELDS = (
    "answer",
    "input_prompt_sha256",
    "evidence_context_sha256",
    "new_tokens",
    "prompt_style",
    "decoding",
    "seed",
    "system_prompt",
    "n_evidence_items",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def answer_sha(a: str) -> str:
    return hashlib.sha256(a.encode("utf-8")).hexdigest()


def main() -> int:
    frozen, fresh = load_jsonl(FROZEN), load_jsonl(FRESH)

    check: dict = {
        "task": "TASK 71 Phase 3 — Task-69 BASE+RAG baseline reproduction",
        "frozen_file": str(FROZEN.relative_to(REPO)),
        "frozen_sha256": sha256_file(FROZEN),
        "fresh_file": str(FRESH.relative_to(REPO)),
        "fresh_sha256": sha256_file(FRESH),
        "prompts_sha_expected": TASK69_PROMPTS_SHA,
        "n_frozen": len(frozen),
        "n_fresh": len(fresh),
        "mismatches": [],
        "timing_note": "decode_seconds excluded (wall-clock, non-deterministic)",
    }

    ok = True
    if len(frozen) != 47 or len(fresh) != 47:
        ok = False
        check["mismatches"].append(
            {"where": "row_count", "frozen": len(frozen), "fresh": len(fresh)}
        )

    frozen_by = {r["example_id"]: r for r in frozen}
    if [r["example_id"] for r in fresh] != [r["example_id"] for r in frozen]:
        ok = False
        check["mismatches"].append({"where": "row_order_or_ids", "frozen": "47 ids", "fresh": [r["example_id"] for r in fresh]})

    for r in fresh:
        eid = r["example_id"]
        f = frozen_by.get(eid)
        if f is None:
            ok = False
            check["mismatches"].append({"example_id": eid, "where": "missing_in_frozen"})
            continue
        for field in BYTE_FIELDS:
            if r.get(field) != f.get(field):
                ok = False
                check["mismatches"].append(
                    {
                        "example_id": eid,
                        "where": field,
                        "frozen": f.get(field),
                        "fresh": r.get(field),
                    }
                )

    check["gate"] = "PASS" if ok else "FAIL"
    check["verified_byte_exact_fields"] = list(BYTE_FIELDS) if ok else None
    check["answer_sha256_all_match"] = (
        ok
        and all(answer_sha(r["answer"]) == answer_sha(frozen_by[r["example_id"]]["answer"]) for r in fresh)
    )
    OUT.write_text(json.dumps(check, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}")

    if not ok:
        print("PHASE3_BASELINE_GATE_FAIL — Task-69 result NOT reproduced")
        for m in check["mismatches"][:20]:
            print("  mismatch:", json.dumps(m, ensure_ascii=False))
        return 3

    print(
        "PHASE3_BASELINE_GATE_PASS — 47/47 rows byte-exact vs task69_base_rag_results.jsonl "
        f"(file sha {check['fresh_sha256'][:16]}…)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
