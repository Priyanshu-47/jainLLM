"""TASK 68 held-out analysis: mechanical per-example audit of the 13 SFT-02 eval rows.

Inputs
  data/evaluation/sft02_eval_results.jsonl  (Task-68 generations, 13 rows)
  data/evaluation/sft_eval_v2.jsonl         (held-out rows + reference answers)
  data/training/sft_train_v2.jsonl          (61 train rows; template-carryover check)

Output
  data/evaluation/sft02_heldout_analysis.json

What is measured (all deterministic, documented; NOT accuracy scores)
  looped / infringement        — same uniform detector as score_task68_4way
  answer_len vs reference_len  — concision signal (SFT-01 target failure: median 851)
  reference_coverage           — fraction of reference content words (len>=4,
                                 ASCII stoplist removed) present in the answer.
                                 Heuristic lexical-overlap diagnostic ONLY; not
                                 an accuracy judgement (no rubric exists).
  opener                       — first sentence (template-rigidity signal)
  verbatim_train_openers       — answer's first sentence equals some train
                                 answer's first sentence (template carryover)
  abstention_row               — for the ABSTENTION row: marker hit +
                                 forbidden 4-digit year assertion (same marker
                                 spirit as the frozen abstention cases)
  tok_run_max                  — longest back-to-back repeated-token run
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EVAL = REPO / "data" / "evaluation"
TRAIN = REPO / "data" / "training" / "sft_train_v2.jsonl"

GEN_RESULTS = EVAL / "sft02_eval_results.jsonl"
EVAL_ROWS = EVAL / "sft_eval_v2.jsonl"
OUT_PATH = EVAL / "sft02_heldout_analysis.json"

STOP = set("""about above after again against all and any because been before being below between both
but can cannot could did do does doing down during each few for from further had has have having her here
hers herself him himself his how into its itself just more most not now off once only other our ours
ourselves out over own same she should so some such than that the their theirs them themselves then there
these they this those through under until very was were what when where which while who whom why will
with you your yours yourself yourselves""".split())


def looped(answer: str) -> bool:
    sents = [re.sub(r"\W+", " ", s).lower().strip()
             for s in re.split(r"[.!?।\n]", answer or "")]
    sents = [s for s in sents if len(s.split()) >= 4]
    if any(v >= 3 for v in Counter(sents).values()):
        return True
    toks = (answer or "").split()
    for k in range(1, 9):
        for i in range(len(toks) - k * 3 + 1):
            if toks[i:i + k] == toks[i + k:i + 2 * k] == toks[i + 2 * k:i + 3 * k]:
                if k > 1 or any(len(t) > 2 for t in toks[i:i + k]):
                    return True
    return False


def opener_of(answer: str) -> str:
    first = re.split(r"[.!?।\n]", answer or "", maxsplit=1)[0]
    return re.sub(r"\s+", " ", first).strip().lower()


def content_words(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-zA-Z']{4,}", (text or "").lower()):
        if w not in STOP:
            out.append(w)
    return out


def coverage(answer: str, reference: str) -> float | None:
    ref = content_words(reference)
    if not ref:
        return None
    a = (answer or "").lower()
    hit = sum(1 for w in set(ref) if w in a)
    return round(hit / len(set(ref)), 4)


def tok_run_max(answer: str) -> int:
    toks = (answer or "").split()
    run = best = 1 if toks else 0
    for i in range(1, len(toks)):
        run = run + 1 if toks[i] == toks[i - 1] else 1
        best = max(best, run)
    return best


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def main() -> int:
    gens = {r["example_id"]: r for r in load_jsonl(GEN_RESULTS)}
    refs = {r["example_id"]: r for r in load_jsonl(EVAL_ROWS)}
    train = load_jsonl(TRAIN)
    train_openers = {opener_of(r["messages"][-1]["content"]) for r in train}

    if len(gens) != 13 or len(refs) != 13:
        raise SystemExit(f"expected 13 rows, got gens={len(gens)} refs={len(refs)}")
    if set(gens) != set(refs):
        raise SystemExit("generation ids do not match eval rows")

    per_row = []
    for eid, ref_row in refs.items():
        g = gens[eid]
        answer = g["answer"]
        reference = ref_row["answer"]
        cat = ref_row.get("category", "")
        is_abst = "ABSTENTION" in cat.upper()
        entry = {
            "example_id": eid,
            "category": cat,
            "language": ref_row.get("language"),
            "source_id": ref_row.get("source_id"),
            "question": ref_row["question"],
            "reference_answer": reference,
            "answer": answer,
            "looped": looped(answer),
            "infringement": "INFRINGEMENT" in answer,
            "answer_len_chars": len(answer),
            "reference_len_chars": len(reference),
            "len_ratio": round(len(answer) / max(len(reference), 1), 3),
            "reference_coverage": coverage(answer, reference),
            "opener": opener_of(answer),
            "verbatim_train_opener": opener_of(answer) in train_openers,
            "tok_run_max": tok_run_max(answer),
            "new_tokens": g.get("new_tokens"),
            "prompt_style": g.get("prompt_style"),
            "is_abstention_row": is_abst,
        }
        if is_abst:
            a_low = answer.lower()
            markers = ["not stated", "unknown", "not available", "cannot", "can't",
                       "unable", "do not know", "don't know", "not mentioned",
                       "not given", "insufficient", "no information", "not recorded",
                       "not specified", "does not state", "doesn't state", "unclear"]
            year_hits = re.findall(r"\b(?:17|18|19|20)\d{2}\b", answer)
            entry["abstention_marker_hit"] = any(m in a_low for m in markers)
            entry["abstention_year_assertions"] = year_hits
            entry["abstention_row_passed_mechanical"] = bool(
                entry["abstention_marker_hit"]) and not year_hits
        per_row.append(entry)

    lens = [r["answer_len_chars"] for r in per_row]
    covs = [r["reference_coverage"] for r in per_row if r["reference_coverage"] is not None]
    ratios = [r["len_ratio"] for r in per_row]
    openers = [r["opener"] for r in per_row]
    mode_op, mode_n = Counter(openers).most_common(1)[0]
    abst_entries = [r for r in per_row if r["is_abstention_row"]]

    analysis = {
        "task": "TASK 68 — SFT-02 held-out (sft_eval_v2, 13 rows) mechanical analysis",
        "artifacts": {
            "generations": str(GEN_RESULTS.relative_to(REPO)),
            "eval_rows": str(EVAL_ROWS.relative_to(REPO)),
            "train_rows": str(TRAIN.relative_to(REPO)),
        },
        "method_note": (
            "All fields are deterministic lexical/structural diagnostics. "
            "reference_coverage is a heuristic content-word overlap, NOT an accuracy "
            "score: the held-out rows carry no scoring rubric (same situation as "
            "sft_eval_v1 in Task 65). Quality judgements on these rows are "
            "NOT_MEASURED; the 47-case frozen benchmark remains the behavioural "
            "benchmark. Task-65's sft_eval_v1 cannot be compared row-by-row with "
            "sft_eval_v2 (different rows): cross-SFT comparisons use the frozen set."
        ),
        "n_rows": len(per_row),
        "aggregate": {
            "answer_len_median": int(statistics.median(lens)),
            "answer_len_mean": round(statistics.mean(lens), 1),
            "answer_len_max": max(lens),
            "reference_len_median": int(statistics.median([r["reference_len_chars"] for r in per_row])),
            "len_ratio_median": round(statistics.median(ratios), 3),
            "len_ratio_max": max(ratios),
            "reference_coverage_mean": round(statistics.mean(covs), 4) if covs else None,
            "reference_coverage_min": min(covs) if covs else None,
            "looped_rows": sum(1 for r in per_row if r["looped"]),
            "infringement_rows": sum(1 for r in per_row if r["infringement"]),
            "verbatim_train_opener_rows": sum(1 for r in per_row if r["verbatim_train_opener"]),
            "tok_run_max": max(r["tok_run_max"] for r in per_row),
            "mode_opener": mode_op,
            "mode_opener_count": mode_n,
            "mode_opener_share": round(mode_n / len(per_row), 4),
            "distinct_openers": len(set(openers)),
            "prompt_styles": sorted({r["prompt_style"] for r in per_row}),
            "total_new_tokens": sum(r["new_tokens"] or 0 for r in per_row),
        },
        "abstention_row": [
            {k: r[k] for k in ("example_id", "question", "answer",
                               "abstention_marker_hit", "abstention_year_assertions",
                               "abstention_row_passed_mechanical")}
            for r in abst_entries
        ],
        "per_row": per_row,
        "not_measured": [
            "accuracy/correctness of held-out answers (no rubric): NOT_MEASURED",
            "grammar/fluency: NOT_MEASURED",
            "row-by-row comparison with SFT-01 (sft_eval_v1 rows differ): NOT_COMPARABLE",
        ],
    }
    OUT_PATH.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT_PATH.relative_to(REPO)} ({len(per_row)} rows)")
    print("aggregate:", json.dumps(analysis["aggregate"]))
    for r in abst_entries:
        print("abstention row:", r["example_id"], "marker=", r["abstention_marker_hit"],
              "years=", r["abstention_year_assertions"],
              "pass=", r["abstention_row_passed_mechanical"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
