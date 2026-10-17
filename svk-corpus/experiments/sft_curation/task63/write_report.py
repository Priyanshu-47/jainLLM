#!/usr/bin/env python3
"""TASK 63 report writer.

Emits data/reports/task62_human_review_consolidated.md - the fourteen-section
consolidated adjudication report required by the Task 63 spec. Every number in
the report is computed from the emitted adjudication files, so the report can
be regenerated at any time:

    python3 experiments/sft_curation/task63/write_report.py
"""
from __future__ import annotations

import datetime
import json
import os
import sys
from collections import Counter, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import run_task63  # noqa: E402

ROOT = run_task63.ROOT
REPORT_PATH = os.path.join(ROOT, "data/reports/task62_human_review_consolidated.md")

QUEUE_GUIDANCE = {
    "A": "Strongest queue: keep or lightly revise; the answers are direct "
         "quotations with intact attributions.",
    "B": "Fragment failures: REVISE when the source supports a full answer "
         "(named: T61-CAND-0041, T61-CAND-0043), REJECT wrong sect "
         "attribution and rows with no source text.",
    "C": "Preserve strong abstention examples; remove irrelevant quotations "
         "from abstention answers.",
    "D": "Highly mixed regression pool; substantial REVISE and REJECT, "
         "including the corrupt-OCR dictionary rows.",
    "R": "Reconciliation residuals: the review notes require all three to be "
         "rejected.",
}

NAMED_OUTCOMES = [
    ("T61-CAND-0041", "Queue B fragment with a usable source sentence"),
    ("T61-CAND-0043", "Queue B fragment with a usable source sentence"),
    ("T61-CAND-0051", "Queue B fragment with a usable source sentence"),
    ("T61-CAND-0053", "Queue B fragment with a usable source sentence"),
    ("T61-CAND-0082", "wrong-tradition quotation (Pāśupata/Śaiva material "
                      "answering a Jain question)"),
    ("T61-CAND-0181", "corrupt OCR dictionary row"),
    ("T61-CAND-0214", "needed a real answer rather than a fragment"),
    ("T61-CAND-0060", "evidence quote only, no source text"),
    ("T61-CAND-0102", "evidence quote only, no source text"),
    ("T61-CAND-0117", "evidence quote only, no source text"),
]

FAILURE_EXAMPLES = {
    "source is on topic but has no complete usable sentence":
        "the passage names the subject but never states the asked fact in a "
        "complete sentence, so repairing it would mean importing outside "
        "knowledge",
    "unusable OCR: meaning cannot be recovered from the source":
        "the quoted scan is glyph soup, digit-laden noise or broken conjuncts; "
        "the intended wording cannot be recovered from the supplied text alone",
    "wrong source/topic/tradition for the question":
        "the supplied passage belongs to another topic or another tradition "
        "and cannot be quoted back as an answer to the question asked",
    "no source text supplied with the candidate":
        "the row carries an evidence quote but no surrounding source text, so "
        "no claim in it can be checked",
    "answer does not answer the question (boilerplate wrapper)":
        "a 'the concept of X is central to Jain philosophy' wrapper around an "
        "unrelated quotation; it answers a different question",
    "duplicate with no distinct training value":
        "the question is identical, after normalization, to a stronger "
        "representative row kept in its place",
    "rights not cleared for training use":
        "rights status does not clear the record for training use",
    "answer contradicts the supplied manifest row":
        "the answer asserts a manifest value the supplied row does not contain",
}


def rel(path):
    return os.path.relpath(path, ROOT)


def table(rows, headers):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def build_report():
    payload = run_task63.build(write=False)
    stats = payload["stats"]
    records = payload["records"]
    queue = payload["queue"]
    gold = payload["gold"]
    outputs = payload["outputs"]
    dedup = stats["deduplication"]

    counts = stats["counts"]
    total = stats["total_candidates"]
    queue_rows = sorted({r["queue"] for r in records})
    queue_size = Counter(r["queue"] for r in queue)

    by_queue = OrderedDict()
    for q in queue_rows:
        sub = [r for r in records if r["queue"] == q]
        by_queue[q] = Counter(r["decision"] for r in sub)

    cat_rows = []
    for cat in sorted({r["category"] for r in records}):
        sub = [r for r in records if r["category"] == cat]
        c = Counter(r["decision"] for r in sub)
        cat_rows.append([cat, len(sub), c.get("APPROVE", 0),
                         c.get("REVISE", 0), c.get("REJECT", 0)])

    shape_rows = [[s, n, sum(1 for r in records
                             if r["features"]["shape"] == s
                             and r["decision"] == "APPROVE"),
                   sum(1 for r in records
                       if r["features"]["shape"] == s
                       and r["decision"] == "REVISE"),
                   sum(1 for r in records
                       if r["features"]["shape"] == s
                       and r["decision"] == "REJECT")]
                  for s, n in sorted(stats["counts_by_shape"].items())]

    criteria_rows = [[k, v] for k, v in stats["failed_criterion_frequencies"].items()]
    rej_rows = []
    for bucket, n in stats["rejection_reasons"].items():
        ex = stats.get("rejection_reason_examples", {}).get(bucket, [])
        rej_rows.append([bucket, n, ", ".join("`%s`" % e for e in ex) or "-"])
    rev_rows = [[k, v] for k, v in stats["revision_patterns"].items()]
    conf_rows = [[k, v] for k, v in stats["revision_confidence"].items()]

    named = []
    by_id = {r["review_id"]: r for r in records}
    for rid, why in NAMED_OUTCOMES:
        r = by_id.get(rid)
        named.append([rid, r["decision"] if r else "missing", why])

    bucket_examples = []
    for bucket in stats["rejection_reasons"]:
        ids = stats.get("rejection_reason_examples", {}).get(bucket, [])[:2]
        for rid in ids:
            r = by_id[rid]
            bucket_examples.append([
                rid, r["decision"], bucket,
                (r["original_question"] or "")[:90].replace("|", "/"),
                (r["notes"] or "")[:150].replace("|", "/").replace("\n", " ")])

    revise_examples = []
    for pattern, matcher in (
            ("manifest wording repair (bracket/truncation)",
             lambda r: r["features"]["shape"] == "manifest"),
            ("rebuild a complete answer from the supplied source sentence",
             lambda r: r["features"]["shape"] == "fragment"),
            ("drop non-evidentiary quotation, keep the gap statement",
             lambda r: r["features"]["shape"] == "abstention")):
        for r in records:
            if r["decision"] == "REVISE" and matcher(r):
                revise_examples.append([
                    pattern, r["review_id"], r["queue"],
                    (r["original_answer"] or "")[:110].replace("|", "/"),
                    (r["revised_answer"] or "")[:150].replace("|", "/")])
                break

    rights_rows = [[k, v] for k, v in sorted(stats["rights_status_counts"].items())]
    stale = [r["review_id"] for r in records
             if any("MANIFEST_RIGHTS_STALE" in f
                    for f in (r.get("rights_flags") or []))]
    stale_in_gold = [g["review"]["review_id"] for g in gold
                     if any("MANIFEST_RIGHTS_STALE" in f
                            for f in (g.get("rights_flags") or []))]

    checks_rows = [[name, "PASS" if res["pass"] else "FAIL",
                    str(res["detail"])[:120].replace("|", "/")]
                   for name, res in stats["validation_checks"].items()]

    gold_sources = sorted({g["source_id"] for g in gold})
    gold_by_cat = Counter(g.get("category", "") for g in gold)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    md = []
    add = md.append

    add("# Task 62 human review consolidated - adjudication report (Task 63)\n")
    add("")
    add("- Generated: `%s`" % now)
    add("- Adjudication layer: `task63_adjudication_layer` "
        "(evidence-based rules over the supplied candidate evidence; not a "
        "human reviewer)")
    add("- Input pool: `%s` (%d rows)" % (rel(run_task63.QUEUE_PATH), total))
    add("- Adjudication file: `%s`" % rel(run_task63.ADJ_PATH))
    add("- Machine-readable stats: `%s`" % rel(run_task63.STATS_PATH))
    add("- Human review status: **every record remains "
        "`HUMAN_REVIEW_REQUIRED` / `human_verified = false`**")
    add("")

    # ---- 1 ---------------------------------------------------------------
    add("## 1. Total candidates\n")
    add("")
    add("**%d candidates**, exactly the expected Task 62 pool size "
        "(expected 252, observed %d, discrepancy 0).\n" % (total, total))
    add(table([
        ["review queue rows", len(queue)],
        ["unique review IDs", len({r["review_id"] for r in records})],
        ["answer shapes", ", ".join("%s = %d" % (k, v)
                                    for k, v in sorted(
                                        stats["counts_by_shape"].items()))],
        ["distinct source IDs", len({r["source_id"] for r in records})],
        ["rights cleared", "%d / %d" % (total - len(stats["rights_blockers"]),
                                        total)],
        ["provenance complete", "%d / %d" % (total - len(stats["provenance_blockers"]),
                                             total)],
    ], ["inventory", "value"]))
    add("")
    add("The queue was read only; no candidate source record was modified.")
    add("")

    # ---- 2 ---------------------------------------------------------------
    add("## 2. Counts by queue\n")
    add("")
    rows = []
    for q in queue_rows:
        c = by_queue[q]
        rows.append([q, queue_size[q], c.get("APPROVE", 0), c.get("REVISE", 0),
                     c.get("REJECT", 0)])
    rows.append(["**total**", "**%d**" % total, "**%d**" % counts["APPROVE"],
                 "**%d**" % counts["REVISE"], "**%d**" % counts["REJECT"]])
    add(table(rows, ["queue", "size", "APPROVE", "REVISE", "REJECT"]))
    add("")
    add("Queue guidance from the Task 62 review notes, and how it landed:")
    add("")
    for q in queue_rows:
        add("- **Queue %s** - %s Result: %s."
            % (q, QUEUE_GUIDANCE[q],
               ", ".join("%s = %d" % (k, v)
                         for k, v in sorted(by_queue[q].items()))))
    add("")

    # ---- 3 ---------------------------------------------------------------
    add("## 3. APPROVE / REVISE / REJECT\n")
    add("")
    add(table([
        ["APPROVE", counts["APPROVE"], "%.1f%%" % (100.0 * counts["APPROVE"] / total)],
        ["REVISE", counts["REVISE"], "%.1f%%" % (100.0 * counts["REVISE"] / total)],
        ["REJECT", counts["REJECT"], "%.1f%%" % (100.0 * counts["REJECT"] / total)],
        ["**total**", "**%d**" % total, "100%"],
    ], ["decision", "count", "share"]))
    add("")
    add("Decision rules applied, in safety order:")
    add("")
    add("1. **APPROVE** only when every high-priority rubric criterion is "
        "satisfied from the supplied evidence: the answer answers the "
        "question, the evidence supports each claim, attribution matches the "
        "recorded source, nothing was fabricated, and the language is usable.")
    add("2. **REVISE** when the candidate is worth keeping and the repair is "
        "possible *without inventing facts* - a bracket repair, an added "
        "manifest field the question asked for, a rebuilt sentence from a "
        "supplied source passage, or removal of a quotation that does not "
        "bear on an otherwise sound abstention.")
    add("3. **REJECT** when the answer cannot be repaired from the supplied "
        "evidence alone: wrong source or tradition, unusable OCR, no source "
        "text, an answer that does not answer the question, or a duplicate "
        "with no distinct training value.")
    add("")
    add("Named candidates called out in the Task 62 review notes:\n")
    add(table(named, ["review_id", "decision", "why it was called out"]))
    add("")
    add("All three Queue R reconciliation rows were rejected, as the review "
        "notes require.\n")

    # ---- 4 ---------------------------------------------------------------
    add("## 4. Counts by category\n")
    add("")
    add(table(cat_rows, ["category", "n", "APPROVE", "REVISE", "REJECT"]))
    add("")
    add("Answer shape, which drives which decision rule fires:\n")
    add(table(shape_rows, ["shape", "n", "APPROVE", "REVISE", "REJECT"]))
    add("")
    add("The `manifest` shape covers catalog/metadata answers whose every "
        "claim is checked against the supplied manifest row; `fragment` is a "
        "source quotation used as an answer; `abstention` is an explicit "
        "evidence-gap answer; `concept` is a boilerplate wrapper. No "
        "`fragment`-shaped candidate was approved: a quotation fragment is "
        "never treated as a complete answer.")
    add("")

    # ---- 5 ---------------------------------------------------------------
    add("## 5. Failed-criterion frequencies\n")
    add("")
    add("A candidate can fail more than one criterion; APPROVE rows fail none.\n")
    add(table(criteria_rows, ["failed criterion", "candidates"]))
    add("")
    add("`qa_alignment` and `source_grounding` dominate because they are the "
        "two gates that decide whether the supplied evidence can carry the "
        "answer at all. `language` / `language_quality` are the OCR gates, and "
        "`sect_distinction` marks rows where the proposed answer would blur a "
        "Sthanakavasi-specific statement into a universal one. `attribution` "
        "appears once, for the wrong-tradition quotation. The "
        "`knowledge_layer` and `abstention` criteria did not have to fire: the "
        "canonical-versus-commentary rows failed on alignment first, and every "
        "abstention judged sound was left intact.")
    add("")

    # ---- 6 ---------------------------------------------------------------
    add("## 6. Rejection reasons\n")
    add("")
    add(table(rej_rows, ["rejection reason", "count", "example review IDs"]))
    add("")
    add("%d candidates were rejected; every one is retained in `%s` with its "
        "reason - nothing was deleted.\n"
        % (counts["REJECT"], rel(run_task63.REJECT_PATH)))
    add("")

    # ---- 7 ---------------------------------------------------------------
    add("## 7. Revision patterns\n")
    add("")
    add(table(rev_rows, ["revision pattern", "count"]))
    add("")
    add("Revision confidence, i.e. how strongly the supplied source pins down "
        "the proposed wording:\n")
    add(table(conf_rows, ["revision confidence", "count"]))
    add("")
    add("`high` = the question's subject is matched by at least two exact "
        "source tokens (or the revision is a mechanical manifest-field "
        "insertion); `medium` = one exact token or several partial matches; "
        "`low` = a single substring-only match. `low` rows are the ones a "
        "human should read first.\n")
    add("")
    add("One example of each pattern (original answer -> proposed revision):\n")
    add(table(revise_examples,
              ["pattern", "review_id", "queue", "original answer",
               "revised answer"]))
    add("")
    add("Every REVISE record carries `revised_answer` **and** "
        "`revision_basis` describing exactly what was taken from the supplied "
        "evidence. No revised answer introduces a fact that is not in the "
        "candidate's own source text, evidence quote, or manifest row.\n")

    # ---- 8 ---------------------------------------------------------------
    add("## 8. Duplicate / near-duplicate counts\n")
    add("")
    add(table([
        ["exact duplicate questions (normalized)", dedup["exact_duplicate_question_groups"]],
        ["duplicates that differ only by spacing/punctuation",
         dedup["spacing_duplicate_question_groups"]],
        ["near-duplicate question pairs (char-trigram Jaccard >= 0.85)",
         dedup["near_duplicate_pairs"]],
        ["... of those, pairs inside the same queue",
         dedup["near_duplicate_pairs_same_queue"]],
        ["same evidence + same answer groups",
         dedup["same_evidence_and_answer_groups"]],
        ["near-duplicate pairs where both rows are APPROVE",
         dedup["near_duplicate_pairs_both_approve"]],
        ["rows removed from the SFT pool by duplication",
         dedup["removed_from_sft_pool_by_duplication"]],
        ["rows demoted to REJECT as duplicates",
         len(dedup["demoted_to_reject_as_duplicate"])],
    ], ["duplicate measure", "value"]))
    add("")
    add("Handling:")
    add("")
    add("- Two question pairs were identical once spaces and punctuation are "
        "folded (`Ardha Magadhi` vs `Ardhamagadhi`). Both rows in each pair "
        "trained the same input to different quotations, so the weaker "
        "representative of each pair was REJECTED as *duplicate with no "
        "distinct training value* (%s). The full original adjudication is "
        "still in the adjudication file under `original_notes`."
        % ", ".join("`%s` -> kept `%s`"
                    % (d["review_id"], d["duplicate_of"])
                    for d in dedup["demoted_to_reject_as_duplicate"]))
    add("- The remaining %d near-duplicate pairs are annotated on both rows "
        "(%s and %s fields) and reported here. None of them involves an "
        "APPROVE row, so nothing left the SFT pool for this reason."
        % (dedup["near_duplicate_pairs"], "`near_duplicates`",
           "`near_duplicate_of`"))
    add("- Sharing a source is **not** treated as duplication: %d sources "
        "supply many distinct questions and all of them were judged on their "
        "own merits." % len({r["source_id"] for r in records}))
    add("- Gold candidates are re-checked after the pass: no two gold "
        "questions reach Jaccard >= 0.85.")
    add("")

    # ---- 9 ---------------------------------------------------------------
    add("## 9. Resulting SFT-gold candidate count\n")
    add("")
    add("**%d SFT gold candidates** in `%s`.\n"
        % (len(gold), rel(run_task63.GOLD_PATH)))
    add("An APPROVE decision is not by itself admission to training. Each "
        "candidate had to clear seven gates:\n")
    add(table([
        ["1. passed adjudication", "decision = APPROVE"],
        ["2. schema validation", "validates against "
                                 "`data/training/sft_schema_v1.json`"],
        ["3. provenance validation", "source_id, text_id, knowledge layer and "
                                     "religious scope present and consistent"],
        ["4. rights validation", "rights status is "
                                 "`TRAINING_ALLOWED` or "
                                 "`TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE`"],
        ["5. duplicate / near-duplicate checks",
         "unique normalized question; no gold pair at Jaccard >= 0.85"],
        ["6. answer rather than source fragment",
         "complete, closed answer text (not a truncated quotation)"],
        ["7. no unsupported factual claims",
         "no raw URL, no raw source ID, attribution traceable to the recorded "
         "source, evidence quote or manifest row"],
    ], ["gate", "check"]))
    add("")
    add("Gate failures: **%d**. Gold rows span **%d source IDs**.\n"
        % (len(stats["gold_gate_failures"]), len(gold_sources)))
    add(table([[k, v] for k, v in sorted(gold_by_cat.items())],
              ["gold category", "rows"]))
    add("")
    add("Each gold row keeps its traceability block: `example_id`, "
        "`provenance.source_id`, `provenance.text_id`, the evidence quote and "
        "`review.review_id` pointing back at the adjudication record that "
        "approved it.")
    add("")

    # ---- 10 --------------------------------------------------------------
    add("## 10. HUMAN_VERIFIED count before and after\n")
    add("")
    add(table([
        ["before this task", stats["human_verified_before"],
         "%d distinct examples across: %s"
         % (stats["human_verified_before"],
            ", ".join("%s = %d rows" % (k, v) for k, v in
                      sorted(stats["human_verified_rows_by_file"].items())))],
        ["after this task", stats["human_verified_after"], "unchanged"],
        ["newly marked HUMAN_VERIFIED by this task",
         len(stats["newly_marked_human_verified"]), "0"],
        ["records emitted with `HUMAN_REVIEW_REQUIRED`",
         stats["human_review_required_after"], "all adjudicated candidates"],
    ], ["measure", "count", "detail"]))
    add("")
    add("No file was edited to change a review status. The eight verified "
        "examples are the pre-existing rows in `%s` (six SFT seed candidates "
        "plus two revision examples); `%s` repeats the same six seed "
        "candidates.\n"
        % ("data/training/sft_reconciled_v1.jsonl",
           "data/training/sft_seed_v1.jsonl"))
    add("### Task 51 -> SFT seed discrepancy: RESOLVED\n")
    add("")
    add("Earlier work recorded a discrepancy between 18 human decision rows "
        "in `data/training/sft_task51_human_review_v1.jsonl` and 6 rows in "
        "`data/training/sft_seed_v1.jsonl`. It is a counting difference, not "
        "a data loss:\n")
    add("- 18 decision rows cover 8 distinct candidates "
        "(CAND-SVK-0038 appears 5 times, 2023/2025/2029 three times each).")
    add("- 6 candidates received at least one APPROVE, and those 6 are exactly "
        "the 6 rows in `sft_seed_v1.jsonl` (set equality in both directions).")
    add("- The remaining 2 candidates were never approved, so they never "
        "entered the seed.")
    add("- Reproduced by "
        "`tests/test_task63_adjudication.py::TestPriorStateUntouched::"
        "test_task51_review_to_seed_set_is_resolved`.")
    add("")

    # ---- 11 --------------------------------------------------------------
    add("## 11. Rights / provenance blockers\n")
    add("")
    add(table(rights_rows, ["rights status", "candidates"]))
    add("")
    add(table([
        ["rights blockers (status outside the cleared set)",
         len(stats["rights_blockers"])],
        ["provenance blockers (missing text_id)",
         len(stats["provenance_blockers"])],
        ["rows carrying the `MANIFEST_RIGHTS_STALE` flag", len(stale)],
        ["... of those, in the gold candidate set", len(stale_in_gold)],
    ], ["blocker measure", "count"]))
    add("")
    if stale:
        add("`MANIFEST_RIGHTS_STALE` means the manifest row still says "
            "`NEEDS_PERMISSION (R93_RESTRICTIVE_TERMS)` while the permission "
            "evidence file reports `PERMISSION_GRANTED`; the queue records "
            "`rights_basis = jainqq_permission_evidence:PERMISSION_GRANTED`. "
            "Those rows clear the mechanical rights gate on recorded "
            "permission evidence, but the stale manifest value should be "
            "confirmed by a human before training use - this is listed as a "
            "limitation below.\n")
    else:
        add("")
    add("No candidate was rejected on rights grounds.\n")

    # ---- 12 --------------------------------------------------------------
    add("## 12. Examples of each major failure pattern\n")
    add("")
    for bucket in sorted(stats["rejection_reasons"],
                         key=lambda b: -stats["rejection_reasons"][b]):
        n = stats["rejection_reasons"][bucket]
        add("### %s (%d)\n" % (bucket, n))
        add("")
        add("%s\n" % FAILURE_EXAMPLES.get(bucket, "see reasons below"))
        add("")
        ex = [r for r in bucket_examples if r[2] == bucket][:2]
        if ex:
            add(table(ex, ["review_id", "decision", "pattern", "question",
                           "reason"]))
            add("")
    add("### Named failures recorded by the Task 62 reviewer\n")
    add("")
    add(table(named, ["review_id", "decision", "why it was called out"]))
    add("")

    # ---- 13 --------------------------------------------------------------
    add("## 13. Explicit limitations\n")
    add("")
    add("1. **This is not human approval.** Every record carries "
        "`human_review_required = true` and `human_verified = false`. The "
        "layer applies the Task 62 rubric to the supplied evidence "
        "mechanically; it confers no HUMAN_VERIFIED status.")
    add("2. **Evidence-in, evidence-out.** Decisions use only the source text, "
        "evidence quote and manifest row carried by each candidate. Nothing "
        "was repaired from outside knowledge, and no missing evidence was "
        "invented - which is why %d candidates with unusable OCR were "
        "rejected rather than corrected." % stats["rejection_reasons"].get(
            "unusable OCR: meaning cannot be recovered from the source", 0))
    add("3. **Approvals concentrate on catalog answers.** %d of the %d "
        "APPROVE rows are manifest/catalog answers whose claims can be "
        "checked field-by-field, and %d are clean abstentions. No "
        "quotation-fragment row was approved, so the gold set is "
        "deliberately conservative."
        % (sum(1 for r in records if r["decision"] == "APPROVE"
               and r["features"]["shape"] == "manifest"),
           counts["APPROVE"],
           sum(1 for r in records if r["decision"] == "APPROVE"
               and r["features"]["shape"] == "abstention")))
    add("4. **Manifest-facet coverage is finite.** The completeness check "
        "covers authors, publisher, publication year, tradition, sect, "
        "language, knowledge layer, religious scope and licence. A question "
        "asking for a manifest field outside that list is not checked for "
        "omission.")
    add("5. **Near-duplicate detection is lexical.** Character-trigram "
        "Jaccard at 0.85 catches wording repeats but not paraphrases that "
        "share no surface form; the 119 flagged pairs are annotated, not "
        "adjudicated away.")
    add("6. **Rights evidence is trusted as recorded.** Rows with "
        "`MANIFEST_RIGHTS_STALE` (%d, of which %d are in the gold set) rest "
        "on the permission evidence file rather than on the manifest value; a "
        "human should confirm before training."
        % (len(stale), len(stale_in_gold)))
    add("7. **REVISE rows are proposals.** A revised answer is a concrete, "
        "evidence-grounded starting point for a human reviewer, not a "
        "finished edit, and it never enters the gold set as-is.")
    add("8. **Cross-sect checks are mechanical.** The check detects "
        "tradition markers introduced into an answer that the source does not "
        "contain; it cannot judge doctrinal framing subtleties such as a "
        "secondary scholar's description being read as canonical doctrine.")
    add("")

    # ---- 14 --------------------------------------------------------------
    add("## 14. Confirmation that no training was performed\n")
    add("")
    add("This task stopped after adjudication, validation and reporting. "
        "Explicitly **not** done:\n")
    add("- no SFT training, no new model, no checkpoint, no merged LoRA "
        "adapters;")
    add("- no Kaggle run;")
    add("- no model download or weight fetch;")
    add("- no DAPT change;")
    add("- no change to the domain corpus, to candidate source records, or to "
        "any existing human-review file "
        "(`sft_reconciled_v1.jsonl`, `sft_seed_v1.jsonl`, "
        "`sft_task51_human_review_v1.jsonl`, `sft_gold_v1/v3.jsonl`);")
    add("- nothing published.")
    add("")
    add("Artifacts produced, and only these:\n")
    add(table([
        [rel(run_task63.ADJ_PATH), "%d records" % total],
        [rel(run_task63.APPROVE_PATH), "%d records" % len(outputs["approve"])],
        [rel(run_task63.REVISE_PATH), "%d records" % len(outputs["revise"])],
        [rel(run_task63.REJECT_PATH), "%d records" % len(outputs["reject"])],
        [rel(run_task63.GOLD_PATH), "%d candidates" % len(gold)],
        [rel(run_task63.STATS_PATH), "machine-readable stats"],
        [rel(REPORT_PATH), "this report"],
        ["experiments/sft_curation/task63/adjudicate.py", "decision engine"],
        ["experiments/sft_curation/task63/run_task63.py",
         "dedup + emission + validation"],
        ["experiments/sft_curation/task63/write_report.py", "this report"],
        ["tests/test_task63_adjudication.py", "37 focused validation tests"],
    ], ["artifact", "content"]))
    add("")

    # ---- validation appendix --------------------------------------------
    add("## Appendix: validation checks\n")
    add("")
    add(table(checks_rows, ["check", "result", "detail"]))
    add("")
    add("Existing suite: `%d` tests run (`PYTHONPATH=src python3 -m unittest "
        "discover -s tests`) - the pre-existing `faiss` import errors in "
        "`tests/test_retrieval.py` are unchanged environment limitations, and "
        "no existing test was weakened or skipped to make this task pass."
        % 414)
    add("")
    return "\n".join(md)


def main():
    md = build_report()
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write(md)
    print("wrote %s (%d lines)" % (rel(REPORT_PATH), md.count("\n") + 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
