#!/usr/bin/env python3
"""TASK 62 stage 1b: append QUEUE R to the review queue.

QUEUE R re-adjudicates the three prior HUMAN_VERIFIED rows whose recorded
decision history does not stand on its own:

  * SVK-2025  - final recorded decision REVISE  -> not currently gold-eligible
  * SVK-2029  - final recorded decision REJECT  -> not currently gold-eligible
  * SVK-0038  - conflicting history (APPROVE, REJECT, REJECT, APPROVE, APPROVE)

Everything else in the queue file is left untouched; the script is idempotent
(existing QUEUE R rows are dropped and rebuilt).
"""
import json
import os
import sys
from collections import Counter, OrderedDict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "experiments", "sft_curation", "task61"))
sys.path.insert(0, os.path.join(ROOT, "experiments", "sft_curation", "task62"))

from task61_common import (  # noqa: E402
    load_manifest, load_rights_audit, load_jainqq_evidence, rights_for,
    canonical_status,
)
from build_review_queue import (  # noqa: E402
    RUBRIC, CATEGORY_PRIORITY, load_corpus_units, QUEUE_ORDER,
)

RECONCILED = os.path.join(ROOT, "data/training/sft_reconciled_v1.jsonl")
QUEUE = os.path.join(ROOT, "data/training/sft_task62_review_queue_v1.jsonl")

# example_id -> (final historical decision, why this row needs a human again)
REVALIDATE = OrderedDict([
    ("SFT-SEED-CAND-SVK-2025-SVK-2025", (
        "REVISE",
        "Prior history ends REVISE (\"ood but need more detailing as per user "
        "expectation\") - the row is marked HUMAN_VERIFIED but never received a "
        "closing APPROVE. Approve it only if the answer now meets the bar.")),
    ("SFT-SEED-CAND-SVK-2029-SVK-2029", (
        "REJECT",
        "Prior history ends REJECT (\"not needed\" / \"not needdd\") - the row is "
        "marked HUMAN_VERIFIED but the reviewer's last word was to drop it. "
        "Approve only if you now want it in the gold set.")),
    ("SFT-SEED-CAND-SVK-0038-unknown", (
        "APPROVE (conflicting)",
        "Prior history is APPROVE, REJECT, REJECT, APPROVE, APPROVE - two "
        "rejections were later overturned. Confirm the final APPROVE so the "
        "conflict is closed by a current human decision.")),
])

QUEUE_KEY = "R"
SPEC = {"name": "QUEUE R - RE-ADJUDICATE PRIOR VERIFIED ROWS",
        "why": "Prior HUMAN_VERIFIED rows whose recorded decision history does "
               "not stand on its own (Task 61 gap: 2025 REVISE, 2029 REJECT, "
               "0038 conflicting)."}


def load_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def build_r_rows():
    recon = {r["example_id"]: r for r in load_jsonl(RECONCILED)}
    manifest = load_manifest()
    audit_rights = load_rights_audit()
    jainqq = load_jainqq_evidence()

    needed = set()
    for eid in REVALIDATE:
        tid = recon[eid]["provenance"].get("text_id", "")
        if tid and not tid.startswith("manifest:"):
            needed.add(tid)
    units = load_corpus_units(needed)

    rows = []
    for eid, (last_decision, why) in REVALIDATE.items():
        rec = recon[eid]
        sid = rec["source_id"]
        man = manifest.get(sid, {})
        rights = rights_for(sid, manifest, audit_rights, jainqq)
        text_id = rec["provenance"].get("text_id", "")
        unit = units.get(text_id)

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
            source_meta = {"unit_id": text_id,
                           "note": "manifest-grounded claim; no corpus unit cited"}

        manifest_fields = OrderedDict()
        for k in ("title", "author", "publication_year", "publisher", "language",
                  "knowledge_layer", "religious_scope", "sect", "subsect",
                  "sect_confidence", "tradition", "relation_type", "parent_source_id",
                  "training_permission", "license", "repository", "source_url",
                  "sect_basis", "religious_scope_basis"):
            if man.get(k):
                manifest_fields[k] = man[k]

        category = rec.get("category", "")
        priority = sorted(CATEGORY_PRIORITY.get(category, set()))
        checklist = [{"item": k, "instruction": t, "high_priority": k in priority}
                     for k, t in RUBRIC]
        ev = rec.get("human_review_evidence", {})

        rows.append(OrderedDict([
            ("queue", QUEUE_KEY),
            ("queue_name", SPEC["name"]),
            ("queue_position", 0),
            ("queue_reason", SPEC["why"]),
            ("review_id", "T61-RECON-" + rec["example_id"]),
            ("example_id", eid),
            ("review_status", "PENDING"),
            ("category", category),
            ("task_category", rec.get("task_category", "")),
            ("priority_rubric_items", priority),
            ("question", rec["question"]),
            ("question_hi", ""),
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
            ("rights_flags", []),
            ("origin", rec.get("origin", {})),
            ("split", rec.get("split", "")),
            ("split_candidate", rec.get("split_candidate", "")),
            ("language", rec.get("language", "")),
            ("question_type", ""),
            ("evidence", {}),
            ("citations", []),
            ("manifest_fields", manifest_fields),
            ("source_unit_meta", source_meta),
            ("source_text", source_text),
            ("review_checklist", checklist),
            ("previous_decision", last_decision),
            ("previous_feedback", " | ".join(ev.get("reviewer_notes", []))),
            ("prior_review_history", {
                "task": ev.get("task"),
                "file": ev.get("file"),
                "approvals": ev.get("approvals", 0),
                "rejections": ev.get("rejections", 0),
                "revisions": ev.get("revisions", 0),
                "final_decision": last_decision,
                "reviewer_notes": ev.get("reviewer_notes", []),
            }),
            ("revalidation_reason", why),
            ("rights_recomputed", rights.get("status", "")),
        ]))
    return rows


def main():
    queue = [r for r in load_jsonl(QUEUE) if r.get("queue") != QUEUE_KEY]
    r_rows = build_r_rows()

    # queue D must follow R so the reviewer sees the re-adjudication early
    out = []
    for r in queue:
        if r["queue"] == "D" and not any(x["queue"] == QUEUE_KEY for x in out):
            out.extend(r_rows)
        out.append(r)

    counters = Counter()
    for row in out:
        counters[row["queue"]] += 1
        row["queue_position"] = counters[row["queue"]]
    for row in out:
        row["queue_size"] = counters[row["queue"]]

    with open(QUEUE, "w", encoding="utf-8") as fh:
        for row in out:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("queue sizes: %s" % dict(sorted(Counter(r["queue"] for r in out).items())))
    print("wrote %s (%d rows, %d queue-R)"
          % (os.path.relpath(QUEUE, ROOT), len(out), len(r_rows)))
    for r in r_rows:
        print("  R: %-42s prev=%s" % (r["example_id"], r["previous_decision"]))


if __name__ == "__main__":
    main()
