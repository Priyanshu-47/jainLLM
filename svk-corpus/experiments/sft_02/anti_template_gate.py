"""TASK 67 Phase 5: anti-repetition / anti-template concentration gate.

Measures (does not blanket-ban):
  1. exact answer duplicates
  2. near-duplicate answers (shingle Jaccard)
  3. repeated opening phrases (first 3 and first 4 normalised words)
  4. repeated sentence templates (normalised sentence skeletons)
  5. repeated word n-grams across answers
  6. category-specific template concentration

"The manifest records" is measured as a specific phrase: it may legitimately
occur when describing metadata, but must not dominate the dataset.

Exit codes / levels: PASS < WARN < FAIL. A WARN is reported but does not
block the build; a FAIL raises.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

from sft02_common import fold, norm_ws, read_jsonl, shingles, jaccard

# --- thresholds (documented in the Task-67 report) -------------------------
MAX_EXACT_DUP_ANSWERS = 0
MAX_NEAR_DUP_PAIRS = 0
OPENER_PHRASE_WARN = 0.10        # first-3-word phrase share
OPENER_PHRASE_FAIL = 0.15
MANIFEST_RECORDS_FAIL = 0.15     # exact "the manifest records" opener share
MANIFEST_RECORDS_WARN = 0.10
SENT_TEMPLATE_WARN = 0.10        # single normalised sentence skeleton share
SENT_TEMPLATE_FAIL = 0.20
TOP5_SENT_TEMPLATE_FAIL = 0.35   # combined share of the 5 commonest skeletons
NGRAM_WARN = 0.20                # any 8-gram present in this share of rows
NGRAM_FAIL = 0.35
CATEGORY_OPENER_FAIL = 0.60      # within one category
CATEGORY_OPENER_WARN = 0.40
MIN_CAT_N = 4                    # concentration is meaningless below this n



def norm_opener(answer: str, n: int = 3) -> str:
    words = re.sub(r"[^\w\s]", " ", norm_ws(answer).lower()).split()
    return " ".join(words[:n])


def sentence_template(sentence: str) -> str:
    """Skeleton of a sentence: quoted spans collapsed, digits->#, lowercased."""
    s = norm_ws(sentence)
    s = re.sub(r"[\"“'][^\"”']+[\"”']", '"QUOTE"', s)
    s = re.sub(r"\d+", "#", s)
    s = re.sub(r"\b(?:[A-Z][a-z]+)\b", "NAME", s)  # likely titles/proper nouns
    return re.sub(r"\s+", " ", s).strip().lower()


def _split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?।॥])\s+|\n+", text)
    return [norm_ws(p) for p in parts if norm_ws(p)]


def _flag(report: dict, level: str, msg: str) -> None:
    report["flags"].append(f"[{level}] {msg}")


def measure(rows: List[dict]) -> dict:
    answers = [str(r.get("answer") or "") for r in rows]
    n = len(answers)
    report: Dict[str, dict] = {"n_rows": n, "flags": [], "level": "PASS"}

    # 1. exact duplicates
    counts = Counter(fold(a) for a in answers)
    exact_dups = {k: v for k, v in counts.items() if v > 1}
    report["exact_duplicate_answers"] = len(exact_dups)
    if len(exact_dups) > MAX_EXACT_DUP_ANSWERS:
        _flag(report, "FAIL", f"exact duplicate answers: {len(exact_dups)}")

    # 2. near-duplicate answers
    sh = [shingles(a) for a in answers]
    near_pairs = []
    for i in range(len(answers)):
        for j in range(i + 1, len(answers)):
            if jaccard(sh[i], sh[j]) >= 0.80:
                near_pairs.append((rows[i].get("example_id"), rows[j].get("example_id")))
    report["near_duplicate_pairs"] = len(near_pairs)
    report["near_duplicate_examples"] = near_pairs[:10]
    if len(near_pairs) > MAX_NEAR_DUP_PAIRS:
        _flag(report, "FAIL", f"near-duplicate answer pairs: {len(near_pairs)}")

    # 3. opening phrases
    open3 = Counter(norm_opener(a, 3) for a in answers)
    open4 = Counter(norm_opener(a, 4) for a in answers)
    top3, top3c = open3.most_common(1)[0] if open3 else ("", 0)
    report["top_opener_phrase_3w"] = {"phrase": top3, "count": top3c,
                                      "share": round(top3c / n, 4) if n else 0.0}
    report["opener_phrase_counts_3w"] = dict(open3.most_common(8))
    share3 = top3c / n if n else 0.0
    if share3 > OPENER_PHRASE_FAIL:
        _flag(report, "FAIL", f"opener phrase '{top3}' share {share3:.1%} > {OPENER_PHRASE_FAIL:.0%}")
    elif share3 > OPENER_PHRASE_WARN:
        _flag(report, "WARN", f"opener phrase '{top3}' share {share3:.1%} > warn {OPENER_PHRASE_WARN:.0%}")

    tmr = sum(1 for a in answers if norm_opener(a, 3) == "the manifest records")
    report["manifest_records_opener"] = {"count": tmr, "share": round(tmr / n, 4) if n else 0.0}
    if n and tmr / n > MANIFEST_RECORDS_FAIL:
        _flag(report, "FAIL", f"'The manifest records' opener share {tmr/n:.1%} > {MANIFEST_RECORDS_FAIL:.0%}")
    elif n and tmr / n > MANIFEST_RECORDS_WARN:
        _flag(report, "WARN", f"'The manifest records' opener share {tmr/n:.1%} > warn {MANIFEST_RECORDS_WARN:.0%}")

    # 4. sentence templates
    sent_counter: Counter = Counter()
    rows_per_sent: Dict[str, set] = defaultdict(set)
    for idx, a in enumerate(answers):
        for s in _split_sentences(a):
            if len(s.split()) < 5:
                continue
            tpl = sentence_template(s)
            if len(tpl.split()) < 5:
                continue
            sent_counter[tpl] += 1
            rows_per_sent[tpl].add(rows[idx].get("example_id"))
    top_tpls = sent_counter.most_common(8)
    report["top_sentence_templates"] = [
        {"template": t[:110], "rows": len(rows_per_sent[t])} for t, _ in top_tpls
    ]
    worst_tpl, worst_rows = (top_tpls[0][0], len(rows_per_sent[top_tpls[0][0]])) if top_tpls else ("", 0)
    worst_share = worst_rows / n if n else 0.0
    top5_rows = sum(len(rows_per_sent[t]) for t, _ in top_tpls[:5])
    top5_share = top5_rows / n if n else 0.0
    report["worst_sentence_template"] = {"template": worst_tpl[:140], "rows": worst_rows,
                                         "share": round(worst_share, 4)}
    report["top5_sentence_template_share"] = round(top5_share, 4)
    if worst_share > SENT_TEMPLATE_FAIL:
        _flag(report, "FAIL", f"sentence template share {worst_share:.1%} > {SENT_TEMPLATE_FAIL:.0%}")
    elif worst_share > SENT_TEMPLATE_WARN:
        _flag(report, "WARN", f"sentence template share {worst_share:.1%} > warn {SENT_TEMPLATE_WARN:.0%}")
    if top5_share > TOP5_SENT_TEMPLATE_FAIL:
        _flag(report, "FAIL", f"top-5 sentence template combined share {top5_share:.1%} > {TOP5_SENT_TEMPLATE_FAIL:.0%}")

    # 5. word n-grams (8-gram) across answers
    ngram_rows: Dict[str, set] = defaultdict(set)
    for idx, a in enumerate(answers):
        words = re.sub(r"[^\w\s]", " ", norm_ws(a).lower()).split()
        seen = set()
        for i in range(max(0, len(words) - 7)):
            g = " ".join(words[i:i + 8])
            if g in seen:
                continue
            seen.add(g)
            ngram_rows[g].add(rows[idx].get("example_id"))
    top_ngrams = sorted(ngram_rows.items(), key=lambda kv: -len(kv[1]))[:8]
    report["top_ngrams_8"] = [{"ngram": g, "rows": len(s)} for g, s in top_ngrams]
    if n:
        worst_g, worst_gs = (top_ngrams[0] if top_ngrams else ("", set()))
        worst_g_share = len(worst_gs) / n
        report["worst_8gram"] = {"ngram": worst_g, "rows": len(worst_gs), "share": round(worst_g_share, 4)}
        if worst_g_share > NGRAM_FAIL:
            _flag(report, "FAIL", f"8-gram share {worst_g_share:.1%} > {NGRAM_FAIL:.0%}")
        elif worst_g_share > NGRAM_WARN:
            _flag(report, "WARN", f"8-gram share {worst_g_share:.1%} > warn {NGRAM_WARN:.0%}")

    # 6. category-specific opener concentration
    by_cat: Dict[str, List[str]] = defaultdict(list)
    for r, a in zip(rows, answers):
        by_cat[str(r.get("category") or "UNKNOWN")].append(a)
    cat_report = {}
    for cat, cat_answers in sorted(by_cat.items()):
        cn = len(cat_answers)
        cat_open = Counter(norm_opener(a, 3) for a in cat_answers)
        phrase, c = cat_open.most_common(1)[0] if cat_open else ("", 0)
        share = c / cn if cn else 0.0
        cat_report[cat] = {"n": cn, "top_opener": phrase, "count": c, "share": round(share, 4)}
        if cn < MIN_CAT_N:
            cat_report[cat]["exempt"] = f"n < {MIN_CAT_N}"
            continue
        if share > CATEGORY_OPENER_FAIL:
            _flag(report, "FAIL", f"category {cat}: opener '{phrase}' share {share:.1%} > {CATEGORY_OPENER_FAIL:.0%}")
        elif share > CATEGORY_OPENER_WARN:
            _flag(report, "WARN", f"category {cat}: opener '{phrase}' share {share:.1%} > warn {CATEGORY_OPENER_WARN:.0%}")
    report["category_opener_concentration"] = cat_report

    # level
    level = "FAIL" if any(f.startswith("[FAIL]") for f in report["flags"]) \
        else ("WARN" if report["flags"] else "PASS")
    report["level"] = level
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="anti-template concentration gate")
    ap.add_argument("files", nargs="+", help="jsonl dataset files")
    ap.add_argument("--json", action="store_true", help="print full report as JSON")
    args = ap.parse_args(argv)
    rows: List[dict] = []
    for f in args.files:
        rows.extend(read_jsonl(f))
    rep = measure(rows)
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print(f"rows={rep['n_rows']} level={rep['level']}")
        for k in ("exact_duplicate_answers", "near_duplicate_pairs", "top_opener_phrase_3w",
                  "manifest_records_opener", "worst_sentence_template",
                  "top5_sentence_template_share", "worst_8gram"):
            print(f"  {k}: {rep[k]}")
        for f in rep["flags"]:
            print(f"  FLAG: {f}")
    return 1 if rep["level"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
