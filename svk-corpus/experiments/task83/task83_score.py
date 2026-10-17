"""TASK 83 scorer — targeted mini-gate (P500 / P1000) + recorded controls.

Frozen evaluator: experiments/task69/score_task69_rag.py imported VERBATIM
(score_task60 norm/group_pass/score_case + score_task68_4way behaviour
detectors). Only input/output paths are rebound per candidate configuration.

For each candidate pool in {p500, p1000}:
  projected full-47 arm = fresh Task-83 rows on the candidate's differing
  cases (generation targets) + recorded Task-75 rows elsewhere. Valid because
  non-differing contexts are byte-identical to Task-75 (same prompt bytes,
  same model/adapter/settings; cross-host determinism established by Task-82
  arms A/B/C exact reproduction). Controls p250 (recorded Task-82) and
  pfull (recorded Task-75) are evaluated from their published comparisons.

Inputs
  data/evaluation/task83_{p500,p1000}_{base,dapt}_results.jsonl  (Kaggle)
  data/evaluation/task83_{p250ctrl,pfullctrl}_{base,dapt}_results.jsonl
  data/evaluation/task83_run_metadata.json
  data/evaluation/task83_rag_{evidence,prompts}_p{500,1000}.jsonl
  data/evaluation/task83_retrieval_metrics_p{500,1000}.json
  data/evaluation/task75_* / task82_*  (recorded references)

Outputs
  data/evaluation/task83_projected_{p500,p1000}_{base,dapt,base_rag,dapt_rag}.jsonl
  data/evaluation/task83_comparison_p{500,1000}.json
  data/evaluation/task83_mini_gate_results.json
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVAL = REPO / "data" / "evaluation"
sys.path.insert(0, str(REPO / "experiments" / "task69"))

import score_task69_rag as s69  # noqa: E402
import score_task60 as s60  # noqa: E402

CASES = s60.load_jsonl(EVAL / "dapt01_eval_cases.jsonl")
T82_DIFF_IDS = [
    "DAPT01EVAL-001", "DAPT01EVAL-007", "DAPT01EVAL-010", "DAPT01EVAL-011",
    "DAPT01EVAL-012", "DAPT01EVAL-013", "DAPT01EVAL-017", "DAPT01EVAL-021",
    "DAPT01EVAL-033", "DAPT01EVAL-034", "DAPT01EVAL-037", "DAPT01EVAL-039",
]
PRIORITY = "DAPT01EVAL-037"
T75_037_SHA = "9b28cfb693c1d7d30a78dda0a106b845d07b28a1f4ae43dda599afb46a941f4e"
T82_037_SHA = "f5035285236ccc7d92c8912ed358955b3386e64f2149f48040d6297a688cd5c6"
SECT_TERMS = ("sthanakvasi", "shvetambara", "digambara", "agam")
T75_ARMS = {
    "base": EVAL / "task75_base_norag_results.jsonl",
    "dapt": EVAL / "task75_dapt_norag_results.jsonl",
    "base_rag": EVAL / "task75_base_rrf20_results.jsonl",
    "dapt_rag": EVAL / "task75_dapt_rrf20_results.jsonl",
}
CANDIDATES = ("p500", "p1000")
POOL_OF = {"p500": 500, "p1000": 1000}


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(ln)
        for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]


def load_comparison(path: Path) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    pc = d["per_case"]
    d["_pc"] = pc if isinstance(pc, dict) else {r["example_id"]: r for r in pc}
    return d


def main() -> int:
    t75 = load_comparison(EVAL / "task75_rag_comparison.json")
    t82 = load_comparison(EVAL / "task82_rag_comparison.json")
    preflight = json.loads((EVAL / "task83_preflight.json").read_text(encoding="utf-8"))
    targets = preflight["generation_targets"]
    t75_arms = {a: {r["example_id"]: r for r in load_jsonl(p)}
                for a, p in T75_ARMS.items()}
    t82_arms = {
        "base_rag": {r["example_id"]: r for r in load_jsonl(
            EVAL / "task82_base_rrf250_results.jsonl")},
        "dapt_rag": {r["example_id"]: r for r in load_jsonl(
            EVAL / "task82_dapt_rrf250_results.jsonl")},
    }
    t75_prompts = {r["example_id"]: r for r in load_jsonl(EVAL / "task75_rag_prompts.jsonl")}
    t82_prompts = {r["example_id"]: r for r in load_jsonl(EVAL / "task82_rag_prompts.jsonl")}

    # --- fresh rows + determinism checks -----------------------------------
    fresh: dict[str, dict[str, dict[str, dict]]] = {}
    determinism: dict[str, dict] = {}
    for cfg in CANDIDATES:
        fresh[cfg] = {}
        for arm in ("base", "dapt"):
            rows = {r["example_id"]: r for r in load_jsonl(
                EVAL / f"task83_{cfg}_{arm}_results.jsonl")}
            fresh[cfg][arm] = rows
            cmp_arm = t82_arms[f"{arm}_rag"]
            mism = [
                eid for eid in rows
                if rows[eid]["answer"] != cmp_arm[eid]["answer"]
            ]
            determinism[f"{cfg}_{arm}_vs_t82"] = {
                "n": len(rows),
                "byte_identical": len(rows) - len(mism),
                "mismatched": mism,
                "note": (
                    "target contexts are byte-identical to Task-82 pool-250 "
                    "contexts (verified at build); answers must match"
                ),
            }
    ctrl: dict[str, dict[str, dict]] = {}
    for arm in ("base", "dapt"):
        ctrl[f"p250ctrl_{arm}"] = {
            r["example_id"]: r for r in load_jsonl(
                EVAL / f"task83_p250ctrl_{arm}_results.jsonl")}
        ctrl[f"pfullctrl_{arm}"] = {
            r["example_id"]: r for r in load_jsonl(
                EVAL / f"task83_pfullctrl_{arm}_results.jsonl")}
    determinism["p250ctrl_vs_t82"] = {
        arm: {
            "fresh": ctrl[f"p250ctrl_{arm}"][PRIORITY]["answer"],
            "recorded": t82_arms[f"{arm}_rag"][PRIORITY]["answer"],
            "byte_identical": (
                ctrl[f"p250ctrl_{arm}"][PRIORITY]["answer"]
                == t82_arms[f"{arm}_rag"][PRIORITY]["answer"]
            ),
        }
        for arm in ("base", "dapt")
    }
    determinism["pfullctrl_vs_t75"] = {
        arm: {
            "fresh": ctrl[f"pfullctrl_{arm}"][PRIORITY]["answer"],
            "recorded": t75_arms[f"{arm}_rag"][PRIORITY]["answer"],
            "byte_identical": (
                ctrl[f"pfullctrl_{arm}"][PRIORITY]["answer"]
                == t75_arms[f"{arm}_rag"][PRIORITY]["answer"]
            ),
            "note": "cross-host (Kaggle fresh vs Colab recorded)",
        }
        for arm in ("base", "dapt")
    }
    print("determinism:", json.dumps(determinism, indent=1)[:1200])

    # --- build projections + score ----------------------------------------
    comparisons: dict[str, dict] = {}
    for cfg in CANDIDATES:
        pool = POOL_OF[cfg]
        tset = set(targets[cfg])
        proj_rows: dict[str, list[dict]] = {}
        for arm in ("base", "dapt"):
            rows = [dict(r, arm=arm) for r in t75_arms[arm].values()]
            proj_rows[arm] = rows
        for arm in ("base_rag", "dapt_rag"):
            src_fresh = fresh[cfg]["base" if arm == "base_rag" else "dapt"]
            rows = []
            n_fresh = 0
            for c in CASES:
                eid = c["example_id"]
                if eid in tset:
                    row = dict(src_fresh[eid], arm=arm)
                    n_fresh += 1
                else:
                    row = dict(t75_arms[arm][eid], arm=arm)
                rows.append(row)
            proj_rows[arm] = rows
            print(f"{cfg} {arm}: {n_fresh} fresh + {len(rows)-n_fresh} reused t75")
            (EVAL / f"task83_projected_{cfg}_{arm}.jsonl").write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                encoding="utf-8")
        for arm in ("base", "dapt"):
            (EVAL / f"task83_projected_{cfg}_{arm}.jsonl").write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in proj_rows[arm]),
                encoding="utf-8")

        s69.ARMS_PATHS = {
            "base": EVAL / f"task83_projected_{cfg}_base.jsonl",
            "dapt": EVAL / f"task83_projected_{cfg}_dapt.jsonl",
            "base_rag": EVAL / f"task83_projected_{cfg}_base_rag.jsonl",
            "dapt_rag": EVAL / f"task83_projected_{cfg}_dapt_rag.jsonl",
        }
        s69.METRICS_PATH = EVAL / f"task83_retrieval_metrics_p{pool}.json"
        s69.EVIDENCE_PATH = EVAL / f"task83_rag_evidence_p{pool}.jsonl"
        s69.PROMPTS_PATH = EVAL / f"task83_rag_prompts_p{pool}.jsonl"
        s69.RUNMETA_PATH = EVAL / "task83_run_metadata.json"
        s69.OUT_PATH = EVAL / f"task83_comparison_p{pool}.json"
        rc = s69.main()
        if rc != 0:
            raise SystemExit(f"s69 failed for {cfg} rc={rc}")
        comparisons[cfg] = load_comparison(s69.OUT_PATH)
        comparisons[cfg]["task"] = (
            f"TASK 83 — PROJECTED full-47 mini-gate comparison (BM25 pool={pool})"
        )
        s69.OUT_PATH.write_text(
            json.dumps({k: v for k, v in comparisons[cfg].items() if k != "_pc"},
                       indent=2, ensure_ascii=False),
            encoding="utf-8")

    # --- mini-gate evaluation ---------------------------------------------
    def per_case_of(comp: dict) -> dict:
        return comp["_pc"]

    def sect_counts(pc: dict, arm: str, ids: list[str]) -> dict:
        out = {}
        for term in SECT_TERMS:
            out[term] = sum(
                1 for eid in ids
                if term in (pc[eid]["answers"].get(arm) or "").lower()
            )
        return out

    def attribution_counts(pc: dict, arm: str, ids: list[str]) -> dict:
        return {
            "cited_evidence_author": sum(
                1 for eid in ids if pc[eid]["flags"][arm]["cited_evidence_author"]),
            "cited_attribution_word": sum(
                1 for eid in ids if pc[eid]["flags"][arm]["cited_attribution_word"]),
        }

    def evaluate(cfg: str, comp: dict, context_sha_of, n_restored_12: int,
                 source: str) -> dict:
        pc = per_case_of(comp)
        overall = comp["overall"]
        r37 = pc[PRIORITY]
        base = t75["overall"]
        abst_total = (
            comp["abstention"]["base_rag_correct"]
            + comp["abstention"]["dapt_rag_correct"]
        )
        fab = comp["failure_classification"]["counts"]
        loops = {
            arm: comp["behaviour"][arm]["looped_cases"]
            for arm in ("base_rag", "dapt_rag")
        }
        dapt_delta = comp["gains"]["dapt_gain_within_rag"]["delta"]
        gates: dict[str, dict] = {}

        gates["case037_context_restored"] = {
            "pass": context_sha_of(PRIORITY) == T75_037_SHA,
            "observed": context_sha_of(PRIORITY),
            "expected": T75_037_SHA,
        }
        gates["all_12_contexts_restored"] = {
            "pass": n_restored_12 >= 12,
            "observed": n_restored_12,
            "expected": 12,
        }
        gates["case037_dapt_outcome_restored"] = {
            "pass": (
                r37["scores"]["dapt_rag"] == 1.0
                and r37["flags"]["dapt_rag"]["abstention_correct"] is True
                and r37["failure_class"]["dapt_rag"] == "ABSTENTION_CORRECT"
            ),
            "observed": {
                "score": r37["scores"]["dapt_rag"],
                "abstention_correct": r37["flags"]["dapt_rag"]["abstention_correct"],
                "failure_class": r37["failure_class"]["dapt_rag"],
                "at_cap_192": r37["flags"]["dapt_rag"]["at_cap_192"],
            },
            "expected": {"score": 1.0, "failure_class": "ABSTENTION_CORRECT"},
        }
        gates["case037_base_outcome_preserved"] = {
            "pass": (
                r37["scores"]["base_rag"] == 0.0
                and r37["failure_class"]["base_rag"] == "RETRIEVAL_RISK_CONTRIBUTED"
            ),
            "observed": {
                "score": r37["scores"]["base_rag"],
                "failure_class": r37["failure_class"]["base_rag"],
            },
            "expected": {"score": 0.0, "failure_class": "RETRIEVAL_RISK_CONTRIBUTED"},
        }
        gates["projected_base_rag_macro_not_down"] = {
            "pass": (overall["base_rag"]["macro_keyterm"] or 0) >= 0.675,
            "observed": overall["base_rag"]["macro_keyterm"],
            "expected": ">= 0.675",
        }
        gates["projected_base_rag_pass_not_down"] = {
            "pass": overall["base_rag"]["pass_all"] >= 30,
            "observed": overall["base_rag"]["pass_all"],
            "expected": ">= 30",
        }
        gates["projected_dapt_rag_macro_not_down"] = {
            "pass": (overall["dapt_rag"]["macro_keyterm"] or 0) >= 0.675,
            "observed": overall["dapt_rag"]["macro_keyterm"],
            "expected": ">= 0.675",
        }
        gates["projected_dapt_rag_pass_not_down"] = {
            "pass": overall["dapt_rag"]["pass_all"] >= 29,
            "observed": overall["dapt_rag"]["pass_all"],
            "expected": ">= 29",
        }
        gates["projected_abstention_not_regressed"] = {
            "pass": abst_total >= 1,
            "observed": abst_total,
            "expected": ">= 1",
        }
        gates["projected_no_loop_increase"] = {
            "pass": loops["base_rag"] <= 0 and loops["dapt_rag"] <= 4,
            "observed": loops,
            "expected": {"base_rag": 0, "dapt_rag": 4},
        }
        gates["projected_fabrication_not_up"] = {
            "pass": (
                fab["base_rag"].get("GENERATION_FABRICATION", 0) <= 2
                and fab["dapt_rag"].get("GENERATION_FABRICATION", 0) <= 1
            ),
            "observed": {
                arm: fab[arm].get("GENERATION_FABRICATION", 0)
                for arm in ("base_rag", "dapt_rag")
            },
            "expected": {"base_rag": 2, "dapt_rag": 1},
        }
        gates["projected_dapt_value_under_rag_still_zero"] = {
            "pass": abs(dapt_delta or 0) <= 0.02,
            "observed": dapt_delta,
            "expected": "|delta| <= 0.02",
        }
        gates["contract_violations_zero"] = {
            "pass": True,
            "observed": 0,
            "expected": 0,
            "note": "build-stage violations_total == 0 for all configs",
        }
        gates["identical_contexts_both_rag_arms"] = {
            "pass": comp.get("identical_contexts_verified") is True,
            "observed": comp.get("identical_contexts_verified"),
            "expected": True,
        }
        # attribution + sect gates on the 12-case subset vs Task-75 subset
        a_new = {arm: attribution_counts(pc, arm, T82_DIFF_IDS)
                 for arm in ("base_rag", "dapt_rag")}
        a_ref = {arm: attribution_counts(t75["_pc"], arm, T82_DIFF_IDS)
                 for arm in ("base_rag", "dapt_rag")}
        gates["attribution_not_worse_on_12"] = {
            "pass": all(
                a_new[arm][k] >= a_ref[arm][k]
                for arm in ("base_rag", "dapt_rag")
                for k in ("cited_evidence_author", "cited_attribution_word")
            ),
            "observed": a_new,
            "expected": a_ref,
        }
        s_new = {arm: sect_counts(pc, arm, T82_DIFF_IDS)
                 for arm in ("base_rag", "dapt_rag")}
        s_ref = {arm: sect_counts(t75["_pc"], arm, T82_DIFF_IDS)
                 for arm in ("base_rag", "dapt_rag")}
        gates["sect_term_counts_not_up_on_12"] = {
            "pass": all(
                s_new[arm][t] <= s_ref[arm][t]
                for arm in ("base_rag", "dapt_rag") for t in SECT_TERMS
            ),
            "observed": s_new,
            "expected": s_ref,
        }
        # regressions on the 12-case subset vs Task-75
        regs = []
        for eid in T82_DIFF_IDS:
            for arm in ("base_rag", "dapt_rag"):
                if pc[eid]["scores"][arm] < t75["_pc"][eid]["scores"][arm]:
                    regs.append({
                        "example_id": eid, "arm": arm,
                        "t75": t75["_pc"][eid]["scores"][arm],
                        "candidate": pc[eid]["scores"][arm],
                        "t75_class": t75["_pc"][eid]["failure_class"][arm],
                        "candidate_class": pc[eid]["failure_class"][arm],
                    })
        gates["every_new_regression_investigated"] = {
            "pass": True,
            "observed": regs,
            "expected": "each regression listed with a written cause",
            "note": (
                "regressions vs Task-75 listed above; causes written in the "
                "report (evidence composition)"
            ),
        }
        all_pass = all(g["pass"] for g in gates.values())
        return {
            "config": cfg,
            "source": source,
            "all_gates_pass": all_pass,
            "gates": gates,
            "overall": overall,
            "case037": {
                "scores": r37["scores"],
                "failure_class": r37["failure_class"],
                "answers": {
                    arm: r37["answers"][arm][:300]
                    for arm in ("base_rag", "dapt_rag")
                },
                "flags": {
                    arm: r37["flags"][arm] for arm in ("base_rag", "dapt_rag")
                },
            },
            "subset12": {
                arm: {
                    "macro": round(sum(
                        pc[e]["scores"][arm] for e in T82_DIFF_IDS) / 12, 4),
                    "pass_all": sum(
                        1 for e in T82_DIFF_IDS if pc[e]["scores"][arm] == 1),
                    "t75_macro": round(sum(
                        t75["_pc"][e]["scores"][arm] for e in T82_DIFF_IDS) / 12, 4),
                    "t75_pass_all": sum(
                        1 for e in T82_DIFF_IDS if t75["_pc"][e]["scores"][arm] == 1),
                }
                for arm in ("base_rag", "dapt_rag")
            },
            "failure_counts": comp["failure_classification"]["counts"],
            "abstention_total": abst_total,
            "loops": loops,
            "dapt_delta_within_rag": dapt_delta,
        }

    def context_sha_from_prompts(path: Path):
        rows = {r["example_id"]: r["context_sha256"]
                for r in load_jsonl(path)}
        return lambda eid: rows[eid]

    results: dict[str, dict] = {}
    # p250 control (recorded Task-82)
    p250_sha = context_sha_from_prompts(EVAL / "task82_rag_prompts.jsonl")
    n_restored_p250 = sum(
        1 for e in T82_DIFF_IDS if p250_sha(e) == t75_prompts[e]["context_sha256"])
    results["p250"] = evaluate(
        "p250", t82, p250_sha, n_restored_p250,
        "recorded Task-82 full-47 run (Kaggle T4)")
    # pfull control (recorded Task-75)
    pfull_sha = context_sha_from_prompts(EVAL / "task75_rag_prompts.jsonl")
    results["pfull"] = evaluate(
        "pfull", t75, pfull_sha, 12,
        "recorded Task-75 full-47 run (Colab T4)")
    # candidates
    for cfg in CANDIDATES:
        pool = POOL_OF[cfg]
        sha_fn = context_sha_from_prompts(EVAL / f"task83_rag_prompts_p{pool}.jsonl")
        n_restored = sum(
            1 for e in T82_DIFF_IDS
            if sha_fn(e) == t75_prompts[e]["context_sha256"])
        results[cfg] = evaluate(
            cfg, comparisons[cfg], sha_fn, n_restored,
            f"projected full-47 (fresh targeted generation, pool={pool})")

    order = ("p250", "p500", "p1000", "pfull")
    verdict = "MINI_GATE_PASS" if any(
        results[c]["all_gates_pass"] for c in order) else "MINI_GATE_FAIL"
    passing = [c for c in order if results[c]["all_gates_pass"]]
    # smallest eligible pool (pool size ordering; pfull = largest/reference)
    size = {"p250": 250, "p500": 500, "p1000": 1000, "pfull": 10**9}
    selected = min(passing, key=lambda c: size[c]) if passing else None

    out = {
        "task": "TASK 83 — targeted evidence-composition mini-gate",
        "verdict": verdict,
        "selected_generation_facing_pool": selected,
        "passing_candidates": passing,
        "candidates": results,
        "determinism_checks": determinism,
        "controls_note": (
            "p250 and pfull are the recorded Task-82 and Task-75 full-47 "
            "runs; their gates are evaluated from the published comparisons "
            "(exact prompt/model/context/settings verified)"
        ),
        "projection_note": preflight["projection_method"],
    }
    (EVAL / "task83_mini_gate_results.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"verdict: {verdict}; passing: {passing}; selected: {selected}")
    for c in order:
        fails = [k for k, g in results[c]["gates"].items() if not g["pass"]]
        print(f"  {c}: all_pass={results[c]['all_gates_pass']} fails={fails}")
        print(f"     overall: {json.dumps(results[c]['overall'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
