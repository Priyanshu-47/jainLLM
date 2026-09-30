#!/usr/bin/env python3
"""TASK 61 stage 2 - audit every existing SFT candidate artifact (Tasks 40-52).

Classifies each unique candidate into exactly one class:

    A HUMAN_VERIFIED_APPROVED   B HUMAN_REVISE_REQUIRED   C HUMAN_REJECTED
    D NEW_CANDIDATE_REQUIRES_HUMAN_REVIEW                  E RIGHTS_BLOCKED
    F PROVENANCE_INCOMPLETE      G DUPLICATE               H UNSUITABLE_FOR_SFT

Output: data/training/_task61_existing_candidates_audit.json
(intermediate; merged into data/training/sft_audit_v1.json by stage 3)
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from task61_common import (  # noqa: E402
    CLASS_A, CLASS_B, CLASS_C, CLASS_D, CLASS_E, CLASS_F, CLASS_G, CLASS_H,
    SFT_DIR, canonical_status, is_boilerplate, load_jainqq_evidence,
    load_manifest, load_rights_audit, load_split_map, normalize_q,
    ocr_noise_score, read_jsonl, rights_for, split_candidate,
)

EXAMPLE_FILES = {
    "stage_a_draft": "sft_stage_a_draft_v1.jsonl",
    "stage_a_review_queue": "sft_stage_a_review_queue_v1.jsonl",
    "gold_v1": "sft_gold_v1.jsonl",
    "gold_v2": "sft_gold_v2.jsonl",
    "gold_rejected_v1": "sft_gold_rejected_v1.jsonl",
    "review_priority_v1": "sft_review_priority_v1.jsonl",
    "revision_candidates_v1": "sft_revision_candidates_v1.jsonl",
    "review_remaining_v3": "sft_review_remaining_v3.jsonl",
    "gold_rejected_v2": "sft_gold_rejected_v2.jsonl",
    "candidate_pool_v1": "sft_candidate_pool_v1.jsonl",
    "task51_review_priority_v1": "sft_task51_review_priority_v1.jsonl",
    "stage_a_human_review_v1": "sft_stage_a_human_review_v1.jsonl",
    "revision_blocked_v1": "sft_revision_blocked_v1.jsonl",
    "candidate_quarantine_v1": "sft_candidate_quarantine_v1.jsonl",
    "seed_v1": "sft_seed_v1.jsonl",
    "gold_v3": "sft_gold_v3.jsonl",
}

REVIEW_FILES = {
    "task44": "sft_human_review_results_v1.jsonl",
    "task47": "sft_revision_human_review_v1.jsonl",
    "task51": "sft_task51_human_review_v1.jsonl",
}

VERIFIED_FILES = {"seed_v1", "gold_v3"}


def get_question(rec: dict) -> str:
    if rec.get("question"):
        return str(rec["question"])
    if rec.get("revised_question"):
        return str(rec["revised_question"])
    msgs = rec.get("messages")
    if isinstance(msgs, list):
        for m in msgs:
            if m.get("role") == "user":
                return str(m.get("content", ""))
    draft = rec.get("original_draft")
    if isinstance(draft, dict):
        for m in draft.get("messages", []):
            if m.get("role") == "user":
                return str(m.get("content", ""))
    return ""


def get_answer(rec: dict) -> str:
    if rec.get("answer"):
        return str(rec["answer"])
    if rec.get("revised_answer"):
        return str(rec["revised_answer"])
    msgs = rec.get("messages")
    if isinstance(msgs, list):
        for m in msgs:
            if m.get("role") == "assistant":
                return str(m.get("content", ""))
    draft = rec.get("original_draft")
    if isinstance(draft, dict):
        for m in draft.get("messages", []):
            if m.get("role") == "assistant":
                return str(m.get("content", ""))
    return ""


def subject_ids(rec: dict) -> list:
    ids = []
    for key in ("example_id", "candidate_id", "revision_id", "review_id"):
        v = rec.get(key)
        if v:
            ids.append(str(v))
    draft = rec.get("original_draft")
    if isinstance(draft, dict) and draft.get("example_id"):
        ids.append(str(draft["example_id"]))
    orig = rec.get("original_example_id")
    if orig:
        ids.append(str(orig))
    if rec.get("source_ids"):
        pass
    # stage_a_human_review nests ids
    return [i for i in dict.fromkeys(ids) if i]


def source_ids_of(rec: dict) -> list:
    out = []
    if rec.get("source_id"):
        out.append(rec["source_id"])
    if isinstance(rec.get("source_ids"), list):
        out.extend([s for s in rec["source_ids"] if s])
    cid = rec.get("candidate_id") or ""
    if cid.startswith("CAND-"):
        parts = cid.split("-")
        if len(parts) >= 3:
            out.append("-".join(parts[1:3]))
    draft = rec.get("original_draft")
    if isinstance(draft, dict) and isinstance(draft.get("source_ids"), list):
        out.extend([s for s in draft["source_ids"] if s])
    return list(dict.fromkeys([s for s in out if s]))


def unit_ids_of(rec: dict) -> list:
    out = []
    if rec.get("unit_id"):
        out.append(rec["unit_id"])
    if isinstance(rec.get("source_units"), list):
        out.extend([u for u in rec["source_units"] if u])
    if isinstance(rec.get("citations"), list):
        for c in rec["citations"]:
            if isinstance(c, dict) and c.get("unit_id"):
                out.append(c["unit_id"])
    draft = rec.get("original_draft")
    if isinstance(draft, dict):
        if draft.get("unit_id"):
            out.append(draft["unit_id"])
        if isinstance(draft.get("source_units"), list):
            out.extend([u for u in draft["source_units"] if u])
    return list(dict.fromkeys([u for u in out if u]))


def main() -> None:
    manifest = load_manifest()
    audit_rights = load_rights_audit()
    jainqq = load_jainqq_evidence()
    split_of = load_split_map()

    # ---------------- human decisions -------------------------------------
    approvals: dict = defaultdict(list)   # subject -> [decision records]
    rejections: dict = defaultdict(list)
    revisions: dict = defaultdict(list)
    for tag, fname in REVIEW_FILES.items():
        for rec in read_jsonl(os.path.join(SFT_DIR, fname)):
            subj = rec.get("example_id") or rec.get("candidate_id") or ""
            dec = (rec.get("decision") or "").upper()
            if not subj or not dec:
                continue
            entry = {"task": tag, "file": fname, "decision": dec,
                     "at": rec.get("reviewed_at") or rec.get("review_timestamp") or "",
                     "notes": rec.get("reviewer_notes") or rec.get("review_notes") or ""}
            if dec == "APPROVE":
                approvals[subj].append(entry)
            elif dec == "REJECT":
                rejections[subj].append(entry)
            elif dec == "REVISE":
                revisions[subj].append(entry)

    verified_subjects = set()
    verified_questions = {}
    for vkey in VERIFIED_FILES:
        fname = EXAMPLE_FILES[vkey]
        for rec in read_jsonl(os.path.join(SFT_DIR, fname)):
            q = normalize_q(get_question(rec))
            verified_questions[q] = vkey
            for sid in subject_ids(rec):
                verified_subjects.add(sid)
            if rec.get("candidate_id"):
                verified_subjects.add(rec["candidate_id"])

    # ---------------- gather candidate records ----------------------------
    raw = []
    for tag, fname in EXAMPLE_FILES.items():
        rows = read_jsonl(os.path.join(SFT_DIR, fname))
        for idx, rec in enumerate(rows):
            if tag == "stage_a_human_review_v1" and isinstance(rec.get("original_draft"), dict):
                merged = dict(rec["original_draft"])
                merged["_recommended_action"] = rec.get("recommended_action", "")
                merged["_review_status"] = rec.get("review_status", "")
                rec = merged
            raw.append({"file_key": tag, "file": fname, "index": idx, "rec": rec})

    # ---------------- dedup by normalized question + source ----------------
    groups: dict = {}
    order = []
    for item in raw:
        rec = item["rec"]
        q = normalize_q(get_question(rec))
        key = (q, tuple(sorted(source_ids_of(rec))))
        if not q:
            key = ("__empty__", (item["file_key"], item["index"]))
        if key not in groups:
            groups[key] = {"question": get_question(rec), "answer": get_answer(rec),
                           "source_ids": source_ids_of(rec), "unit_ids": unit_ids_of(rec),
                           "subjects": [], "occurrences": []}
            order.append(key)
        g = groups[key]
        for s in subject_ids(rec):
            if s not in g["subjects"]:
                g["subjects"].append(s)
        if not g["answer"]:
            g["answer"] = get_answer(rec)
        if not g["unit_ids"]:
            g["unit_ids"] = unit_ids_of(rec)
        g["occurrences"].append(item)

    # ---------------- classify -------------------------------------------
    results = []
    seen_q = {}
    for key in order:
        g = groups[key]
        occ_files = [o["file_key"] for o in g["occurrences"]]
        subjects = g["subjects"]
        qkey = normalize_q(g["question"])

        appr = [e for s in subjects for e in approvals.get(s, [])]
        rej = [e for s in subjects for e in rejections.get(s, [])]
        rev = [e for s in subjects for e in revisions.get(s, [])]
        # a record counts as verified only when its own text is the approved text
        # (matches a HUMAN_VERIFIED row) or it lives in a verified inventory file.
        in_verified = qkey in verified_questions or bool(set(occ_files) & VERIFIED_FILES)

        rights = None
        src = g["source_ids"][0] if g["source_ids"] else ""
        if src:
            rights = rights_for(src, manifest, audit_rights, jainqq)

        klass = None
        reason = ""
        if in_verified and appr:
            klass, reason = CLASS_A, "human APPROVE present and this exact row is in the HUMAN_VERIFIED inventory (%s)" % verified_questions.get(qkey, "inventory file")
        elif appr and not in_verified:
            successor = verified_questions.get(qkey)
            klass, reason = CLASS_B, "subject %s had a human APPROVE/REVISE, but this row is not the approved text; the human-approved successor lives in the HUMAN_VERIFIED inventory%s" % (
                ",".join(subjects[:2]), " (%s)" % successor if successor else " (see sft_reconciled_v1.jsonl)")
        elif rej and not appr:
            klass, reason = CLASS_C, "human REJECT: %s" % (rej[-1]["notes"][:140] or rej[-1]["at"])
        elif rev and not appr:
            klass, reason = CLASS_B, "human REVISE: %s" % (rev[-1]["notes"][:140] or rev[-1]["at"])
        else:
            # no human decision
            if not g["source_ids"]:
                klass, reason = CLASS_F, "no source_id on record"
            elif rights and not rights["allowed"]:
                klass, reason = CLASS_E, "rights not cleared: %s (%s)" % (rights["rights_status"], rights["basis"])
            elif not g["unit_ids"]:
                klass, reason = CLASS_F, "no source unit / text_id on record"
            elif qkey in seen_q:
                klass, reason = CLASS_G, "duplicate of first occurrence in %s" % seen_q[qkey]
            else:
                q, a = g["question"].strip(), g["answer"].strip()
                problems = []
                if not q or len(q) < 12:
                    problems.append("question missing/too short")
                if not a or len(a) < 40:
                    problems.append("answer missing/too short")
                if a and normalize_q(a) == normalize_q(q):
                    problems.append("answer duplicates question")
                if a and is_boilerplate(a):
                    problems.append("boilerplate answer")
                if a and "According to the source material from" in a and len(a) < 200:
                    problems.append("citation-only answer with no explanation")
                noise = ocr_noise_score(a)
                if noise["score"] >= 0.5:
                    problems.append("ocr_noise=%s" % noise["hits"])
                if not problems:
                    klass, reason = CLASS_D, "no human decision yet; rights+provenance clean"
                else:
                    klass, reason = CLASS_H, "; ".join(problems)

        if qkey not in seen_q:
            seen_q[qkey] = occ_files[0]

        results.append({
            "class": klass,
            "reason": reason,
            "question": g["question"][:200],
            "source_ids": g["source_ids"],
            "subjects": subjects,
            "files": sorted(set(occ_files)),
            "occurrences": len(g["occurrences"]),
            "rights_status": (rights or {}).get("rights_status", "UNKNOWN_NO_SOURCE"),
            "unit_ids": len(g["unit_ids"]),
            "human_approvals": len(appr),
            "human_rejections": len(rej),
            "human_revisions": len(rev),
        })

    # ---------------- per-file inventory ----------------------------------
    per_file = {}
    for tag, fname in EXAMPLE_FILES.items():
        rows = read_jsonl(os.path.join(SFT_DIR, fname))
        subs = set()
        for rec in rows:
            subs.update(subject_ids(rec))
        per_file[tag] = {
            "file": fname,
            "rows": len(rows),
            "unique_subject_ids": len(subs),
            "decision_fields": dict(Counter(str(rec.get("status") or rec.get("review_status") or rec.get("reviewer_status") or "") for rec in rows)),
        }

    class_counts = Counter(r["class"] for r in results)
    for c in (CLASS_A, CLASS_B, CLASS_C, CLASS_D, CLASS_E, CLASS_F, CLASS_G, CLASS_H):
        class_counts.setdefault(c, 0)

    out = {
        "task": 61,
        "stage": "existing_candidate_audit",
        "candidate_artifacts": per_file,
        "human_decision_totals": {
            "approval_subjects": sorted(approvals),
            "rejection_subjects": sorted(rejections),
            "revision_subjects": sorted(revisions),
            "approval_records": sum(len(v) for v in approvals.values()),
            "rejection_records": sum(len(v) for v in rejections.values()),
            "revision_records": sum(len(v) for v in revisions.values()),
        },
        "unique_candidates_audited": len(results),
        "class_counts": dict(class_counts),
        "class_definitions": {
            CLASS_A: "human APPROVE recorded (present in or recoverable to the HUMAN_VERIFIED inventory)",
            CLASS_B: "human REVISE recorded - not usable until re-reviewed",
            CLASS_C: "human REJECT recorded",
            CLASS_D: "no human decision yet; rights cleared, provenance complete, not duplicate, passes hygiene checks",
            CLASS_E: "source rights not cleared for SFT (manifest/audit/evidence)",
            CLASS_F: "provenance incomplete (missing source id or unit/text id)",
            CLASS_G: "duplicate of an earlier candidate (same normalized question + sources)",
            CLASS_H: "structurally unsuitable for SFT (short/empty/boilerplate/OCR-noisy/citation-only)",
        },
        "records": results,
        "rights_blocked_sources": sorted({
            r["source_ids"][0] for r in results
            if r["class"] == CLASS_E and r["source_ids"]
        }),
    }

    path = os.path.join(SFT_DIR, "_task61_existing_candidates_audit.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    print("unique candidates audited: %d" % len(results))
    print("class counts: %s" % dict(class_counts))
    print("wrote %s" % path)


if __name__ == "__main__":
    main()
