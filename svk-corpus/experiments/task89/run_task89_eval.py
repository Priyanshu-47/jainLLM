"""Task 89 — evidence-grounded generation evaluation (smoke subset).

Reads a small, clearly-labelled SUBSET of the frozen DAPT-01 evaluation
cases READ-ONLY (the benchmark file is never modified) and runs the
experimental ``AnswerService`` (production BM25 retrieval + local Ollama
``qwen2.5:7b-instruct``) against each question.

Metrics per case (kept separate, never collapsed into one number):
  * objective_score          frozen keyword-rule score (score_task60 logic,
                             imported read-only — the frozen module is not
                             modified or re-run over historical files)
  * citation_validity        all cited ids belonged to supplied evidence
  * citation_present         at least one valid citation
  * evidence_support_ratio   content-word overlap of answer vs supplied
                             evidence (lexical proxy for factual support)
  * abstention_correct       abstention behaviour vs ``abstention_case``
  * sect_mention_flags       tradition terms in the answer that do not
                             appear in the supplied evidence/metadata
                             (potential attribution issues, for review)
  * latency                  retrieval / generation / total, separately

Outputs (new files only):
  data/reports/task89_generation_eval.json   machine-readable results
  experiments/task89/task89_case_outputs.jsonl  raw answers + prompts

Run:
  cd svk-corpus && PYTHONPATH=src .venv/bin/python \
      experiments/task89/run_task89_eval.py
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from svk_corpus.generation.answer import AnswerService  # noqa: E402

CASES_PATH = REPO / "data" / "evaluation" / "dapt01_eval_cases.jsonl"
FROZEN_SCORER = (REPO / "experiments" / "dapt_01" / "evaluation"
                 / "score_task60.py")
OUT_JSON = REPO / "data" / "reports" / "task89_generation_eval.json"
OUT_RAW = REPO / "experiments" / "task89" / "task89_case_outputs.jsonl"

# Representative subset: 5 categories + both abstention behaviours.
SUBSET_IDS = [
    "DAPT01EVAL-001",   # JAIN_TERMINOLOGY (ahimsa)
    "DAPT01EVAL-002",   # JAIN_TERMINOLOGY (karma)
    "DAPT01EVAL-024",   # AGAM_GROUNDED (Aavashyak mool number)
    "DAPT01EVAL-028",   # STHANAKAVASI_DISTINCTION (sect attribution)
    "DAPT01EVAL-034",   # SOURCE_ATTRIBUTION (author)
    "DAPT01EVAL-036",   # ABSTENTION expected (publication year)
    "DAPT01EVAL-037",   # ABSTENTION expected (founding year, hard case)
    "DAPT01EVAL-040",   # PRACTICE (samayika duration)
]

TRADITION_TERMS = [
    "sthānakavāsī", "sthānakavāsi", "sthankavasi", "stanakavasi",
    "svetambara", "śvetāmbara", "shvetambar", "svetembar",
    "digambara", "digambar", "terapanth", "agam", "agama",
    "jain", "jaina", "jaina",
]

_WORD_RE = re.compile(r"[a-zāīūṛṝḷṅñṭḍṇśṣé'’-]{4,}")
_SENT_RE = re.compile(r"(?<=[.!?])\s+")
_CITE_RE = re.compile(r"\[E\d+(?:\s*,\s*E\d+)*\]")


def load_frozen_scorer():
    spec = importlib.util.spec_from_file_location("task89_frozen_scorer",
                                                  FROZEN_SCORER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def content_words(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall((text or "").lower())}


def evidence_support_ratio(answer: str, evidence: list[dict]) -> float:
    """Fraction of answer content words present in the supplied evidence."""
    aw = content_words(answer)
    if not aw:
        return 0.0
    ev = " ".join(e["text"] + " " + e["title"] + " " + e["citation"]
                  for e in evidence)
    ew = content_words(ev)
    return round(len(aw & ew) / len(aw), 4)


def uncited_sentences(answer: str) -> list[str]:
    out = []
    for sent in _SENT_RE.split(answer.strip()):
        s = sent.strip()
        if len(s) < 25 or s.upper().startswith("ABSTAIN"):
            continue
        if not _CITE_RE.search(s):
            out.append(s[:160])
    return out


def sect_mention_flags(answer: str, evidence: list[dict]) -> dict:
    a = (answer or "").lower()
    ev_blob = " ".join(
        e["text"] + " " + e["title"] + " " + e["sect"] + " "
        + e["religious_scope"] + " " + e["knowledge_layer"] for e in evidence
    ).lower()
    in_answer = sorted({t for t in TRADITION_TERMS if t in a})
    unsupported = [t for t in in_answer if t not in ev_blob]
    return {"tradition_terms_in_answer": in_answer,
            "terms_absent_from_evidence": unsupported,
            "flag": bool(unsupported)}


def main() -> int:
    if not CASES_PATH.exists():
        raise SystemExit(f"frozen benchmark missing: {CASES_PATH}")
    scorer = load_frozen_scorer()
    cases = {json.loads(l)["example_id"]: json.loads(l)
             for l in CASES_PATH.read_text(encoding="utf-8").splitlines()
             if l.strip()}
    missing = [i for i in SUBSET_IDS if i not in cases]
    if missing:
        raise SystemExit(f"subset ids missing from benchmark: {missing}")

    t0 = time.perf_counter()
    svc = AnswerService.from_repo(REPO)
    init_s = time.perf_counter() - t0
    print(f"[eval] service ready in {init_s:.1f}s "
          f"mode={svc.retrieval_mode} model={svc.provider.model}")

    per_case = []
    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    with OUT_RAW.open("w", encoding="utf-8") as raw_f:
        for eid in SUBSET_IDS:
            case = cases[eid]
            q = case["question"]
            t_q = time.perf_counter()
            res = svc.answer(q)
            wall = time.perf_counter() - t_q
            d = res.to_dict()

            frozen = scorer.score_case(case, res.answer) if res.answer else {
                "objective_score": 0.0, "group_passes": [],
                "groups_satisfied": "0/0", "abstention_detected": False}
            abstain_expected = bool(case.get("abstention_case"))
            abstention_correct = (res.abstained == abstain_expected) or (
                abstain_expected and bool(frozen.get("abstention_detected")))

            rec = {
                "example_id": eid,
                "category": case["category"],
                "question": q,
                "expected_answer_or_reference": case["expected_answer_or_reference"],
                "abstention_expected": abstain_expected,
                "answer": res.answer,
                "abstained": res.abstained,
                "abstention_reason": res.abstention_reason,
                "error": res.error,
                "citations": res.citations,
                "invalid_citations": res.invalid_citations,
                "citation_valid": res.citations_valid,
                "citation_present": bool(res.citations),
                "citation_map": res.citation_map,
                "evidence_ids": [e["text_id"] for e in res.evidence],
                "evidence_source_ids": [e["source_id"] for e in res.evidence],
                "evidence_sect": [e["sect"] for e in res.evidence],
                "objective_score": frozen.get("objective_score"),
                "groups_satisfied": frozen.get("groups_satisfied"),
                "abstention_detected_by_markers":
                    bool(frozen.get("abstention_detected")),
                "abstention_correct": bool(abstention_correct),
                "evidence_support_ratio":
                    evidence_support_ratio(res.answer, res.evidence),
                "uncited_sentences": uncited_sentences(res.answer),
                "sect_flags": sect_mention_flags(res.answer, res.evidence),
                "retrieval_mode": res.retrieval_mode,
                "model": res.model,
                "latency": {
                    "retrieval_s": d["retrieval_latency_s"],
                    "generation_s": d["generation_latency_s"],
                    "total_s": d["total_latency_s"],
                    "wall_s": round(wall, 3),
                },
                "eval_count": res.eval_count,
                "warnings": res.warnings,
            }
            per_case.append(rec)
            raw_f.write(json.dumps({"example_id": eid, **d,
                                    "prompt_question": q},
                                   ensure_ascii=False) + "\n")
            print(f"[eval] {eid} {case['category'][:22]:22s} "
                  f"score={rec['objective_score']} "
                  f"cit={'Y' if rec['citation_valid'] else 'N'} "
                  f"abstain={res.abstained}/{abstain_expected} "
                  f"sup={rec['evidence_support_ratio']} "
                  f"lat={rec['latency']['total_s']}s "
                  f"err={res.error or '-'}")

    n = len(per_case)
    scored = [r for r in per_case if r["objective_score"] is not None]
    agg = {
        "n_cases": n,
        "n_errors": sum(1 for r in per_case if r["error"]),
        "objective_mean": round(
            sum(r["objective_score"] for r in scored) / len(scored), 4)
        if scored else None,
        "objective_full_pass": sum(1 for r in per_case
                                  if r["objective_score"] == 1.0),
        "citation_valid_rate": round(sum(1 for r in per_case
                                         if r["citation_valid"]) / n, 4),
        "citation_present_rate": round(sum(1 for r in per_case
                                           if r["citation_present"]) / n, 4),
        "abstention_correct_rate": round(sum(1 for r in per_case
                                             if r["abstention_correct"]) / n, 4),
        "abstentions": sum(1 for r in per_case if r["abstained"]),
        "abstention_expected_count": sum(1 for r in per_case
                                         if r["abstention_expected"]),
        "support_ratio_mean": round(
            sum(r["evidence_support_ratio"] for r in per_case) / n, 4),
        "sect_flags_count": sum(1 for r in per_case if r["sect_flags"]["flag"]),
        "answers_with_uncited_sentences": sum(
            1 for r in per_case if r["uncited_sentences"]),
        "latency": {
            "retrieval_mean_s": round(
                sum(r["latency"]["retrieval_s"] for r in per_case) / n, 4),
            "generation_mean_s": round(
                sum(r["latency"]["generation_s"] for r in per_case) / n, 3),
            "total_mean_s": round(
                sum(r["latency"]["total_s"] for r in per_case) / n, 3),
            "total_max_s": max(r["latency"]["total_s"] for r in per_case),
        },
    }

    report = {
        "task": "task89",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "label": ("SMOKE SUBSET — not a validated benchmark; 8/47 frozen "
                  "cases chosen for category coverage"),
        "model": {
            "id": svc.provider.model,
            "endpoint": svc.provider.endpoint,
            "num_predict": svc.provider.config.num_predict,
            "num_ctx": svc.provider.config.num_ctx,
            "temperature": svc.provider.config.temperature,
            "timeout_s": svc.provider.config.timeout_s,
            "runtime": "local Ollama on CPU (4 vCPU), no external API",
        },
        "retrieval": {
            "mode": svc.retrieval_mode,
            "evidence_k": svc.evidence_k,
            "text_trunc": svc.text_trunc,
            "service_init_s": round(init_s, 2),
        },
        "benchmark": {
            "path": str(CASES_PATH.relative_to(REPO)),
            "subset_ids": SUBSET_IDS,
            "read_only": True,
        },
        "aggregate": agg,
        "per_case": per_case,
        "limitations": [
            "8 of 47 frozen cases; single run; no human adjudication.",
            "evidence_support_ratio is a lexical overlap proxy, not a factual-"
            "correctness judgement; uncited_sentences is sentence-level.",
            "sect_flags are heuristic prompts for review, not verified errors.",
            "Latency measured on a shared CPU VM; warm/cold model state varies.",
            "Keyword objective_score inherits the frozen scorer's term-matching "
            "semantics (it is not a model-based judgement).",
        ],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    print(f"\n[eval] wrote {OUT_JSON.relative_to(REPO)}")
    print(f"[eval] wrote {OUT_RAW.relative_to(REPO)}")
    print(f"[eval] aggregate: {json.dumps(agg, indent=2)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
