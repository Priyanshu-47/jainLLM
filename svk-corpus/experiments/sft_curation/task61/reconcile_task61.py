#!/usr/bin/env python3
"""TASK 61 stage 1 - human-review reconciliation (Tasks 40-52).

Reads every human-review artifact produced by Tasks 40-52, classifies each
record, and assigns exactly one reconciliation state to every approval record:

    PRESENT | RECOVERABLE | EXCLUDED_WITH_REASON | NOT_VERIFIED

Outputs (all under data/training):
    sft_reconciled_v1.jsonl          existing HUMAN_VERIFIED examples, normalized
    sft_reconciliation_table.csv     one row per human review record
    _task61_reconciliation_summary.json  intermediate for the Task 61 audit

Hard rules: no human-approved example is dropped or rewritten; every approval
record in sft_task51_human_review_v1.jsonl must appear exactly once.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from task61_common import (  # noqa: E402
    CLASS_A, CLASS_B, CLASS_C, CLASS_D, CLASS_E, CLASS_F, CLASS_G, CLASS_H,
    CORPUS, ROOT, SFT_DIR, STATE_EXCLUDED, STATE_NOT_VERIFIED, STATE_PRESENT,
    STATE_RECOVERABLE, VALID_STATES, canonical_status, load_jainqq_evidence,
    load_manifest, load_rights_audit, load_split_map, load_units,
    map_knowledge_layer, map_religious_scope, normalize_q, read_jsonl,
    rights_for, split_candidate, write_jsonl,
)

TASK51_APPROVALS_EXPECTED = 11

REVIEW_FILES = {
    "T41_stage_a_review_queue": "sft_stage_a_human_review_v1.jsonl",
    "T44_gold_review": "sft_human_review_results_v1.jsonl",
    "T47_revision_review": "sft_revision_human_review_v1.jsonl",
    "T50_review": "sft_task50_human_review_v1.jsonl",
    "T51_candidate_review": "sft_task51_human_review_v1.jsonl",
}

CANDIDATE_FILES = {
    "stage_a_draft": "sft_stage_a_draft_v1.jsonl",
    "stage_a_review_queue": "sft_stage_a_review_queue_v1.jsonl",
    "gold_v1": "sft_gold_v1.jsonl",
    "gold_rejected_v1": "sft_gold_rejected_v1.jsonl",
    "review_priority_v1": "sft_review_priority_v1.jsonl",
    "revision_candidates_v1": "sft_revision_candidates_v1.jsonl",
    "review_remaining_v3": "sft_review_remaining_v3.jsonl",
    "gold_rejected_v2": "sft_gold_rejected_v2.jsonl",
    "candidate_pool_v1": "sft_candidate_pool_v1.jsonl",
    "task51_review_priority_v1": "sft_task51_review_priority_v1.jsonl",
    "seed_v1": "sft_seed_v1.jsonl",
    "gold_v3": "sft_gold_v3.jsonl",
    "gold_v2": "sft_gold_v2.jsonl",
    "revision_blocked_v1": "sft_revision_blocked_v1.jsonl",
    "candidate_quarantine_v1": "sft_candidate_quarantine_v1.jsonl",
}


def subject_source(subject_id: str) -> str:
    if subject_id.startswith("CAND-"):
        parts = subject_id.split("-")
        return "-".join(parts[1:3]) if len(parts) >= 3 else ""
    if subject_id.startswith("REV-"):
        subject_id = subject_id[4:]
    return ""


def _squeeze(text: str) -> str:
    return "".join((text or "").split()).lower()


def quoted_spans(answer: str, min_len: int = 40) -> list:
    spans = []
    for m in re.finditer(r"\"(.+?)\"", answer or "", flags=re.S):
        span = " ".join(m.group(1).split())
        if len(span) >= min_len:
            spans.append(span)
    return spans


def find_unit_by_text(source_id: str, spans: list) -> list:
    """Locate the corpus unit that actually contains the quoted evidence."""
    if not source_id or not spans:
        return []
    hits = []
    with open(CORPUS, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip() or source_id not in line:
                continue
            rec = json.loads(line)
            if rec.get("source_id") != source_id:
                continue
            hay = _squeeze(rec.get("text", "")) + " " + _squeeze(rec.get("normalized_text", ""))
            for span in spans:
                if _squeeze(span) and _squeeze(span) in hay:
                    hits.append({"unit": rec.get("unit_id") or rec.get("id", ""), "id": rec.get("id", ""), "matched_span": span[:80]})
                    break
    return hits


def quote_in_units(spans: list, unit_records: list) -> dict:
    """Verify quoted evidence actually occurs in the cited unit(s)."""
    if not spans:
        return {"checked": False, "result": "NO_QUOTE_IN_ANSWER", "missing": []}
    hay = " ".join(_squeeze(u.get("text", "")) + " " + _squeeze(u.get("normalized_text", "")) for u in unit_records)
    if not hay:
        return {"checked": True, "result": "NO_CITED_UNIT_TEXT", "missing": [s[:60] for s in spans]}
    missing = [s[:60] for s in spans if _squeeze(s) not in hay]
    if not missing:
        return {"checked": True, "result": "VERIFIED", "missing": []}
    # tolerate OCR-level differences on the shared token overlap
    still = []
    for span in spans:
        if _squeeze(span) in hay:
            continue
        toks = [t.lower() for t in re.findall(r"[A-Za-z]{5,}", span)]
        if toks:
            core = toks[:12]
            present = sum(1 for t in core if t in hay)
            if present / len(core) < 0.75:
                still.append(span[:60])
    if not still:
        return {"checked": True, "result": "VERIFIED_FUZZY", "missing": []}
    return {"checked": True, "result": "QUOTE_NOT_FOUND_IN_CITED_UNIT", "missing": still}


def main() -> None:
    manifest = load_manifest()
    audit = load_rights_audit()
    jainqq = load_jainqq_evidence()
    split_of = load_split_map()

    paths = {k: os.path.join(SFT_DIR, v) for k, v in REVIEW_FILES.items()}
    review_rows = {k: read_jsonl(p) for k, p in paths.items()}
    cand_rows = {k: read_jsonl(os.path.join(SFT_DIR, v)) for k, v in CANDIDATE_FILES.items()}

    seed = cand_rows["seed_v1"]
    gold_v3 = cand_rows["gold_v3"]

    # ---------------- verified inventory (existing HUMAN_VERIFIED) ----------
    seed_by_cand = {r["candidate_id"]: r for r in seed}
    gold3_by_rev = {r["revision_id"]: r for r in gold_v3}
    gold3_by_orig = {r["original_example_id"]: r for r in gold_v3}

    # subject id -> source id / unit ids (for rights + provenance)
    subj_meta: dict = {}

    def note_meta(subject_id, source_id, unit_ids, origin):
        cur = subj_meta.setdefault(subject_id, {"source_ids": set(), "unit_ids": set(), "origins": set()})
        if source_id:
            cur["source_ids"].add(source_id)
        for u in unit_ids or []:
            cur["unit_ids"].add(u)
        cur["origins"].add(origin)

    for r in cand_rows["candidate_pool_v1"]:
        note_meta(r.get("candidate_id", ""), r.get("source_id", ""), [r.get("unit_id")] if r.get("unit_id") else [], "candidate_pool_v1")
    for r in cand_rows["task51_review_priority_v1"]:
        note_meta(r.get("candidate_id", ""), r.get("source_id", ""), [r.get("unit_id")] if r.get("unit_id") else [], "task51_review_priority_v1")
    for key in ("gold_v1", "revision_candidates_v1", "review_remaining_v3", "gold_rejected_v1", "gold_rejected_v2"):
        for r in cand_rows[key]:
            note_meta(r.get("example_id", ""), (r.get("source_ids") or [""])[0], r.get("source_units", []), key)
    for r in cand_rows["stage_a_draft"]:
        note_meta(r.get("example_id", ""), (r.get("source_ids") or [""])[0], r.get("source_units", []), "stage_a_draft_v1")
    for r in seed:
        note_meta(r["candidate_id"], r.get("source_id", ""), [], "seed_v1")
    for r in gold_v3:
        note_meta(r["revision_id"], (r.get("source_ids") or [""])[0], r.get("source_units", []), "gold_v3")
        note_meta(r["original_example_id"], (r.get("source_ids") or [""])[0], r.get("source_units", []), "gold_v3")

    # resolve unit ids actually present in the training corpus
    wanted_units = set()
    for meta in subj_meta.values():
        wanted_units |= meta["unit_ids"]
    units = load_units(wanted=wanted_units)
    missing_units = sorted(wanted_units - set(units))

    # ---------------- helper closures --------------------------------------
    def rights_of_source(source_id: str) -> dict:
        if not source_id:
            return {"allowed": False, "rights_status": "UNKNOWN_NO_SOURCE", "basis": "no source id on record", "audit_category": "", "flags": []}
        return rights_for(source_id, manifest, audit, jainqq)

    def provenance_of(subject_id: str) -> dict:
        meta = subj_meta.get(subject_id, {})
        unit_ids = sorted(meta.get("unit_ids") or [])
        srcs = sorted(meta.get("source_ids") or [])
        if not srcs:
            return {"status": "INCOMPLETE_NO_SOURCE", "text_ids": [], "source_ids": []}
        if not unit_ids:
            return {"status": "INCOMPLETE_NO_UNIT_ID", "text_ids": [], "source_ids": srcs}
        present = [u for u in unit_ids if u in units]
        if not present:
            return {"status": "INCOMPLETE_UNIT_NOT_IN_CORPUS", "text_ids": unit_ids, "source_ids": srcs}
        if len(present) < len(unit_ids):
            return {"status": "PARTIAL_UNIT_RESOLUTION", "text_ids": present, "source_ids": srcs}
        return {"status": "COMPLETE", "text_ids": present, "source_ids": srcs}

    # ---------------- decision groups (duplicate approvals) ------------------
    def group_of(rows, id_field):
        c = Counter(r.get(id_field, "") for r in rows)
        return c

    t51_rows = review_rows["T51_candidate_review"]
    t51_group = group_of(t51_rows, "candidate_id")
    t47_rows = review_rows["T47_revision_review"]
    t47_group = group_of(t47_rows, "example_id")
    t44_rows = review_rows["T44_gold_review"]
    t44_group = group_of(t44_rows, "example_id")

    # approval-record dispositions -----------------------------------------
    # returns (state, reason, classification, disposition)
    def disposition_for(task, row):
        decision = (row.get("decision") or "").strip().upper()
        if task == "T41_stage_a_review_queue":
            rec = row.get("recommended_action", "")
            return (
                STATE_NOT_VERIFIED,
                "Task 41 review-queue record with automated recommendation %r only; no human decision submitted" % rec,
                CLASS_B if rec == "REVISE" else (CLASS_C if rec == "REJECT" else CLASS_D),
                "PENDING_HUMAN_REVIEW",
            )
        if task == "T50_review":
            return (STATE_NOT_VERIFIED, "Task 50 review file exists but is empty (0 records)", CLASS_D, "NOT_RECORDED")
        subject = row.get("candidate_id") or row.get("example_id") or ""
        if not decision:
            return (STATE_NOT_VERIFIED, "review record has an empty decision field", CLASS_D, "NOT_RECORDED")

        # APPROVE
        if decision == "APPROVE":
            if task == "T51_candidate_review" and subject in seed_by_cand:
                s = seed_by_cand[subject]
                dup = t51_group[subject]
                extra = "; approval record %d of %d for the same candidate (deduplicated to 1 seed row)" % (
                    1, dup) if dup > 1 else ""
                return (
                    STATE_PRESENT,
                    "candidate present in sft_seed_v1.jsonl as %s%s" % (s.get("id", ""), extra),
                    CLASS_A,
                    "PRESENT_AS_" + str(s.get("id", "")),
                )
            if task == "T47_revision_review" and (subject in gold3_by_orig or row.get("revision_id") in gold3_by_rev):
                rev = gold3_by_rev.get(row.get("revision_id")) or gold3_by_orig.get(subject)
                return (
                    STATE_PRESENT,
                    "approved revision present in sft_gold_v3.jsonl as %s" % rev.get("revision_id"),
                    CLASS_A,
                    "PRESENT_AS_" + rev.get("revision_id"),
                )
            if task == "T44_gold_review":
                # later human-approved revision supersedes this record
                for rev in gold_v3:
                    if rev.get("original_example_id") == subject:
                        return (
                            STATE_PRESENT,
                            "original approved text superseded by human-requested revision; approved revision present as %s in sft_gold_v3.jsonl" % rev.get("revision_id"),
                            CLASS_A,
                            "PRESENT_AS_" + rev.get("revision_id"),
                        )
                return (
                    STATE_RECOVERABLE,
                    "human APPROVE recorded but no matching row in the HUMAN_VERIFIED inventory; original draft recoverable from sft_stage_a_draft_v1.jsonl",
                    CLASS_A,
                    "RECOVERABLE_NOT_IN_INVENTORY",
                )
            return (
                STATE_RECOVERABLE,
                "human APPROVE recorded but candidate not present in the HUMAN_VERIFIED inventory",
                CLASS_A,
                "RECOVERABLE_NOT_IN_INVENTORY",
            )

        # REVISE
        if decision == "REVISE":
            exist = []
            if subject in subj_meta:
                exist = sorted(subj_meta[subject]["origins"])
            if exist:
                return (
                    STATE_RECOVERABLE,
                    "human REVISE recorded; record still available in %s" % ", ".join(exist),
                    CLASS_B,
                    "REVISION_REQUIRED",
                )
            return (STATE_NOT_VERIFIED, "human REVISE recorded but no candidate record located", CLASS_B, "REVISION_REQUIRED_LOST")

        # REJECT
        if decision == "REJECT":
            note = (row.get("reviewer_notes") or row.get("review_notes") or "").strip()
            reason = "human REJECT recorded at %s" % (row.get("reviewed_at") or row.get("review_timestamp") or "")
            if note:
                reason += "; reviewer reason: %s" % note[:160]
            return (STATE_EXCLUDED, reason, CLASS_C, "EXCLUDED_BY_HUMAN_REJECT")

        return (STATE_NOT_VERIFIED, "unrecognised decision %r" % decision, CLASS_D, "NOT_RECORDED")

    # ---------------- build reconciliation table ----------------------------
    table = []

    def add_rows(task, rows, id_field, task_num):
        for idx, row in enumerate(rows):
            subject = row.get(id_field) or row.get("example_id") or row.get("candidate_id") or ""
            if not subject and isinstance(row.get("original_draft"), dict):
                subject = row["original_draft"].get("example_id", "")
            decision = (row.get("decision") or "").strip().upper()
            state, reason, klass, disp = disposition_for(task, row)
            meta = subj_meta.get(subject, {})
            src = sorted(meta.get("source_ids") or [])
            src0 = src[0] if src else (subject_source(subject) or "")
            r = rights_of_source(src0) if src0 else {"rights_status": "UNKNOWN_NO_SOURCE", "basis": ""}
            prov = provenance_of(subject)
            table.append({
                "review_task": task_num,
                "review_file": REVIEW_FILES[task],
                "record_index": idx,
                "record_key": "%s#%d" % (task, idx),
                "subject_id": subject,
                "decision": decision,
                "decision_timestamp": row.get("reviewed_at") or row.get("review_timestamp") or "",
                "reviewer": row.get("reviewer", ""),
                "decision_group_size": (t51_group if task == "T51_candidate_review" else t47_group if task == "T47_revision_review" else t44_group if task == "T44_gold_review" else Counter()).get(subject, 0),
                "automated_recommendation": row.get("recommended_action", ""),
                "state": state,
                "reason": reason,
                "classification": klass,
                "final_disposition": disp,
                "source_id": src0,
                "rights_status": r.get("rights_status", ""),
                "provenance_status": prov.get("status", ""),
                "verified_inventory_row": disp if disp.startswith("PRESENT_AS_") else "",
                "reviewer_notes": (row.get("reviewer_notes") or row.get("review_notes") or ""),
            })

    add_rows("T41_stage_a_review_queue", review_rows["T41_stage_a_review_queue"], "example_id", "Task41")
    add_rows("T44_gold_review", review_rows["T44_gold_review"], "example_id", "Task44")
    add_rows("T47_revision_review", review_rows["T47_revision_review"], "example_id", "Task47")
    add_rows("T50_review", review_rows["T50_review"], "example_id", "Task50")
    add_rows("T51_candidate_review", review_rows["T51_candidate_review"], "candidate_id", "Task51")

    # ---------------- assertions -------------------------------------------
    t51_approvals = [r for r in table if r["review_task"] == "Task51" and r["decision"] == "APPROVE"]
    assert len(t51_approvals) == TASK51_APPROVALS_EXPECTED, "expected %d T51 approvals, got %d" % (
        TASK51_APPROVALS_EXPECTED, len(t51_approvals))
    for row in t51_approvals:
        assert row["state"] in VALID_STATES, row
    t51_states = Counter(r["state"] for r in t51_approvals)
    assert set(t51_states) <= {STATE_PRESENT}, "unexpected T51 approval states: %s" % t51_states

    all_states = Counter(r["state"] for r in table)
    for s in all_states:
        assert s in VALID_STATES, s

    # no approved example may be missing from the reconciled output
    reconciled_sources = []

    # ---- seed rows ---------------------------------------------------------
    seed_ids_by_cand = {r["candidate_id"]: r["id"] for r in seed}
    for r in seed:
        cid = r["candidate_id"]
        meta = subj_meta.get(cid, {})
        src = r.get("source_id", "")
        man = manifest.get(src, {})
        rights = rights_of_source(src)
        unit_ids = sorted(meta.get("unit_ids") or [])
        text_id = unit_ids[0] if unit_ids else ""
        unit = units.get(text_id, {}) if text_id else {}
        prov_status = provenance_of(cid)["status"]
        decisions = [x for x in t51_rows if x.get("candidate_id") == cid]
        approvers = [x for x in decisions if (x.get("decision") or "").upper() == "APPROVE"]
        rejected = [x for x in decisions if (x.get("decision") or "").upper() == "REJECT"]
        notes = []
        if rejected:
            notes.append("CONFLICTING_HUMAN_DECISIONS: %d APPROVE vs %d REJECT on the same candidate; kept because >=1 human APPROVE exists (rule: any APPROVE keeps the example). Never silently dropped." % (
                len(approvers), len(rejected)))
        if prov_status != "COMPLETE":
            notes.append("PROVENANCE_GAP: %s" % prov_status)
        if rights.get("flags"):
            notes.extend(rights["flags"])
        if not man.get("knowledge_layer"):
            notes.append("MANIFEST_KNOWLEDGE_LAYER_EMPTY -> mapped to MIXED")
        if not man.get("religious_scope"):
            notes.append("MANIFEST_RELIGIOUS_SCOPE_EMPTY -> mapped to UNKNOWN")
        q, a = r.get("question", ""), r.get("answer", "")
        messages = [{"role": "user", "content": q}, {"role": "assistant", "content": a}]
        reconciled_sources.append({
            "example_id": r.get("id", ""),
            "review_ref": cid,
            "version": "1.0",
            "task_category": "general_qa",
            "category": r.get("category", ""),
            "question": q,
            "answer": a,
            "messages": messages,
            "source_id": src,
            "parent_source_id": man.get("parent_source_id", ""),
            "source_title": r.get("source_title") or man.get("title", ""),
            "locator": (unit.get("source_locator") or {}),
            "religious_scope": map_religious_scope(man.get("religious_scope", "")),
            "religious_scope_manifest_raw": man.get("religious_scope", ""),
            "knowledge_layer": map_knowledge_layer(man.get("knowledge_layer", "")),
            "knowledge_layer_manifest_raw": man.get("knowledge_layer", ""),
            "canonical_status": canonical_status(man),
            "teacher_or_author": man.get("author", ""),
            "lineage": r.get("lineage", ""),
            "language": r.get("language", ""),
            "tradition": man.get("tradition", ""),
            "sect": man.get("sect", ""),
            "provenance": {
                "source_id": src,
                "text_id": text_id,
                "unit_ids": unit_ids,
                "title": man.get("title", ""),
                "author": man.get("author", ""),
                "publication_year": man.get("publication_year", ""),
                "language": man.get("language", ""),
                "knowledge_layer": map_knowledge_layer(man.get("knowledge_layer", "")),
                "religious_scope": map_religious_scope(man.get("religious_scope", "")),
                "sect": man.get("sect", ""),
                "sect_confidence": (man.get("sect_confidence") or "UNKNOWN").upper(),
                "teacher_or_author": man.get("author", ""),
                "lineage": r.get("lineage", ""),
                "source_quality": (man.get("source_quality") or "UNKNOWN").upper(),
                "locator": {"page": (unit.get("source_locator") or {}).get("page"), "section": (unit.get("source_locator") or {}).get("section")},
                "license_status": rights.get("rights_status", ""),
                "citation_text": "%s (%s)" % (man.get("title", ""), src),
                "status": prov_status,
                "unit_found_in_training_corpus": bool(unit),
                "artifact_sha256": (unit.get("provenance") or {}).get("artifact_sha256", ""),
                "repository": (unit.get("provenance") or {}).get("repository", man.get("repository", "")),
                "source_url": (unit.get("provenance") or {}).get("source_url", man.get("source_url", "")),
            },
            "rights_status": rights.get("rights_status", ""),
            "rights_basis": rights.get("basis", ""),
            "rights_audit_category": rights.get("audit_category", ""),
            "origin": {"synthetic": False, "method": "expert_reviewed", "reviewer": "HUMAN_REVIEWER", "confidence": "high"},
            "split": split_candidate(src, split_of),
            "split_candidate": split_candidate(src, split_of),
            "human_review_status": "HUMAN_VERIFIED",
            "reconciliation_state": STATE_PRESENT,
            "human_review_evidence": {
                "task": "Task51",
                "file": REVIEW_FILES["T51_candidate_review"],
                "approvals": len(approvers),
                "rejections": len(rejected),
                "revisions": len([x for x in decisions if (x.get("decision") or "").upper() == "REVISE"]),
                "first_decision_at": min([x.get("reviewed_at", "") for x in decisions], default=""),
                "last_decision_at": max([x.get("reviewed_at", "") for x in decisions], default=""),
                "reviewer_notes": [x.get("reviewer_notes", "") for x in decisions if x.get("reviewer_notes")],
                "review_count": r.get("review_count", len(decisions)),
            },
            "quality_flags": notes + ["needs_review"] if notes else ["needs_review"],
            "audit_notes": notes,
        })

    # ---- gold_v3 rows ------------------------------------------------------
    task_category_map = {"JAIN_CONCEPT": "general_qa", "JAIN_PRACTICE": "general_qa", "AGAM_EXPLANATION": "general_qa"}
    for r in gold_v3:
        src = (r.get("source_ids") or [""])[0]
        man = manifest.get(src, {})
        rights = rights_of_source(src)
        unit_ids = list(r.get("source_units") or [])
        text_id = unit_ids[0] if unit_ids else ""
        unit = units.get(text_id, {}) if text_id else {}
        prov_status = provenance_of(r.get("revision_id", ""))["status"]
        notes = []
        if prov_status != "COMPLETE":
            notes.append("PROVENANCE_GAP: %s" % prov_status)
        if r.get("needs_human_review"):
            notes.append("SOURCE_RECORD_FLAG_NEEDS_HUMAN_REVIEW=True left by the Task 47 builder; human APPROVE decision %s overrides it - flagged, not silently cleared" % r.get("review_timestamp", ""))
        if rights.get("flags"):
            notes.extend(rights["flags"])
        q = r.get("messages", [{}])[0].get("content", "") if r.get("messages") else r.get("revised_question", "")
        a = r.get("messages", [{}])[1].get("content", "") if r.get("messages") and len(r.get("messages")) > 1 else r.get("revised_answer", "")
        if not r.get("messages"):
            messages = [{"role": "user", "content": r.get("revised_question", "")}, {"role": "assistant", "content": r.get("revised_answer", "")}]
        else:
            messages = r.get("messages")
        reconciled_sources.append({
            "example_id": r.get("revision_id", ""),
            "review_ref": r.get("original_example_id", ""),
            "version": "1.0",
            "task_category": task_category_map.get(r.get("category", ""), "general_qa"),
            "category": r.get("category", ""),
            "question": q,
            "answer": a,
            "messages": messages,
            "source_id": src,
            "parent_source_id": man.get("parent_source_id", ""),
            "source_title": (r.get("source_grounding") or {}).get("source_title") or man.get("title", ""),
            "locator": (unit.get("source_locator") or {}),
            "religious_scope": map_religious_scope(man.get("religious_scope", "")),
            "religious_scope_manifest_raw": man.get("religious_scope", ""),
            "knowledge_layer": map_knowledge_layer(man.get("knowledge_layer", "")),
            "knowledge_layer_manifest_raw": man.get("knowledge_layer", ""),
            "canonical_status": canonical_status(man),
            "teacher_or_author": (r.get("teacher_attribution") or {}).get("teacher") or man.get("author", ""),
            "lineage": r.get("lineage", ""),
            "language": r.get("language", ""),
            "tradition": man.get("tradition", ""),
            "sect": man.get("sect", ""),
            "provenance": {
                "source_id": src,
                "text_id": text_id,
                "text_ids": unit_ids,
                "title": man.get("title", ""),
                "author": man.get("author", ""),
                "publication_year": man.get("publication_year", ""),
                "language": man.get("language", ""),
                "knowledge_layer": map_knowledge_layer(man.get("knowledge_layer", "")),
                "religious_scope": map_religious_scope(man.get("religious_scope", "")),
                "sect": man.get("sect", ""),
                "sect_confidence": (man.get("sect_confidence") or "UNKNOWN").upper(),
                "teacher_or_author": (r.get("teacher_attribution") or {}).get("teacher") or man.get("author", ""),
                "lineage": r.get("lineage", ""),
                "source_quality": (man.get("source_quality") or "UNKNOWN").upper(),
                "locator": {"page": (unit.get("source_locator") or {}).get("page"), "section": (unit.get("source_locator") or {}).get("section")},
                "license_status": rights.get("rights_status", ""),
                "citation_text": "%s (%s)" % (man.get("title", ""), src),
                "status": prov_status,
                "unit_found_in_training_corpus": bool(unit),
                "artifact_sha256": (unit.get("provenance") or {}).get("artifact_sha256", ""),
                "repository": (unit.get("provenance") or {}).get("repository", man.get("repository", "")),
                "source_url": (unit.get("provenance") or {}).get("source_url", man.get("source_url", "")),
            },
            "rights_status": rights.get("rights_status", ""),
            "rights_basis": rights.get("basis", ""),
            "rights_audit_category": rights.get("audit_category", ""),
            "origin": {"synthetic": False, "method": "expert_reviewed", "reviewer": "HUMAN_REVIEWER", "confidence": "high"},
            "split": split_candidate(src, split_of),
            "split_candidate": split_candidate(src, split_of),
            "human_review_status": "HUMAN_VERIFIED",
            "reconciliation_state": STATE_PRESENT,
            "human_review_evidence": {
                "task": "Task47",
                "file": REVIEW_FILES["T47_revision_review"],
                "approvals": 1,
                "revisions": 0,
                "rejections": 0,
                "first_decision_at": r.get("review_timestamp", ""),
                "last_decision_at": r.get("review_timestamp", ""),
                "reviewer_notes": [r.get("reviewer_feedback", "")],
            },
            "quality_flags": (notes + ["needs_review"]) if notes else ["needs_review"],
            "audit_notes": notes,
        })

    # ---- evidence verification + unit recovery for approved rows -----------
    for row in reconciled_sources:
        prov = row["provenance"]
        src = row["source_id"]
        spans = quoted_spans(row.get("answer", ""))
        cited = [u for u in (prov.get("unit_ids") or prov.get("text_ids") or []) if u]
        if prov.get("text_id"):
            cited = list(dict.fromkeys([prov["text_id"]] + cited))
        recs = [units[u] for u in cited if u in units]
        prov["cited_unit_ids"] = cited
        prov["cited_units_found"] = [u for u in cited if u in units]
        result = quote_in_units(spans, recs)
        if spans and not recs:
            hits = find_unit_by_text(src, spans)
            if hits:
                recovered = hits[0]["unit"] or hits[0]["id"]
                prov["recovered_text_ids"] = [h["unit"] or h["id"] for h in hits]
                if not prov.get("text_id"):
                    prov["text_id"] = recovered
                    prov["unit_found_in_training_corpus"] = True
                    prov["status"] = "RECOVERED_BY_TEXT_MATCH"
                result = {"checked": True, "result": "VERIFIED_IN_RECOVERED_UNIT", "missing": [],
                          "recovered_text_ids": prov["recovered_text_ids"]}
        elif spans and recs and result.get("result") in ("QUOTE_NOT_FOUND_IN_CITED_UNIT", "NO_CITED_UNIT_TEXT"):
            hits = find_unit_by_text(src, spans)
            if hits:
                prov["recovered_text_ids"] = [h["unit"] or h["id"] for h in hits]
                result = {"checked": True, "result": "CITED_UNIT_MISMATCH_TEXT_FOUND_ELSEWHERE",
                          "missing": result.get("missing", []), "recovered_text_ids": prov["recovered_text_ids"]}
        prov["quote_verification"] = result
        if prov.get("status") in ("INCOMPLETE_NO_UNIT_ID", "INCOMPLETE_UNIT_NOT_IN_CORPUS") and prov.get("unit_found_in_training_corpus"):
            prov["status"] = "RECOVERED_BY_TEXT_MATCH"
        if result.get("checked"):
            if result["result"] in ("VERIFIED", "VERIFIED_FUZZY", "VERIFIED_IN_RECOVERED_UNIT"):
                row["audit_notes"].append("QUOTE_VERIFIED_IN_CORPUS_UNIT")
            else:
                row["audit_notes"].append("EVIDENCE_QUOTE_NOT_MATCHED: %s %s - human confirmation required before training" % (
                    result["result"], result.get("missing", [])))
                row["quality_flags"].append("low_confidence")

    # duplicate detection across the reconciled inventory
    seen_q = {}
    for row in reconciled_sources:
        key = normalize_q(row["question"])
        if key in seen_q:
            row["audit_notes"].append("NEAR_DUPLICATE_QUESTION: same question as %s in this inventory (both kept - both human-approved; no silent discard)" % seen_q[key])
            row["quality_flags"].append("conflicting_info")
        else:
            seen_q[key] = row["example_id"]

    # ---------------- write outputs ----------------------------------------
    out_jsonl = os.path.join(SFT_DIR, "sft_reconciled_v1.jsonl")
    write_jsonl(out_jsonl, reconciled_sources)

    out_csv = os.path.join(SFT_DIR, "sft_reconciliation_table.csv")
    fields = ["review_task", "review_file", "record_index", "record_key", "subject_id", "decision",
              "decision_timestamp", "reviewer", "decision_group_size", "automated_recommendation",
              "state", "reason", "classification", "final_disposition", "source_id", "rights_status",
              "provenance_status", "verified_inventory_row", "reviewer_notes"]
    with open(out_csv, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in table:
            w.writerow({k: row.get(k, "") for k in fields})

    # ---------------- inventory of every Task 40-52 artifact ---------------
    inventory = []
    for task, fname in list(REVIEW_FILES.items()) + [(k, v) for k, v in CANDIDATE_FILES.items()]:
        rows = read_jsonl(os.path.join(SFT_DIR, fname))
        decisions = Counter((r.get("decision") or r.get("review_decision") or r.get("status") or r.get("review_status") or "") for r in rows)
        inventory.append({
            "task": task,
            "file": fname,
            "rows": len(rows),
            "decision_breakdown": dict(decisions),
        })

    summary = {
        "task": 61,
        "stage": "reconciliation",
        "review_artifacts_inspected": inventory,
        "reconciliation_records_total": len(table),
        "state_counts_all_records": dict(all_states),
        "task51_approval_records": len(t51_approvals),
        "task51_approval_states": dict(t51_states),
        "task51_approval_detail": [
            {"subject_id": r["subject_id"], "decision_timestamp": r["decision_timestamp"],
             "decision_group_size": r["decision_group_size"], "state": r["state"],
             "final_disposition": r["final_disposition"], "reason": r["reason"],
             "rights_status": r["rights_status"], "provenance_status": r["provenance_status"],
             "classification": r["classification"]}
            for r in t51_approvals
        ],
        "task51_decision_counts": dict(Counter((r.get("decision") or "") for r in t51_rows)),
        "task51_unique_candidates_reviewed": len(set(r.get("candidate_id") for r in t51_rows)),
        "task51_queue_rows": len(cand_rows["task51_review_priority_v1"]),
        "existing_human_verified_inventory": [
            {"example_id": r["example_id"], "origin_file": "sft_seed_v1.jsonl" if str(r["example_id"]).startswith("SFT-SEED") else "sft_gold_v3.jsonl",
             "source_id": r["source_id"], "review_ref": r["review_ref"], "rights_status": r["rights_status"],
             "provenance_status": r["provenance"]["status"], "reconciliation_state": r["reconciliation_state"],
             "audit_notes": r["audit_notes"]}
            for r in reconciled_sources
        ],
        "existing_human_verified_count": len(reconciled_sources),
        "seed_rows": len(seed),
        "gold_v3_rows": len(gold_v3),
        "discrepancy_explained": {
            "task51_approval_records": len(t51_approvals),
            "unique_candidates_approved": len(set(r["subject_id"] for r in t51_approvals)),
            "seed_rows": len(seed),
            "explanation": "11 APPROVE review records collapse to 6 unique candidate_ids (Task 51 review queue contains duplicate rows: 17 queue rows for 8 unique candidates, 18 review records for 8 unique candidates). Seed builder rule was 'any APPROVE on a candidate keeps it', so 6 unique approved candidates -> 6 seed rows. No approved candidate was lost.",
            "duplicate_approval_records_collapsed": len(t51_approvals) - len(set(r["subject_id"] for r in t51_approvals)),
        },
        "conflicting_reviews": [
            {"candidate_id": cid, "decisions": [d for d in decs]}
            for cid, decs in sorted(
                ((cid, [(x.get("decision") or "") for x in t51_rows if x.get("candidate_id") == cid])
                 for cid in set(x.get("candidate_id") for x in t51_rows)),
                key=lambda kv: kv[0])
            if len(set(decs)) > 1
        ],
        "unit_resolution": {
            "unit_ids_referenced": len(wanted_units),
            "unit_ids_found_in_training_corpus": len(wanted_units) - len(missing_units),
            "unit_ids_missing": missing_units,
        },
        "outputs": {
            "reconciled": os.path.relpath(out_jsonl, ROOT),
            "reconciliation_table": os.path.relpath(out_csv, ROOT),
        },
    }
    summary_path = os.path.join(SFT_DIR, "_task61_reconciliation_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)

    print("reconciliation records: %d" % len(table))
    print("states: %s" % dict(all_states))
    print("T51 approvals: %d -> %s" % (len(t51_approvals), dict(t51_states)))
    print("reconciled inventory rows: %d" % len(reconciled_sources))
    print("wrote %s" % out_jsonl)
    print("wrote %s" % out_csv)
    print("wrote %s" % summary_path)


if __name__ == "__main__":
    main()
