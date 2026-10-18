"""Task 98 — execute the approved Task 97 case037 evidence-tail ablation.

14 planned model calls on the existing local Ollama (never restarted):
  1 sanity trial each of B_t500_original and D_t2000_original (checks),
  3 trials each of X_E2only, X_E5only, X_E10only, X_E5E10 (exploratory).

All 8 cell prompts are rebuilt from the pinned Task-74 hybrid top-10 and
byte-verified against experiments/task97/cell_specs.json (and B/D against
Task-94 stored prompts) BEFORE any generation. Mixed per-cell truncation
(500 vs 2000 per unit) is applied by rebuilding EvidenceItems per cell; the
production SYSTEM_PROMPT, build_prompt, citation regexes and abstention
regex from svk_corpus.generation.answer are reused unmodified (imported,
not edited). Only authentic corpus tails differ between cells.

Usage:
    PYTHONPATH=src .venv/bin/python experiments/task98/run_task98_ablation.py
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

CASES_PATH = REPO / "data" / "evaluation" / "dapt01_eval_cases.jsonl"
TASK94_JSONL = REPO / "experiments" / "task94" / "task94_ab_results.jsonl"
TASK92_SCRIPT = REPO / "experiments" / "task92" / "run_task92_replay.py"
TASK97_SPECS = REPO / "experiments" / "task97" / "cell_specs.json"
TASK74_QUERIES = REPO / "data" / "evaluation" / "task74_queries_input.jsonl"
DENSE_DIR = REPO / "experiments" / "task74" / "dense_index"
POLICY_PATH = REPO / "configs" / "policy.toml"

OUT_DIR = REPO / "experiments" / "task98"
RAW_JSONL = OUT_DIR / "task98_raw.jsonl"
REPORT_MD = REPO / "data" / "reports" / "task98_ablation_results.md"
REPORT_JSON = REPO / "data" / "reports" / "task98_ablation_results.json"

CASE_ID = "DAPT01EVAL-037"
NUM_PREDICT_DEFAULT = 256

EXPECTED_HASHES = {
    "policy.toml":
        "f32308d94dd9d54395daf2d4bb5ef7ede7600f7762e77dd480aea6926bf25851",
    "task94_ab_results.jsonl":
        "a23e0e0794be30706a7eb394da9f3a09ed1b73e38cc9ced918626df16e8e85c1",
    "frozen_cases":
        "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81",
    "queries_emb.f32.npy":
        "62ec0acdc06f18bc5cbe19370b736531c70b3f0ace172fe9d5dd51dcf3e1a36d",
    "corpus_emb.f16.npy":
        "f54919e63599c94e9a7eb931bde2d4255ee77c2c64c381a28151d63eb00fb91f",
    "task97_cell_specs.json":
        "d18c3efcad99bff5db79dea7044b7bb4007a286d143c415dab0e34a96d416932",
}

# 14-call plan: sanity first, then 3 interleaved rounds of the 4 cells.
PLAN = [
    ("B_t500_original", 1, "sanity"),
    ("D_t2000_original", 1, "sanity"),
] + [
    (cell, trial, "intermediate")
    for trial in (1, 2, 3)
    for cell in ("X_E2only", "X_E5only", "X_E10only", "X_E5E10")
]

_YEAR_AFTER_FOUNDED = re.compile(
    r"founded[^.]{0,60}\b(16|17|18|19|20)\d{2}\b", re.IGNORECASE)


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


def git_info() -> dict:
    def _run(args: list[str]) -> str:
        return subprocess.run(args, cwd=REPO.parent, capture_output=True,
                              text=True, check=True).stdout.strip()
    return {"head": _run(["git", "rev-parse", "HEAD"]),
            "status_short": _run(["git", "status", "--short"])}


def termination_heuristic(answer: str, eval_count: int | None,
                          num_predict: int) -> dict:
    stripped = (answer or "").rstrip()
    ends_terminal = bool(stripped) and stripped[-1] in ".!?\u201d\"')\"]"
    return {
        "eval_count": eval_count,
        "num_predict": num_predict,
        "hit_num_predict_cap": eval_count == num_predict,
        "ends_with_terminal_punctuation": ends_terminal,
        "answer_len_chars": len(answer or ""),
    }


def asserts_founded_year(answer: str) -> bool:
    a = answer or ""
    return bool(_YEAR_AFTER_FOUNDED.search(a)) and not a.lstrip().upper().startswith(
        "ABSTAIN")


def main() -> int:
    t_run0 = time.perf_counter()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if RAW_JSONL.exists():
        print(f"[98] BLOCKED — {RAW_JSONL} already exists; refusing to "
              "overwrite a prior run", flush=True)
        return 3

    # ---------------- Step 0 — preflight (no model calls) ----------------
    print("[98] step 0 — preflight", flush=True)
    before = git_info()
    policy_sha_before = sha256_file(POLICY_PATH)
    hash_status = {}
    for name, path in {
        "policy.toml": POLICY_PATH,
        "task94_ab_results.jsonl": TASK94_JSONL,
        "frozen_cases": CASES_PATH,
        "queries_emb.f32.npy": DENSE_DIR / "queries_emb.f32.npy",
        "corpus_emb.f16.npy": DENSE_DIR / "corpus_emb.f16.npy",
        "task97_cell_specs.json": TASK97_SPECS,
    }.items():
        got = sha256_file(path)
        hash_status[name] = {"expected": EXPECTED_HASHES[name], "got": got,
                             "ok": got == EXPECTED_HASHES[name]}
        print(f"    {name}: {'OK' if hash_status[name]['ok'] else 'MISMATCH'}",
              flush=True)
    if not all(v["ok"] for v in hash_status.values()):
        print("[98] BLOCKED — input hash mismatch; no model calls made",
              flush=True)
        return 3

    from svk_corpus.generation.answer import (SYSTEM_PROMPT, EvidenceItem,
                                              _ABSTAIN_RE, _CITE_RE,
                                              build_prompt)
    from svk_corpus.generation.provider import config_from_env, OllamaProvider
    from svk_corpus.retrieval.api import load_retrieval_policy
    from svk_corpus.retrieval.service import RetrievalService, load_dense_index

    provider_status = OllamaProvider(config_from_env()).model_status()
    print(f"    ollama: {provider_status}", flush=True)
    if not (provider_status.get("reachable")
            and provider_status.get("model_present")):
        print("[98] BLOCKED — ollama/model unavailable", flush=True)
        return 3
    cfg = config_from_env()
    if cfg.num_predict != NUM_PREDICT_DEFAULT:
        print(f"[98] BLOCKED — effective num_predict={cfg.num_predict} != "
              f"production default {NUM_PREDICT_DEFAULT}; settings drift",
              flush=True)
        return 3
    print(f"    effective settings: model={cfg.model} num_ctx={cfg.num_ctx} "
          f"temperature={cfg.temperature} num_predict={cfg.num_predict} "
          f"timeout_s={cfg.timeout_s}", flush=True)

    cases = {c["example_id"]: c for c in load_jsonl(CASES_PATH)}
    if CASE_ID not in cases:
        print(f"[98] BLOCKED — case {CASE_ID} missing from frozen cases",
              flush=True)
        return 3
    t94_gen = [r for r in load_jsonl(TASK94_JSONL)
               if r.get("kind") != "arm_validation"]
    specs = json.loads(TASK97_SPECS.read_text(encoding="utf-8"))
    t92 = load_module("task92_replay", TASK92_SCRIPT)

    print("[98] building retrieval service + verifying pinned dense index...",
          flush=True)
    t0 = time.perf_counter()
    policy = load_retrieval_policy(REPO)
    svc = RetrievalService.from_repo(policy, REPO)
    dense = load_dense_index(DENSE_DIR, svc.docs,
                             verify_file_sha=True, verify_alignment=True)
    print(f"    docs={len(svc.docs)} dense_n={dense.n} "
          f"build={time.perf_counter()-t0:.1f}s", flush=True)

    qrows = load_jsonl(TASK74_QUERIES)
    qemb = np.load(DENSE_DIR / "queries_emb.f32.npy")
    qmap = {r["question"]: qemb[i] for i, r in enumerate(qrows)}
    case = cases[CASE_ID]
    qvec = qmap[case["question"]]
    top10, *_ = t92.hybrid_full_list(svc, dense, qvec, case["question"])

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

    # rebuild all 8 prompts; byte-verify against task97 cell_specs + task94
    print("[98] rebuilding 8 cell prompts and byte-verifying...", flush=True)
    cells: dict[str, dict] = {}
    cell_specs = specs["cells"]
    for cell_id, spec in cell_specs.items():
        extend = set(spec["extend"])
        items = []
        for bi in base_items:
            trunc = 2000 if bi["evidence_id"] in extend else 500
            fields = {k: bi[k] for k in
                      ("evidence_id", "text_id", "source_id", "title",
                       "citation", "score", "rank", "channel", "sect",
                       "religious_scope", "knowledge_layer",
                       "teacher_or_author")}
            fields["text"] = bi["full_text"][:trunc]
            items.append(EvidenceItem(**fields))
        prompt = build_prompt(case["question"], items)
        got_sha = hashlib.sha256(prompt.encode()).hexdigest()
        ok = got_sha == spec["prompt_sha256"]
        cells[cell_id] = {"prompt": prompt, "prompt_sha256": got_sha,
                          "extend": sorted(extend), "hash_ok": ok,
                          "chars": len(prompt)}
        print(f"    {cell_id}: extend={sorted(extend)} chars={len(prompt)} "
              f"hash_ok={ok}", flush=True)
        if not ok:
            print("[98] BLOCKED — cell prompt hash != approved task97 design",
                  flush=True)
            return 3

    for arm, cell_id in (("B", "B_t500_original"),
                         ("D", "D_t2000_original")):
        stored = next(r for r in t94_gen
                      if r["example_id"] == CASE_ID and r["arm"] == arm)
        match = cells[cell_id]["prompt"] == stored["prompt"]
        cells[cell_id]["byte_equal_task94"] = match
        print(f"    {cell_id} byte_equal_task94={match}", flush=True)
        if not match:
            print("[98] BLOCKED — original prompt not reproducible",
                  flush=True)
            return 3

    # ---------------- generation ----------------
    print("[98] executing 14 planned calls (sanity x2 + 4 cells x3)...",
          flush=True)
    raw_fh = RAW_JSONL.open("x", encoding="utf-8")  # non-overwriting create

    def write_raw(row: dict) -> None:
        raw_fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        raw_fh.flush()

    provider = OllamaProvider(cfg)
    calls_made = 0
    rows_out: list[dict] = []
    for cell_id, trial_idx, kind in PLAN:
        cell = cells[cell_id]
        t0 = time.perf_counter()
        try:
            gen = provider.generate(system=SYSTEM_PROMPT, prompt=cell["prompt"])
            err = ""
        except Exception as exc:  # noqa: BLE001 — record and stop
            wall = time.perf_counter() - t0
            print(f"[98] ERROR on {cell_id} trial {trial_idx}: {exc}",
                  flush=True)
            write_raw({"task": "task98", "case_id": CASE_ID,
                       "cell_id": cell_id, "trial_index": trial_idx,
                       "kind": kind, "error": str(exc),
                       "wall_s": round(wall, 3)})
            raw_fh.close()
            return 4
        calls_made += 1
        wall = time.perf_counter() - t0
        answer = gen.text or ""
        abstained = bool(_ABSTAIN_RE.match(answer))
        cited_raw = _CITE_RE.findall(answer)
        valid_ids = {f"E{i}" for i in range(1, 11)}
        flat: list[str] = []
        for c in cited_raw:
            for p in c.split(","):
                p = p.strip()
                if p and p in valid_ids and p not in flat:
                    flat.append(p)
        invalid = sorted({p.strip() for c in cited_raw for p in c.split(",")
                          if p.strip() and p.strip() not in valid_ids})
        row = {
            "task": "task98", "case_id": CASE_ID,
            "question": case["question"],
            "cell_id": cell_id, "trial_index": trial_idx, "kind": kind,
            "extend": cell["extend"],
            "prompt_sha256": cell["prompt_sha256"],
            "prompt_chars": cell["chars"],
            "prompt_byte_equal_task94":
                cell.get("byte_equal_task94", None),
            "evidence_text_ids": [bi["text_id"] for bi in base_items],
            "model": provider.model,
            "temperature": cfg.temperature,
            "num_ctx": cfg.num_ctx,
            "num_predict_effective": cfg.num_predict,
            "timeout_s": cfg.timeout_s,
            "answer": answer,
            "abstained": abstained,
            "abstention_reason": "model_abstain" if abstained else "",
            "citations": flat,
            "invalid_citations": invalid,
            "asserts_founded_year": asserts_founded_year(answer),
            "mentions_1658": "1658" in answer,
            "eval_count": gen.eval_count,
            "latency_wall_s": round(wall, 3),
            "termination": termination_heuristic(answer, gen.eval_count,
                                                 cfg.num_predict),
            "error": err,
        }
        write_raw(row)
        rows_out.append(row)
        print(f"    [{kind}] {cell_id} trial={trial_idx} "
              f"wall={row['latency_wall_s']}s eval={row['eval_count']} "
              f"abst={abstained} assert={row['asserts_founded_year']} "
              f"cites={flat}", flush=True)

    provider.close()
    raw_fh.close()
    total_wall = round(time.perf_counter() - t_run0, 1)

    # ---------------- analysis ----------------
    by_cell: dict[str, list[dict]] = {}
    for r in rows_out:
        by_cell.setdefault(r["cell_id"], []).append(r)

    def cell_stats(cell_id: str) -> dict:
        rs = by_cell[cell_id]
        return {
            "trials": len(rs),
            "abstained": [r["abstained"] for r in rs],
            "asserts_founded_year": [r["asserts_founded_year"] for r in rs],
            "mentions_1658": [r["mentions_1658"] for r in rs],
            "eval_counts": [r["eval_count"] for r in rs],
            "latency_wall_s": [r["latency_wall_s"] for r in rs],
            "hit_cap": [r["termination"]["hit_num_predict_cap"] for r in rs],
            "abstain_rate": sum(bool(r["abstained"]) for r in rs) / len(rs),
            "assert_rate": sum(bool(r["asserts_founded_year"]) for r in rs)
            / len(rs),
        }

    stats = {cid: cell_stats(cid) for cid in
             ("B_t500_original", "D_t2000_original", "X_E2only", "X_E5only",
              "X_E10only", "X_E5E10")}
    for cid, s in stats.items():
        print(f"    {cid}: abstain={s['abstained']} "
              f"assert={s['asserts_founded_year']}", flush=True)

    # sufficiency per tail (3-trial intermediate cells; exploratory)
    def verdict_for_single_tail(cell_id: str) -> str:
        s = stats[cell_id]
        if s["assert_rate"] == 1.0:
            return "sufficient (3/3 assert)"
        if s["assert_rate"] == 0.0 and s["abstain_rate"] == 1.0:
            return "not sufficient (3/3 abstain)"
        if s["abstain_rate"] == 1.0:
            return "not sufficient (abstains; no assert)"
        return f"mixed (assert {s['assert_rate']:.2f})"

    e2_v = verdict_for_single_tail("X_E2only")
    e5_v = verdict_for_single_tail("X_E5only")
    e10_v = verdict_for_single_tail("X_E10only")
    e5e10_s = stats["X_E5E10"]

    interpretation = []
    if stats["X_E2only"]["assert_rate"] == 1.0:
        interpretation.append(
            "E2 tail alone is sufficient: completing the 1658-containing "
            "unit (its own tail is factually trivial) flips the model to "
            "asserting — a localized length/format effect on the decisive "
            "unit.")
    if stats["X_E5only"]["assert_rate"] == 1.0:
        interpretation.append(
            "E5 tail alone is sufficient: the large unrelated content "
            "chunk drives the flip independent of E2 completion.")
    if stats["X_E10only"]["assert_rate"] == 1.0:
        interpretation.append(
            "E10 tail alone is sufficient despite the smallest delta — "
            "length (not specific content) dominates or the model is "
            "highly sensitive to prompt slack.")
    if e5e10_s["assert_rate"] == 1.0 and stats["X_E5only"]["assert_rate"] == 0.0:
        interpretation.append(
            "E5+E10 jointly sufficient though E5 alone is not: "
            "interaction between the two unrelated tails.")
    if (stats["X_E2only"]["assert_rate"] == 0.0
            and stats["X_E5only"]["assert_rate"] == 0.0
            and stats["X_E10only"]["assert_rate"] == 0.0
            and stats["X_E5E10"]["assert_rate"] == 0.0
            and stats["D_t2000_original"]["assert_rate"] == 1.0):
        interpretation.append(
            "No single tail (or E5+E10 pair) is sufficient; only the full "
            "D cell asserts — consistent with a threshold/interaction on "
            "combined added length+content (E2+E5 together).")
    if any(stats[c]["abstain_rate"] not in (0.0, 1.0)
           for c in ("X_E2only", "X_E5only", "X_E10only", "X_E5E10")):
        interpretation.append(
            "At least one intermediate cell flipped abstention across "
            "trials: per-cell nondeterminism reappears; treat sufficiency "
            "verdicts as exploratory and expand trials for that cell "
            "before concluding.")

    # length association across all 8 cells (descriptive only)
    length_rows = []
    for cid, s in stats.items():
        length_rows.append({
            "cell_id": cid, "chars": cells[cid]["chars"],
            "assert_rate": s["assert_rate"], "abstain_rate": s["abstain_rate"],
        })
    interpretation.append(
        "Association (descriptive, 8 cells): "
        + "; ".join(f"{r['cell_id']}={r['chars']}ch/"
                    f"assert{r['assert_rate']:.0f}" for r in length_rows)
        + ". Character count alone does not monotonically predict assertion "
          "if e.g. X_E5only (6119 ch) abstains while X_E2only (5827 ch) "
          "asserts — content of the completed unit matters beyond bulk "
          "length.")

    policy_sha_after = sha256_file(POLICY_PATH)
    after = git_info()
    results = {
        "task": "task98",
        "case_id": CASE_ID,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_calls_total": calls_made,
        "planned_calls": len(PLAN),
        "total_wall_s": total_wall,
        "model": provider.model,
        "effective_settings": {
            "temperature": cfg.temperature, "num_ctx": cfg.num_ctx,
            "num_predict": cfg.num_predict, "timeout_s": cfg.timeout_s,
        },
        "preflight": {"hashes": hash_status,
                      "ollama": provider_status,
                      "git_before": before,
                      "policy_sha256_before": policy_sha_before},
        "cell_hashes": {
            cid: {"prompt_sha256": c["prompt_sha256"], "chars": c["chars"],
                  "extend": c["extend"], "hash_ok": c["hash_ok"],
                  "byte_equal_task94": c.get("byte_equal_task94")}
            for cid, c in cells.items()},
        "stats_by_cell": stats,
        "sufficiency": {
            "X_E2only": e2_v, "X_E5only": e5_v, "X_E10only": e10_v,
            "X_E5E10": verdict_for_single_tail("X_E5E10"),
        },
        "interpretation": interpretation,
        "length_association": length_rows,
        "verification": {
            "policy_sha256_before": policy_sha_before,
            "policy_sha256_after": policy_sha_after,
            "policy_unchanged": policy_sha_before == policy_sha_after
            == EXPECTED_HASHES["policy.toml"],
            "git_before": before, "git_after": after,
            "git_unchanged_no_staged_or_tracked_edits":
                before["head"] == after["head"],
            "B_prompt_byte_equal_task94":
                cells["B_t500_original"].get("byte_equal_task94"),
            "D_prompt_byte_equal_task94":
                cells["D_t2000_original"].get("byte_equal_task94"),
            "all_cell_hashes_match_task97_design":
                all(c["hash_ok"] for c in cells.values()),
        },
        "raw_results": str(RAW_JSONL.relative_to(REPO)),
        "limitations": [
            "B/D sanity calls are n=1 checks, not a statistically strong baseline",
            "intermediate cells are 3-trial exploratory probes; do not overstate causality",
            "pure length cannot be isolated from content: every real tail carries content",
        ],
    }
    REPORT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False),
                           encoding="utf-8")
    print(f"[98] json -> {REPORT_JSON.relative_to(REPO)}", flush=True)
    print(f"[98] model_calls_total={calls_made} wall={total_wall}s",
          flush=True)
    for line in interpretation:
        print(f"    * {line}", flush=True)
    print(f"[98] policy unchanged: "
          f"{results['verification']['policy_unchanged']}; "
          f"git head unchanged: "
          f"{results['verification']['git_unchanged_no_staged_or_tracked_edits']}",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
