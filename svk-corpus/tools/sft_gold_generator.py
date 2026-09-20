#!/usr/bin/env python3
"""Generate final gold dataset from human review results.
Only HUMAN_VERIFIED examples enter the final gold dataset.
OpenCode cannot mark HUMAN_VERIFIED - only human review can.
"""
import os, json, sys
from collections import Counter

BASE_DIR = "/home/azureuser/jainLLM/svk-corpus"
GOLD_V1 = os.path.join(BASE_DIR, "data/training/sft_gold_v1.jsonl")
REVIEW_RESULTS = os.path.join(BASE_DIR, "data/training/sft_human_review_results_v1.jsonl")
GOLD_V2 = os.path.join(BASE_DIR, "data/training/sft_gold_v2.jsonl")
REJECTED_PATH = os.path.join(BASE_DIR, "data/training/sft_gold_rejected_v2.jsonl")

REQUIRED_FIELDS = [
    "example_id", "messages", "question_type", "source_ids", "source_units",
    "citations", "tradition", "lineage", "knowledge_layer", "content_role",
    "teacher", "agam_id", "practice", "language", "verification_status",
    "review_status",
]


def load_jsonl(path):
    items = []
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                try: items.append(json.loads(line.strip()))
                except: pass
    return items


def validate_gold_record(ex):
    issues = []
    for field in REQUIRED_FIELDS:
        if field not in ex:
            issues.append(f"missing:{field}")
    if not ex.get('source_ids'):
        issues.append("no_source_ids")
    if not ex.get('citations'):
        issues.append("no_citations")
    if not ex.get('messages') or len(ex.get('messages', [])) < 2:
        issues.append("insufficient_messages")
    return issues


def main():
    print("SFT GOLD DATASET GENERATOR")
    print("=" * 60)

    examples = {ex['example_id']: ex for ex in load_jsonl(GOLD_V1)}
    reviews = {r['example_id']: r for r in load_jsonl(REVIEW_RESULTS)}

    print(f"Gold candidates: {len(examples)}")
    print(f"Reviews received: {len(reviews)}")

    approved = []
    revised = []
    rejected = []
    pending = []

    for eid, ex in examples.items():
        r = reviews.get(eid)
        if not r:
            pending.append(eid)
            continue
        decision = r.get('decision', '')
        if decision == 'APPROVE':
            approved.append((ex, r))
        elif decision == 'REVISE':
            revised.append((ex, r))
        elif decision == 'REJECT':
            rejected.append((ex, r))
        else:
            pending.append(eid)

    print(f"\nReview results:")
    print(f"  APPROVE: {len(approved)}")
    print(f"  REVISE: {len(revised)}")
    print(f"  REJECT: {len(rejected)}")
    print(f"  PENDING: {len(pending)}")

    if pending:
        print(f"\nWARNING: {len(pending)} examples still pending review:")
        for eid in pending:
            print(f"  - {eid}")

    gold_v2 = []
    for ex, r in approved:
        gold_ex = ex.copy()
        gold_ex['review_status'] = 'HUMAN_VERIFIED'
        gold_ex['verification_status'] = 'SOURCE_GROUNDED'
        gold_ex['reviewer'] = r.get('reviewer', 'UNKNOWN')
        gold_ex['review_timestamp'] = r.get('review_timestamp', '')
        issues = validate_gold_record(gold_ex)
        if issues:
            print(f"  SKIP {gold_ex['example_id']}: {issues}")
            continue
        gold_v2.append(gold_ex)

    os.makedirs(os.path.dirname(GOLD_V2), exist_ok=True)
    with open(GOLD_V2, 'w', encoding='utf-8') as f:
        for ex in gold_v2:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    rejected_records = []
    for ex, r in rejected:
        rejected_records.append({
            "example_id": ex['example_id'],
            "rejection_reason": r.get('review_notes', ''),
            "reviewer": r.get('reviewer', 'UNKNOWN'),
            "review_timestamp": r.get('review_timestamp', ''),
        })
    for eid in pending:
        rejected_records.append({
            "example_id": eid,
            "rejection_reason": "PENDING_REVIEW",
            "reviewer": "NONE",
            "review_timestamp": "",
        })

    with open(REJECTED_PATH, 'w', encoding='utf-8') as f:
        for rec in rejected_records:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')

    print(f"\nFinal gold dataset: {GOLD_V2}")
    print(f"  HUMAN_VERIFIED examples: {len(gold_v2)}")
    print(f"Rejected: {REJECTED_PATH}")
    print(f"  Rejected records: {len(rejected_records)}")

    if gold_v2:
        cats = Counter(ex.get('knowledge_layer', '') for ex in gold_v2)
        teachers = Counter(ex.get('teacher', '') for ex in gold_v2 if ex.get('teacher'))
        practices = Counter(ex.get('practice', '') for ex in gold_v2 if ex.get('practice'))
        sth = Counter(ex.get('lineage', '') for ex in gold_v2)
        print(f"\nGold v2 distribution:")
        print(f"  Categories: {dict(cats)}")
        print(f"  Teachers: {dict(teachers)}")
        print(f"  Practices: {dict(practices)}")
        print(f"  STH status: {dict(sth)}")
    else:
        print("\nNo HUMAN_VERIFIED examples yet.")

    print(f"\nHARD STOP. No model training, no synthetic data.")


if __name__ == "__main__":
    main()
