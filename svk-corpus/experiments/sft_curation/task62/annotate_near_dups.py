#!/usr/bin/env python3
"""TASK 62 stage 1c: annotate the review queue with near-duplicate context.

Adds to every queue row:
  near_dup_count        - same-source sibling questions at Jaccard >= 0.85
  near_duplicates       - [{example_id, question, similarity}] for those siblings
  near_dup_cross_source - any other-source sibling at Jaccard >= 0.85 (leakage check)

Near duplicates are reported for human inspection only. Nothing is dropped here.
Idempotent: re-running recomputes the annotations from scratch.
"""
import itertools
import json
import os
import unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
QUEUE = os.path.join(ROOT, "data/training/sft_task62_review_queue_v1.jsonl")

THRESHOLD = 0.85
SHINGLE_K = 3


def norm(q):
    q = unicodedata.normalize("NFKC", q or "").lower()
    q = "".join(ch if ch.isalnum() else " " for ch in q)
    return " ".join(q.split())


def shingles(s, k=SHINGLE_K):
    s = s.replace(" ", "")
    if not s:
        return set()
    return {s[i:i + k] for i in range(max(1, len(s) - k + 1))}


def jac(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main():
    with open(QUEUE, encoding="utf-8") as fh:
        rows = [json.loads(l) for l in fh if l.strip()]

    qs = [norm(r["question"]) for r in rows]
    shs = [shingles(q) for q in qs]

    same = [[] for _ in rows]
    cross = [[] for _ in rows]
    for i, j in itertools.combinations(range(len(rows)), 2):
        v = jac(shs[i], shs[j])
        if v < THRESHOLD:
            continue
        a, b = rows[i], rows[j]
        same_side = a["source_id"] == b["source_id"]
        for src, dst in ((i, j), (j, i)):
            entry = {
                "example_id": rows[dst]["example_id"],
                "question": rows[dst]["question"],
                "similarity": round(v, 3),
                "same_source": same_side,
                "queue": rows[dst]["queue"],
            }
            (same if same_side else cross)[src].append(entry)

    for idx, row in enumerate(rows):
        sib = sorted(same[idx], key=lambda x: (-x["similarity"], x["example_id"]))
        row["near_dup_count"] = len(sib)
        row["near_duplicates"] = sib
        row["near_dup_cross_source"] = sorted(
            cross[idx], key=lambda x: (-x["similarity"], x["example_id"]))
        row.pop("near_dup_flag", None)

    with open(QUEUE, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    flagged = sum(1 for r in rows if r["near_dup_count"])
    cross_flagged = sum(1 for r in rows if r["near_dup_cross_source"])
    pairs = sum(r["near_dup_count"] for r in rows) // 2
    print("queue rows: %d" % len(rows))
    print("rows with same-source near-dups: %d (pairs=%d, threshold=%.2f)"
          % (flagged, pairs, THRESHOLD))
    print("rows with cross-source near-dups: %d" % cross_flagged)
    worst = sorted(rows, key=lambda r: -r["near_dup_count"])[:6]
    for r in worst:
        print("  %-38s %d siblings" % (r["example_id"], r["near_dup_count"]))


if __name__ == "__main__":
    main()
