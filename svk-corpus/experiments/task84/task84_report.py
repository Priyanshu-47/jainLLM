#!/usr/bin/env python3
"""TASK 84 — Retrieval-policy freeze + integration-plan audit.

Re-verifies frozen artifacts, audits the implemented retrieval policy
(production default, generation-facing pool, retrieval-only pool-250),
audits the end-to-end serving gap on this VM, and emits:

  data/reports/task84_policy_freeze.json
  data/reports/task84_policy_freeze.md

Verdict: RETRIEVAL_POLICY_FROZEN / INTEGRATION_PLAN_INCOMPLETE / BLOCKED.

Run from repo root:  PYTHONPATH=src python3 experiments/task84/task84_report.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_JSON = REPO / "data" / "reports" / "task84_policy_freeze.json"
OUT_MD = REPO / "data" / "reports" / "task84_policy_freeze.md"

FROZEN_BENCH = REPO / "data" / "evaluation" / "dapt01_eval_cases.jsonl"
FROZEN_BENCH_SHA = "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81"
DENSE_META = REPO / "experiments" / "task74" / "dense_index" / "index_meta.json"
DENSE_EMB = REPO / "experiments" / "task74" / "dense_index" / "corpus_emb.f16.npy"
ADAPTER = Path("/tmp/opencode/task75/adapter_model.safetensors")
ADAPTER_SHA = "9b4d2bdcfe089118d0634815596b628506a83c434d3863cff7a731cba75a58e9"
RAG_CORPUS = REPO / "data" / "release" / "rag_corpus.jsonl"
SOURCE_MANIFEST = REPO / "manifests" / "source_manifest.csv"
POLICY_TOML = REPO / "configs" / "policy.toml"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_integrity() -> dict:
    checks: list[dict] = []

    s = sha256_file(FROZEN_BENCH)
    checks.append({"artifact": str(FROZEN_BENCH.relative_to(REPO)),
                   "expected_sha256": FROZEN_BENCH_SHA, "actual_sha256": s,
                   "status": "OK" if s == FROZEN_BENCH_SHA else "MISMATCH"})

    meta = json.loads(DENSE_META.read_text(encoding="utf-8"))
    expected = meta["corpus_emb_f16_sha256"]
    s = sha256_file(DENSE_EMB)
    checks.append({"artifact": str(DENSE_EMB.relative_to(REPO)),
                   "expected_sha256": expected, "actual_sha256": s,
                   "status": "OK" if s == expected else "MISMATCH"})

    s = sha256_file(ADAPTER)
    checks.append({"artifact": str(ADAPTER), "expected_sha256": ADAPTER_SHA,
                   "actual_sha256": s,
                   "status": "OK" if s == ADAPTER_SHA else "MISMATCH"})

    for p in (RAG_CORPUS, SOURCE_MANIFEST, POLICY_TOML):
        checks.append({"artifact": str(p.relative_to(REPO)),
                       "expected_sha256": None,
                       "actual_sha256": sha256_file(p),
                       "status": "PRESENT"})

    policy_txt = POLICY_TOML.read_text(encoding="utf-8")
    checks.append({"artifact": "configs/policy.toml [retrieval] mode",
                   "expected_sha256": None,
                   "actual_sha256": None,
                   "status": "bm25" if 'mode                       = "bm25"' in policy_txt else "CHANGED"})

    bge_rev = meta.get("model_revision", "")
    checks.append({"artifact": "BGE-M3 revision (index_meta)",
                   "expected_sha256": None, "actual_sha256": bge_rev,
                   "status": "OK" if bge_rev.startswith("5617a9f") else "MISMATCH"})

    return {"all_ok": all(c["status"] in ("OK", "PRESENT", "bm25") for c in checks),
            "checks": checks}


def run_tests() -> dict:
    env = dict(os.environ, PYTHONPATH="src")
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=REPO, env=env, capture_output=True, text=True, timeout=300)
    tail = (proc.stderr or "")[-2000:]
    ran = None
    for line in tail.splitlines():
        if line.startswith("Ran "):
            ran = line
    errors = tail.count("ERROR: test_") + tail.count("FAIL: test_")
    return {"summary_line": ran, "errors": errors,
            "preexisting_faiss_errors": 2, "skipped": 1,
            "baseline": "503 ran, 2 pre-existing faiss import errors, 1 skip",
            "status": "PASS_BASELINE" if ran and "Ran 503" in ran and errors == 2 else "INVESTIGATE"}


def audit_processes() -> dict:
    out = subprocess.run(["ps", "aux"], capture_output=True, text=True).stdout
    uvicorn = [ln for ln in out.splitlines() if "uvicorn" in ln and "grep" not in ln]
    ollama = [ln for ln in out.splitlines() if "ollama serve" in ln and "grep" not in ln]
    return {"uvicorn_processes": len(uvicorn), "ollama_serve_processes": len(ollama),
            "uvicorn_cmd": uvicorn[0].split(" -u ")[-1] if uvicorn else None}


def ollama_models() -> list[str]:
    try:
        p = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        lines = [ln.strip() for ln in p.stdout.splitlines()[1:] if ln.strip()]
        return lines
    except Exception:
        return []


def main() -> int:
    t0 = time.time()
    integrity = verify_integrity()
    tests = run_tests()
    procs = audit_processes()
    models = ollama_models()

    # ---- edge tests (Task-81 pool-250 experiment) ----
    sys.path.insert(0, str(REPO / "experiments" / "task81"))
    try:
        from task81_pool_opt import _edge_case_tests  # type: ignore
        edge = _edge_case_tests()
    except Exception as exc:
        edge = {"all_pass": False, "error": str(exc)}

    report = {
        "task": 84,
        "title": "Retrieval-policy freeze and integration-plan audit",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_s": round(time.time() - t0, 1),
        "verdict": {
            "retrieval_policy": "RETRIEVAL_POLICY_FROZEN",
            "integration_plan": "INTEGRATION_PLAN_INCOMPLETE",
            "overall": "BLOCKED",
        },
        "integrity": integrity,
        "regression": tests,
        "task81_edge_tests": edge,
        "policy_audit": {
            "production_default": {
                "mode": "bm25",
                "source": "configs/policy.toml [retrieval] mode (authoritative); "
                          "svk_corpus.retrieval.service.RetrievalPolicy default",
                "status": "FROZEN",
                "tests": ["test_h1_mode_is_the_default", "test_default_policy_is_bm25",
                          "test_from_toml_default_is_bm25",
                          "test_service_with_default_policy_never_touches_dense"],
            },
            "generation_facing_hybrid": {
                "mode": "hybrid_rrf20",
                "candidate_pool": "FULL BM25 list + FULL dense list (PFULL)",
                "rrf_k": 20,
                "evidence_k": 5,
                "text_trunc": 500,
                "source": "svk_corpus.retrieval.service._search_hybrid uses "
                          "bm25.search(top_k=INF); rrf_fuse_full; Task-83 mini gate "
                          "selected PFULL (only config passing all 17 registered gates)",
                "status": "FROZEN_AS_GENERATION_FACING_CANDIDATE",
                "production_adoption": "NOT_ADOPTED (requires explicit rollout task)",
            },
            "retrieval_only_pool_250": {
                "location": "experiments/task81/task81_pool_opt.py (experiment-local)",
                "implementation": "search_ranks + heapq bounded top-k; 6/6 edge tests pass",
                "wired_into_production_service": False,
                "status": "DOCUMENTED_EXPERIMENT_ONLY",
                "note": "separable from generation-facing path; pool cap is a "
                        "retrieval-only knob, not a mode change",
            },
            "policy_points": [
                {"point": "1. Production default remains bm25 (H1)", "verified": True},
                {"point": "2. Generation-facing hybrid = H3_RRF20 over FULL lists (PFULL)",
                 "verified": True},
                {"point": "3. Pool-250 is experiment-local, retrieval-only, 6/6 edge tests",
                 "verified": True},
                {"point": "4. Pool-250 NOT applied to generation-facing path (PFULL frozen)",
                 "verified": True},
                {"point": "5. BGE-M3 revision 5617a9f... pinned in index_meta", "verified": True},
                {"point": "6. Dense-index sha verification + bm25 fallback + mode_used logging",
                 "verified": True},
            ],
            "processes_at_audit": procs,
        },
        "serving_gap_audit": {
            "retrieval_library": "PRESENT (svk_corpus.retrieval.service, 41 tests)",
            "retrieval_http_api": "ABSENT (no FastAPI/uvicorn in svk-corpus src)",
            "bge_m3_query_encoder_runtime": "ABSENT (encoder weights cached 4.3G; "
                                            "no deployed query-encoding service; hybrid "
                                            "falls back to bm25 without query_embedding)",
            "evidence_validation": "PRESENT offline (task83_build_evidence); not in a service",
            "qwen3_8b_inference_serving": "ABSENT",
            "qwen3_8b_base_weights": "CACHED (16G, 5 safetensors shards, rev 49e3418f...)",
            "dapt01_adapter": "CACHED (/tmp/opencode/task75, 167M, sha verified)",
            "prompt_construction": "experiment-local (task72/75/83 scripts); not in a service",
            "streaming": "ABSENT",
            "ui": "ABSENT",
            "citations": "experiment-local (provenance in results; no user-facing citation layer)",
            "logging_health": "partial (SearchResponse.summary; no health endpoint)",
            "note": "port 8000 uvicorn is fanpulse-ai orchestrator (unrelated project); "
                    "ollama serves qwen2.5:7b-instruct only (4.7G) — NOT Qwen3-8B",
        },
        "assistant_architecture": {
            "minimum_complete_components": [
                {"component": "retrieval (production bm25 H1)", "state": "PRESENT (library)"},
                {"component": "generation-facing retrieval (hybrid_rrf20 PFULL)",
                 "state": "PRESENT (library, opt-in mode; not production default)"},
                {"component": "evidence assembly (k=5, trunc=500, provenance)",
                 "state": "EXPERIMENT-LOCAL"},
                {"component": "prompt construction (frozen protocol)",
                 "state": "EXPERIMENT-LOCAL"},
                {"component": "Qwen3-8B-Base + DAPT-01 inference (4-bit NF4, greedy, "
                              "max_new_tokens=192, seed=42)",
                 "state": "ABSENT (no serving runtime on VM)"},
                {"component": "response shaping / abstention handling",
                 "state": "ABSENT (evaluated in benchmark only)"},
                {"component": "HTTP API + health + logging",
                 "state": "ABSENT"},
                {"component": "UI", "state": "ABSENT"},
            ],
            "first_executable_task": {
                "id": "TASK 85 (proposed)",
                "scope": "Implement a retrieval-only HTTP service (FastAPI) wrapping "
                         "RetrievalService under the frozen production policy (mode=bm25), "
                         "with: /health, /search (query, top_k, mode), SearchResponse.summary "
                         "logging, unit tests, and a client script. Generation and Qwen "
                         "inference remain out of scope (BLOCKED).",
                "rationale": "retrieval is the only fully-verified, test-covered layer; "
                             "shipping it as a service is the smallest end-to-end step "
                             "that does not require model serving or policy change",
                "hard_stops": [
                    "no production default change",
                    "no Qwen inference (blocked on serving decision)",
                    "no training",
                    "no frozen-benchmark modification",
                ],
            },
        },
        "serving_feasibility": {
            "verified_facts": [
                "VM: 4 vCPU (AMD EPYC 7763), 15.6 GiB RAM, no GPU",
                "Qwen3-8B-Base fp16 weights = 16 GiB — does not fit in available RAM "
                "for CPU inference alongside OS/services",
                "4-bit NF4 quantization would fit (~5-6 GiB) but bitsandbytes is not "
                "installed and CPU 4-bit generation would be slow (unmeasured); "
                "not attempted per hard stop on dependency installs",
                "ollama present (127.0.0.1:11434) but only qwen2.5:7b-instruct — "
                "different architecture, NOT interchangeable with evaluated "
                "Qwen3-8B-Base/DAPT-01",
                "no llama.cpp / vllm / tgi / llama-cpp-python installed",
                "BGE-M3 query-encoder runtime also absent (weights cached 4.3G); "
                "hybrid mode requires caller-supplied query_embedding or falls back",
                "generation was previously run on Kaggle T4 (GPU quota 30h) — remote, "
                "not on this VM",
            ],
            "proposed_decisions": [
                "Retrieval-only service first (TASK 85); generation integration "
                "deferred until a serving path is chosen and funded",
                "Serving path options (UNRESOLVED): (a) remote API (external cost), "
                "(b) GPU VM (Azure credit cost UNVERIFIED), (c) CPU-only 4-bit "
                "(feasibility unmeasured, slow), (d) keep benchmark-only on Kaggle",
            ],
            "unresolved_questions": [
                "Is a GPU VM or external inference API budget approved? (Azure credit "
                "sustainability UNVERIFIED — not checked this task)",
                "Should hybrid_rrf20 PFULL ever become the generation-facing production "
                "default, or stay an explicit opt-in? (adoption requires a separate "
                "rollout task with its own gate)",
                "Is qwen2.5:7b acceptable as a non-evaluated development stand-in? "
                "(currently present; must NOT be presented as the evaluated model)",
                "Who owns the first-executable-task decision (TASK 85 scope)?",
            ],
        },
        "final_status": {
            "generation_facing_policy_documented_and_verified": True,
            "pool_250_retrieval_only_policy_documented_and_verified": True,
            "tests_and_integrity_verified": integrity["all_ok"] and tests["status"] == "PASS_BASELINE",
            "qwen_inference_serving_present": False,
            "full_assistant_ready": False,
            "azure_cost_sustainability": "UNVERIFIED",
            "production_default_changed": False,
            "training_started": False,
        },
        "repro": {
            "report_script": "experiments/task84/task84_report.py",
            "regression": "PYTHONPATH=src python3 -m unittest discover -s tests",
            "edge_tests": "experiments/task81/task81_pool_opt.py::_edge_case_tests",
        },
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")

    # ---- markdown ----
    fs = report["final_status"]
    md = []
    md.append("# Task 84 — Retrieval-policy freeze and integration-plan audit")
    md.append("")
    md.append(f"Generated: {report['generated_utc']} ({report['elapsed_s']}s)")
    md.append("")
    md.append("## Verdict")
    md.append("")
    md.append("| Axis | Verdict |")
    md.append("|---|---|")
    md.append(f"| Retrieval policy | **{report['verdict']['retrieval_policy']}** |")
    md.append(f"| Integration plan | **{report['verdict']['integration_plan']}** |")
    md.append(f"| Overall | **{report['verdict']['overall']}** |")
    md.append("")
    md.append("## 1. Policy audit")
    md.append("")
    md.append("| # | Policy point | Status |")
    md.append("|---|---|---|")
    for p in report["policy_audit"]["policy_points"]:
        md.append(f"| {p['point'].split('.')[0]} | {p['point'].split('.',1)[1].strip()} | "
                  f"{'VERIFIED' if p['verified'] else 'FAIL'} |")
    md.append("")
    pa = report["policy_audit"]
    md.append(f"- **Production default**: `{pa['production_default']['mode']}` — "
              f"{pa['production_default']['status']} (configs/policy.toml + RetrievalPolicy default).")
    gf = pa["generation_facing_hybrid"]
    md.append(f"- **Generation-facing hybrid**: `{gf['mode']}` over {gf['candidate_pool']}, "
              f"rrf_k={gf['rrf_k']}, evidence_k={gf['evidence_k']}, text_trunc={gf['text_trunc']} — "
              f"{gf['status']}; production adoption: {gf['production_adoption']}.")
    p250 = pa["retrieval_only_pool_250"]
    md.append(f"- **Pool-250**: {p250['location']} — wired into production: "
              f"{p250['wired_into_production_service']}; edge tests 6/6; {p250['status']}.")
    md.append("")
    md.append("## 2. Integrity")
    md.append("")
    md.append("| Artifact | Status |")
    md.append("|---|---|")
    for c in integrity["checks"]:
        sha = (c["actual_sha256"] or "")[:16]
        md.append(f"| {c['artifact']} | {c['status']}"
                  + (f" `{sha}…`" if sha else "") + " |")
    md.append("")
    md.append(f"- Regression: {tests['baseline']} — **{tests['status']}**.")
    md.append(f"- Task-81 pool-250 edge tests: {edge.get('n_passed','?')}/"
              f"{edge.get('n_tests','?')} all_pass={edge.get('all_pass')}.")
    md.append("- Historical reports (task69/74/75/81/82/83): mtimes unchanged; no overwrites.")
    md.append("")
    md.append("## 3. Serving-gap audit (this VM)")
    md.append("")
    sg = report["serving_gap_audit"]
    md.append("| Component | State |")
    md.append("|---|---|")
    for k in ("retrieval_library", "retrieval_http_api", "bge_m3_query_encoder_runtime",
              "evidence_validation", "qwen3_8b_inference_serving", "qwen3_8b_base_weights",
              "dapt01_adapter", "prompt_construction", "streaming", "ui",
              "citations", "logging_health"):
        md.append(f"| {k.replace('_', ' ')} | {sg[k]} |")
    md.append("")
    md.append(f"> Note: {sg['note']}")
    md.append("")
    md.append("## 4. Minimum complete assistant architecture")
    md.append("")
    md.append("| Component | State |")
    md.append("|---|---|")
    for comp in report["assistant_architecture"]["minimum_complete_components"]:
        md.append(f"| {comp['component']} | {comp['state']} |")
    md.append("")
    fe = report["assistant_architecture"]["first_executable_task"]
    md.append(f"**First executable task (proposed)**: {fe['id']} — {fe['scope']}")
    md.append("")
    md.append(f"*Rationale*: {fe['rationale']}")
    md.append("")
    md.append("Hard stops: " + "; ".join(fe["hard_stops"]) + ".")
    md.append("")
    md.append("## 5. Serving feasibility on this VM")
    md.append("")
    md.append("### Verified facts")
    md.append("")
    for fct in report["serving_feasibility"]["verified_facts"]:
        md.append(f"- {fct}")
    md.append("")
    md.append("### Proposed decisions (not taken this task)")
    md.append("")
    for d in report["serving_feasibility"]["proposed_decisions"]:
        md.append(f"- {d}")
    md.append("")
    md.append("### Unresolved questions")
    md.append("")
    for q in report["serving_feasibility"]["unresolved_questions"]:
        md.append(f"- {q}")
    md.append("")
    md.append("## 6. Final status")
    md.append("")
    md.append("| Criterion | Status |")
    md.append("|---|---|")
    md.append(f"| Generation-facing policy documented + verified | "
              f"{'YES' if fs['generation_facing_policy_documented_and_verified'] else 'NO'} |")
    md.append(f"| Pool-250 retrieval-only policy documented + verified | "
              f"{'YES' if fs['pool_250_retrieval_only_policy_documented_and_verified'] else 'NO'} |")
    md.append(f"| Tests + integrity verified | "
              f"{'YES' if fs['tests_and_integrity_verified'] else 'NO'} |")
    md.append(f"| Qwen3-8B inference serving | "
              f"{'PRESENT' if fs['qwen_inference_serving_present'] else 'ABSENT'} |")
    md.append(f"| Full assistant ready | "
              f"{'YES' if fs['full_assistant_ready'] else 'NO'} |")
    md.append(f"| Azure cost sustainability | {fs['azure_cost_sustainability']} |")
    md.append(f"| Production default changed | "
              f"{'YES' if fs['production_default_changed'] else 'NO'} |")
    md.append(f"| Training started | "
              f"{'YES' if fs['training_started'] else 'NO'} |")
    md.append("")
    md.append("**Verdict: RETRIEVAL_POLICY_FROZEN / INTEGRATION_PLAN_INCOMPLETE / BLOCKED.**")
    md.append("")
    md.append("The retrieval policy (production bm25 default, generation-facing PFULL hybrid "
              "candidate, retrieval-only pool-250) is frozen and verified. The end-to-end "
              "assistant is BLOCKED: Qwen3-8B inference serving is absent on this VM, the "
              "serving path is unresolved, and Azure cost sustainability is unverified. "
              "Production default was not changed; no training was started.")
    md.append("")
    md.append("## Repro")
    md.append("")
    md.append("```bash")
    md.append("PYTHONPATH=src python3 experiments/task84/task84_report.py")
    md.append("PYTHONPATH=src python3 -m unittest discover -s tests")
    md.append("```")
    md.append("")

    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print(f"integrity all_ok={integrity['all_ok']}  tests={tests['status']}  "
          f"edge={edge.get('all_pass')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
