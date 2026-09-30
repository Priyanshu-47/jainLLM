#!/usr/bin/env python3
"""TASK 62 stage 1: build the human review queue from the Task 61 candidate pool.

Produces data/training/sft_task62_review_queue_v1.jsonl ordered by the three
priority queues that address the Task 60 regressions:

    QUEUE A - SOURCE_ATTRIBUTION       (unsupported attributed claims 6 -> 20)
    QUEUE B - STHANAKAVASI_DISTINCTION (sect_confusion 1 -> 4)
    QUEUE C - ABSTENTION               (abstention 0/4 -> 0/4)
    QUEUE D - everything else

Nothing is approved here. The queue only prepares evidence for a human.
"""
import csv
import json
import os
import sys
from collections import Counter, OrderedDict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "experiments", "sft_curation", "task61"))

from task61_common import (  # noqa: E402
    CATEGORIES, CATEGORY_TO_TASK_CATEGORY, load_manifest, load_rights_audit,
    load_jainqq_evidence, rights_for, canonical_status,
)

POOL = os.path.join(ROOT, "data/training/sft_candidates_v2.jsonl")
CORPUS = os.path.join(ROOT, "data/release/training_corpus.jsonl")
OUT = os.path.join(ROOT, "data/training/sft_task62_review_queue_v1.jsonl")

QUEUE_ORDER = OrderedDict([
    ("A", {"name": "QUEUE A - SOURCE ATTRIBUTION",
           "categories": ["SOURCE_ATTRIBUTION"],
           "why": "Task 60: unsupported source-attributed claims 6 -> 20 under DAPT-01."}),
    ("B", {"name": "QUEUE B - STHANAKAVASI DISTINCTION",
           "categories": ["STHANAKAVASI_DISTINCTION"],
           "why": "Task 60: sect_confusion cases 1 -> 4; category keyterm -0.25."}),
    ("C", {"name": "QUEUE C - ABSTENTION",
           "categories": ["ABSTENTION/INSUFFICIENT_EVIDENCE"],
           "why": "Task 60: abstention_correct 0/4 for both arms; the model never declines."}),
    ("D", {"name": "QUEUE D - REMAINING CANDIDATES",
           "categories": [],
           "why": "All other categories, reviewed after the regression queues."}),
])

# Reviewer checklist: shown for every record, flagged when the category makes a
# rubric item high-priority. The flag is a prompt to the human, never a verdict.
RUBRIC = [
    ("qa_alignment", "Question-answer alignment: does the answer actually answer this question?"),
    ("source_grounding", "Source grounding: is every factual claim supported by the supplied source text?"),
    ("attribution", "Source attribution: no commentary->Mahavira, teacher->canonical, translation->scripture confusion?"),
    ("sect_distinction", "Sthanakavasi distinction: no tradition-specific claim turned into a universal Jain claim?"),
    ("knowledge_layer", "Canonical vs commentary: is the knowledge layer preserved correctly?"),
    ("abstention", "Abstention: for evidence-gap questions, does it decline instead of inventing?"),
    ("practice", "Practice: is the practice identity, explanation, tradition attribution correct?"),
    ("language", "Prakrit/language: terminology, transliteration, Sanskrit-vs-Prakrit mapping sound?"),
    ("language_quality", "Language quality: natural, grammatical, no awkward generated phrasing?"),
    ("no_fabrication", "No fabrication: no invented citations, teachers, Agam refs, dates, quotes?"),
    ("pedagogy", "Pedagogical value: does it teach source-aware / tradition-aware / careful behaviour?"),
]

CATEGORY_PRIORITY = {
    "SOURCE_ATTRIBUTION": {"attribution", "source_grounding", "no_fabrication"},
    "STHANAKAVASI_DISTINCTION": {"sect_distinction", "source_grounding", "qa_alignment"},
    "ABSTENTION/INSUFFICIENT_EVIDENCE": {"abstention", "qa_alignment", "no_fabrication"},
    "AGAM_GROUNDED": {"source_grounding", "attribution", "no_fabrication"},
    "CANONICAL_VS_COMMENTARY": {"knowledge_layer", "source_grounding"},
    "PRACTICE_EXPLANATION": {"practice", "source_grounding"},
    "PRAKRIT": {"language", "source_grounding"},
    "SANSKRIT": {"language", "source_grounding"},
    "HINDI": {"language", "language_quality"},
    "GUJARATI": {"language", "language_quality"},
    "STHANAKAVASI_TERMINOLOGY": {"sect_distinction", "language"},
    "GENERAL_JAIN_CONCEPT": {"source_grounding", "pedagogy"},
}


def load_corpus_units(needed_ids):
    """Fetch full unit text for the cited units (single pass over the corpus)."""
    found = {}
    if not needed_ids:
        return found
    with open(CORPUS, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            uid = rec.get("id", "")
            if uid in needed_ids and uid not in found:
                found[uid] = rec
                if len(found) == len(needed_ids):
                    break
    return found


def load_review_state(path):
    """example_id -> latest decision (re-runs of the server overwrite cleanly)."""
    state = {}
    if not os.path.exists(path):
        return state
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("example_id"):
                state[rec["example_id"]] = rec
    return state


def queue_for(category):
    for key, spec in QUEUE_ORDER.items():
        if not spec["categories"] or category in spec["categories"]:
            return key
    return "D"


def main():
    manifest = load_manifest()
    audit_rights = load_rights_audit()
    jainqq = load_jainqq_evidence()

    pool = []
    with open(POOL, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                pool.append(json.loads(line))
    print("candidates in pool: %d" % len(pool))

    needed = {r["provenance"].get("text_id", "") for r in pool}
    needed.discard("")
    needed = {u for u in needed if not u.startswith("manifest:")}
    units = load_corpus_units(needed)
    print("source units loaded: %d / %d" % (len(units), len(needed)))

    ordered = sorted(pool, key=lambda r: (queue_for(r["category"]), r["review_id"]))
    n_a = sum(1 for r in ordered if queue_for(r["category"]) == "A")
    n_b = sum(1 for r in ordered if queue_for(r["category"]) == "B")
    n_c = sum(1 for r in ordered if queue_for(r["category"]) == "C")
    print("queue sizes: A=%d B=%d C=%d D=%d"
          % (n_a, n_b, n_c, len(ordered) - n_a - n_b - n_c))

    rows = []
    for pos, rec in enumerate(ordered):
        sid = rec["source_id"]
        man = manifest.get(sid, {})
        rights = rights_for(sid, manifest, audit_rights, jainqq)
        text_id = rec["provenance"].get("text_id", "")
        unit = units.get(text_id)
        qkey = queue_for(rec["category"])

        # source text shown to the reviewer: the cited unit in full when it is a
        # real corpus unit; for manifest-grounded claims the manifest row instead.
        if unit:
            source_text = unit.get("text", "")
            source_meta = {
                "unit_id": unit.get("id", ""),
                "document_id": unit.get("document_id", ""),
                "section": unit.get("section"),
                "script": unit.get("script"),
                "unit_language": unit.get("language"),
                "text_role": unit.get("text_role"),
                "unit_type": unit.get("unit_type"),
            }
        else:
            source_text = ""
            source_meta = {"unit_id": text_id, "note": "manifest-grounded claim; no corpus unit cited"}

        manifest_fields = OrderedDict()
        for k in ("title", "author", "publication_year", "publisher", "language",
                  "knowledge_layer", "religious_scope", "sect", "subsect",
                  "sect_confidence", "tradition", "relation_type", "parent_source_id",
                  "training_permission", "license", "repository", "source_url",
                  "sect_basis", "religious_scope_basis"):
            if man.get(k):
                manifest_fields[k] = man[k]

        priority = sorted(CATEGORY_PRIORITY.get(rec["category"], set()))
        checklist = [
            {"item": key, "instruction": text, "high_priority": key in priority}
            for key, text in RUBRIC
        ]

        rows.append(OrderedDict([
            ("queue", qkey),
            ("queue_name", QUEUE_ORDER[qkey]["name"]),
            ("queue_position", 0),
            ("queue_reason", QUEUE_ORDER[qkey]["why"]),
            ("review_id", rec["review_id"]),
            ("example_id", rec["example_id"]),
            ("review_status", "PENDING"),
            ("category", rec["category"]),
            ("task_category", rec["task_category"]),
            ("priority_rubric_items", priority),
            ("question", rec["question"]),
            ("question_hi", rec.get("question_hi", "")),
            ("answer", rec["answer"]),
            ("source_id", sid),
            ("source_title", rec.get("source_title", "")),
            ("parent_source_id", rec.get("parent_source_id", "")),
            ("locator", rec.get("locator", {})),
            ("religious_scope", rec.get("religious_scope", "")),
            ("sect", rec["provenance"].get("sect", "")),
            ("sect_confidence", rec["provenance"].get("sect_confidence", "")),
            ("knowledge_layer", rec.get("knowledge_layer", "")),
            ("teacher_or_author", rec.get("teacher_or_author", "")),
            ("lineage", rec.get("lineage", "")),
            ("canonical_status", rec.get("canonical_status", "")),
            ("canonical_status_derived_from_manifest", canonical_status(man)),
            ("provenance", rec.get("provenance", {})),
            ("rights_status", rec.get("rights_status", "")),
            ("rights_basis", rec.get("rights_basis", "")),
            ("rights_flags", rec.get("rights_flags", [])),
            ("origin", rec.get("origin", {})),
            ("split", rec.get("split", "")),
            ("split_candidate", rec.get("split_candidate", "")),
            ("language", rec.get("language", "")),
            ("question_type", rec.get("question_type", "")),
            ("evidence", rec.get("evidence", {})),
            ("citations", rec.get("citations", [])),
            ("manifest_fields", manifest_fields),
            ("source_unit_meta", source_meta),
            ("source_text", source_text),
            ("review_checklist", checklist),
            ("previous_decision", ""),
            ("previous_feedback", ""),
        ]))

    # per-queue running position (so the UI can show "Queue A, item 3 of 39")
    counters = Counter()
    for row in rows:
        counters[row["queue"]] += 1
        row["queue_position"] = counters[row["queue"]]
    for row in rows:
        row["queue_size"] = counters[row["queue"]]

    with open(OUT, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("wrote %s (%d rows)" % (os.path.relpath(OUT, ROOT), len(rows)))
    print("queue sizes: %s" % dict(sorted(Counter(r["queue"] for r in rows).items())))
    print("categories: %s" % dict(sorted(Counter(r["category"] for r in rows).items())))


if __name__ == "__main__":
    main()
