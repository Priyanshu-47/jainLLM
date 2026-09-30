#!/usr/bin/env python3
"""TASK 62 human review server.

Reuses the Tasks 44-51 review-server pattern (tools/sft_review_server_task5*.py)
and adds the Task 62 requirements:

  * shows every field the reviewer needs (question, proposed answer, source text,
    provenance, rights, origin, manifest row, evidence quote)
  * per-item rubric checklist (11 conditions, priority items highlighted)
  * APPROVE / REVISE / REJECT
  * REVISE is refused without reviewer feedback
  * REJECT is refused without a rejection reason
  * APPROVE keeps the exact reviewed answer unless the reviewer edits it
  * writes data/training/sft_human_review_v2.jsonl in the Task 62 contract shape
  * never overwrites the candidate source records

Records are keyed by example_id: re-submitting a decision replaces the previous
one for that example_id in the v2 file (append-only history is kept separately).
"""
import json
import os
import socketserver
import threading
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

BASE_DIR = "/home/azureuser/jainLLM/svk-corpus"
QUEUE_PATH = os.environ.get(
    "TASK62_QUEUE_PATH",
    os.path.join(BASE_DIR, "data/training/sft_task62_review_queue_v1.jsonl"))
REVIEW_PATH = os.environ.get(
    "TASK62_REVIEW_PATH",
    os.path.join(BASE_DIR, "data/training/sft_human_review_v2.jsonl"))
HISTORY_PATH = os.environ.get(
    "TASK62_HISTORY_PATH",
    os.path.join(BASE_DIR, "data/training/sft_human_review_v2_history.jsonl"))
PORT = int(os.environ.get("TASK62_REVIEW_PORT", "8084"))
REVIEWER = os.environ.get("TASK62_REVIEWER", "HUMAN_REVIEWER")

_lock = threading.Lock()
WRITES = {"n": 0}


def esc(text):
    return (str(text or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def load_queue():
    rows = []
    with open(QUEUE_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_reviews():
    """example_id -> latest review record."""
    state = OrderedDict()
    if not os.path.exists(REVIEW_PATH):
        return state
    with open(REVIEW_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            eid = rec.get("example_id", "")
            if eid:
                state[eid] = rec
    return state


def write_review(record):
    """Atomically rewrite the v2 file (one row per example_id) + append history."""
    with _lock:
        state = load_reviews()
        state[record["example_id"]] = record
        tmp = REVIEW_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            for rec in state.values():
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        os.replace(tmp, REVIEW_PATH)
        with open(HISTORY_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        WRITES["n"] += 1


def build_record(row, params, error_sink):
    """Assemble a Task 62 review record; append problems to error_sink."""
    decision = (params.get("decision", [""])[0] or "").strip().upper()
    feedback = (params.get("feedback", [""])[0] or "").strip()
    edited = params.get("reviewed_answer", [""])[0]
    edited = edited if edited is not None else ""

    if decision not in ("APPROVE", "REVISE", "REJECT"):
        error_sink.append("Select APPROVE, REVISE or REJECT.")
    if decision == "REVISE" and not feedback:
        error_sink.append("REVISE requires reviewer feedback describing what must change.")
    if decision == "REJECT" and not feedback:
        error_sink.append("REJECT requires a rejection reason.")

    original = row["answer"]
    if decision == "APPROVE":
        # preserve the exact answer unless the reviewer explicitly edited it
        reviewed = edited if edited.strip() and edited != original else original
        if edited and edited != original and not (params.get("edited_flag", [""])[0]):
            error_sink.append("The answer text differs from the original. Tick "
                              "'I intentionally edited this answer' to confirm the edit.")
    elif decision == "REVISE":
        reviewed = edited
    else:
        reviewed = ""

    rubric = OrderedDict()
    for item in row.get("review_checklist", []):
        key = item["item"]
        value = (params.get("rubric_" + key, [""])[0] or "").strip()
        rubric[key] = value or "NOT_ASSESSED"

    if decision == "REVISE" and all(v == "NOT_ASSESSED" for v in rubric.values()):
        error_sink.append("REVISE must record at least one rubric item as FAIL "
                          "(state what failed).")
    if decision == "REJECT" and all(v == "NOT_ASSESSED" for v in rubric.values()):
        error_sink.append("REJECT must record at least one rubric item as FAIL.")

    provenance = row.get("provenance", {})
    return OrderedDict([
        ("review_id", "T62-REVIEW-%s" % row["review_id"].replace("T61-CAND-", "")),
        ("example_id", row["example_id"]),
        ("decision", decision),
        ("reviewer", REVIEWER),
        ("review_timestamp", datetime.now(timezone.utc).isoformat()),
        ("feedback", feedback),
        ("original_answer", original),
        ("reviewed_answer", reviewed),
        ("review_rubric", rubric),
        ("rubric_instructions", [
            {"item": i["item"], "instruction": i["instruction"],
             "high_priority": i["high_priority"]}
            for i in row.get("review_checklist", [])
        ]),
        ("source_id", row["source_id"]),
        ("provenance", provenance),
        ("rights_status", row.get("rights_status", "")),
        ("category", row["category"]),
        ("queue", row.get("queue", "")),
        ("question", row["question"]),
        ("answer_edited", bool(decision != "REJECT" and reviewed and reviewed != original)),
        ("reviewer_notes", feedback),
    ])


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:#f4f5f7;color:#2b2b33;line-height:1.6}
.wrap{max-width:1080px;margin:0 auto;padding:18px}
.top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;
 background:#fff;border-radius:10px;padding:12px 16px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:16px}
.top a{color:#3f3f8f;text-decoration:none;padding:6px 10px;border-radius:6px;font-size:14px}
.top a:hover{background:#eef}
.badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;letter-spacing:.4px}
.bA{background:#ffe0e0;color:#a11}
.bB{background:#fff0cc;color:#862}
.bC{background:#e0e8ff;color:#246}
.bD{background:#e6f4ea;color:#1a7f37}
.bR{background:#f3e8ff;color:#6a1b9a}
.card{background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.08);padding:22px;margin-bottom:16px}
.lab{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#8a8a99;font-weight:700;margin-bottom:6px}
.q{font-size:18px;font-weight:650;line-height:1.5}
.ans{font-size:15px;line-height:1.75;background:#f8f9fc;padding:16px 18px;border-radius:8px;
 border-left:4px solid #4a4a9a;white-space:pre-wrap;word-break:break-word}
.txt{font-size:14px;line-height:1.7;white-space:pre-wrap;word-break:break-word;background:#fbfbfd;
 padding:14px 16px;border-radius:8px;border:1px solid #e6e6ee;max-height:340px;overflow:auto}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:8px}
.cell{background:#f8f9fb;padding:9px 12px;border-radius:6px;font-size:13px;word-break:break-word}
.k{font-weight:650;color:#5a5a6e;display:block;font-size:11px;text-transform:uppercase;letter-spacing:.5px}
.ok{color:#1a7f37;font-weight:650}.warn{color:#b36b00;font-weight:650}.bad2{color:#b3261e;font-weight:650}
.rule{background:#eef3ff;border:1px solid #c9d6ff;border-radius:8px;padding:14px 16px;margin-bottom:16px;font-size:13px}
.rule b{color:#1d3a8a}
.rule ol{margin:8px 0 0 20px}.rule li{margin-bottom:4px}
.check{border:1px solid #e6e6ee;border-radius:8px;padding:6px 12px;margin-bottom:6px;font-size:13.5px;
 display:flex;gap:10px;align-items:flex-start;background:#fcfcfe}
.check.hi{border-color:#f0c36d;background:#fffaf0}
.check .instr{flex:1}
.tag{font-size:10px;font-weight:700;padding:1px 7px;border-radius:999px;background:#f0c36d;color:#5b3a00;white-space:nowrap}
.dec{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:14px}
.dec label{display:flex;align-items:center;gap:7px;cursor:pointer;padding:11px 20px;background:#fff;
 border:2px solid #dcdce6;border-radius:8px;font-weight:650;font-size:15px}
.dec label:hover{border-color:#4a4a9a}
.dec input:checked+span.ap{color:#1a7f37}.dec input:checked+span.rv{color:#b36b00}
.dec input:checked+span.rj{color:#b3261e}
.dec label:has(input:checked){border-color:#4a4a9a;background:#f2f2ff}
textarea{width:100%;padding:11px 13px;border:1px solid #dcdce6;border-radius:8px;font-family:inherit;
 font-size:14px;resize:vertical;background:#fff}
textarea:focus{outline:none;border-color:#4a4a9a}
button{background:#3f3f8f;color:#fff;border:none;padding:13px 26px;border-radius:8px;font-size:15px;
 font-weight:650;cursor:pointer;margin-top:14px}
button:hover{background:#2f2f75}
.err{background:#fdecea;border:1px solid #f5c6c0;color:#8a1f17;border-radius:8px;padding:12px 16px;
 margin-bottom:14px;font-size:14px}
.stats{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}
.stat{background:#fff;padding:14px 20px;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.08);
 text-align:center;min-width:104px}
.n{font-size:26px;font-weight:750;color:#3f3f8f}
.l{font-size:10.5px;text-transform:uppercase;letter-spacing:1px;color:#8a8a99}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;
 box-shadow:0 1px 4px rgba(0,0,0,.08)}
th{background:#3f3f8f;color:#fff;padding:11px 10px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.7px}
td{padding:9px 10px;border-bottom:1px solid #eee;font-size:13.5px;vertical-align:top}
tr:hover{background:#f8f9ff}
a{color:#3f3f8f;text-decoration:none}
.mono{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:#666}
.qnav{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:13px}
details summary{cursor:pointer;font-weight:650;color:#3f3f8f;font-size:13.5px;margin-bottom:8px}
"""


def render_example(idx, queue, reviews, errors=None, saved=False):
    rows = queue
    total = len(rows)
    idx = max(0, min(idx, total - 1))
    r = rows[idx]
    eid = r["example_id"]
    prev = reviews.get(eid, {})
    dec = prev.get("decision", "")
    feedback = prev.get("feedback", "")
    reviewed = prev.get("reviewed_answer", "")
    rubric_prev = prev.get("review_rubric", {}) or {}

    checked = {d: ("checked" if dec == d else "") for d in ("APPROVE", "REVISE", "REJECT")}
    edited_default = reviewed if reviewed and reviewed != r["answer"] else r["answer"]
    edited_flag = "checked" if (reviewed and reviewed != r["answer"]) else ""

    flags = []
    if r.get("rights_flags"):
        flags.append('<span class="badge" style="background:#fff3cd;color:#856404">RIGHTS FLAG: %s</span>'
                     % esc("; ".join(r["rights_flags"])[:220]))
    if r.get("origin", {}).get("synthetic"):
        flags.append('<span class="badge" style="background:#e8eaf6;color:#303f9f">SYNTHETIC ORIGIN</span>')
    if not r.get("source_text"):
        flags.append('<span class="badge" style="background:#eceff1;color:#455a64">MANIFEST-GROUNDED (no corpus unit)</span>')
    nd = r.get("near_duplicates") or []
    if nd:
        items = "".join(
            "<li><span class='mono'>%s</span> (J=%.2f%s) &mdash; %s</li>"
            % (esc(x["example_id"]), x["similarity"],
               "" if x["same_source"] else ", <b>OTHER SOURCE</b>",
               esc(x["question"][:140]))
            for x in nd[:8])
        more = ("<li>... and %d more</li>" % (len(nd) - 8)) if len(nd) > 8 else ""
        flags.append(
            '<span class="badge" style="background:#fff3cd;color:#856404">'
            '%d NEAR-DUPLICATE QUESTION(S) IN THIS SOURCE</span>' % len(nd))
        r["_near_dup_html"] = (
            '<details style="margin-top:8px"><summary style="cursor:pointer;'
            'font-weight:650;color:#856404">%d near-duplicate question(s) in this '
            'source &mdash; inspect manually before approving</summary>'
            '<ul style="margin:8px 0 0 20px;font-size:13.5px">%s%s</ul>'
            '<div style="font-size:12.5px;color:#8a8a99;margin-top:6px">Cross-source '
            'near-duplicates at J&gt;=0.85: %d (leakage check).</div></details>'
            % (len(nd), items, more, len(r.get("near_dup_cross_source") or [])))
    if r.get("canonical_status") != r.get("canonical_status_derived_from_manifest"):
        flags.append('<span class="badge" style="background:#fdecea;color:#8a1f17">CANONICAL STATUS MISMATCH</span>')

    prov_bits = []
    for k, v in r.get("provenance", {}).items():
        if k in ("unit_ids", "locator", "citation_text"):
            continue
        if v:
            prov_bits.append('<div class="cell"><span class="k">%s</span>%s</div>' % (esc(k), esc(v)))

    man_bits = []
    for k, v in r.get("manifest_fields", {}).items():
        man_bits.append('<div class="cell"><span class="k">%s</span>%s</div>' % (esc(k), esc(v)))

    checklist = ""
    for item in r.get("review_checklist", []):
        key = item["item"]
        cur = rubric_prev.get(key, "NOT_ASSESSED")
        hi = " hi" if item["high_priority"] else ""
        tag = ' <span class="tag">HIGH PRIORITY</span>' if item["high_priority"] else ""
        sel = "".join(
            '<option value="%s"%s>%s</option>' % (v, " selected" if cur == v else "", v)
            for v in ("NOT_ASSESSED", "PASS", "FAIL", "N/A"))
        checklist += (
            '<div class="check%s"><span class="instr">%s%s</span>'
            '<select name="rubric_%s" style="padding:5px 8px;border:1px solid #dcdce6;border-radius:6px">%s</select>'
            "</div>" % (hi, esc(item["instruction"]), tag, key, sel))

    reval_html = ""
    if r.get("revalidation_reason"):
        reval_html = (
            '<div class="rule" style="background:#f3e8ff;border-color:#d4b4f5">'
            '<b>QUEUE R - this row already carries a HUMAN_VERIFIED label from an '
            'earlier task, but its recorded decision history does not stand on its '
            'own.</b><div style="margin-top:8px">%s</div>'
            '<div class="mono" style="margin-top:8px;font-size:12px">previous '
            'decision: %s%s</div></div>'
            % (esc(r["revalidation_reason"]), esc(r.get("previous_decision") or "-"),
               (" &nbsp;|&nbsp; prior notes: " + esc((r.get("previous_feedback") or "")[:400]))
               if r.get("previous_feedback") else ""))

    err_html = ""
    if errors:
        err_html = '<div class="err"><b>Submission blocked:</b><ul style="margin:6px 0 0 18px">%s</ul></div>' % "".join(
            "<li>%s</li>" % esc(e) for e in errors)
    saved_html = ('<div class="rule" style="background:#e8f5e9;border-color:#a5d6a7">'
                  "<b>Review saved.</b> Decision recorded for %s.</div>" % esc(eid)) if saved else ""

    answered = sum(1 for x in reviews.values() if x.get("example_id"))
    counts = Counter(x.get("decision", "") for x in reviews.values())

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Task 62 Review {idx+1}/{total}</title><style>{CSS}</style></head><body>
<div class="wrap">
<div class="top">
  <div class="qnav">
    <a href="/?idx={max(0, idx-1)}">&larr; Prev</a>
    <b>{idx+1} / {total}</b>
    <a href="/?idx={min(total-1, idx+1)}">Next &rarr;</a>
    <span class="badge b{r['queue']}">{esc(r['queue_name'])}</span>
    <span class="mono">item {r['queue_position']} of {r['queue_size']} in queue {r['queue']}</span>
  </div>
  <div class="qnav">
    <span class="mono">{esc(eid)}</span>
    <a href="/dashboard">Dashboard</a>
    <a href="/queue?queue=A">A</a><a href="/queue?queue=B">B</a>
    <a href="/queue?queue=C">C</a><a href="/queue?queue=D">D</a><a href="/queue">All</a>
  </div>
</div>

{reval_html}{err_html}{saved_html}
  {r.get("_near_dup_html", "")}

<div class="stats">
  <div class="stat"><div class="n">{answered}</div><div class="l">Reviewed</div></div>
  <div class="stat"><div class="n" style="color:#1a7f37">{counts.get('APPROVE',0)}</div><div class="l">Approve</div></div>
  <div class="stat"><div class="n" style="color:#b36b00">{counts.get('REVISE',0)}</div><div class="l">Revise</div></div>
  <div class="stat"><div class="n" style="color:#b3261e">{counts.get('REJECT',0)}</div><div class="l">Reject</div></div>
  <div class="stat"><div class="n">{total-answered}</div><div class="l">Pending</div></div>
</div>

<div class="card">
  <div class="lab">Question <span class="badge b{r['queue']}">{esc(r['category'])}</span>
    <span class="mono">{esc(r['language'])} / {esc(r['question_type'])}</span></div>
  <div class="q">{esc(r['question'])}</div>
  {"<div class='lab' style='margin-top:10px'>Hindi rendering</div><div class='q' style='font-size:16px'>" + esc(r['question_hi']) + "</div>" if r.get('question_hi') else ""}
</div>

<div class="card">
  <div class="lab">Proposed answer (candidate)</div>
  <div class="ans">{esc(r['answer'])}</div>
  <div style="margin-top:10px">{' '.join(flags)}</div>
</div>

<div class="card">
  <div class="lab">Source text / evidence shown to the reviewer</div>
  {"<div class='txt'>" + esc(r['source_text']) + "</div>" if r.get('source_text') else "<div class='txt' style='color:#777'>No corpus unit cited: this is a manifest-grounded claim. Verify against the manifest row below.</div>"}
  <details style="margin-top:12px"><summary>Evidence quote captured by the builder</summary>
    <div class="txt">{esc((r.get('evidence') or {}).get('quote') or '(none)')}</div></details>
  <details><summary>Extra evidence fields</summary>
    <div class="txt">{esc(json.dumps((r.get('evidence') or {}).get('extra') or {}, ensure_ascii=False, indent=2))}</div></details>
</div>

<div class="card">
  <div class="lab">Source, provenance, rights, origin</div>
  <div class="grid">
    <div class="cell"><span class="k">Source title</span>{esc(r['source_title'])}</div>
    <div class="cell"><span class="k">Source ID</span>{esc(r['source_id'])}</div>
    <div class="cell"><span class="k">Parent source</span>{esc(r.get('parent_source_id') or '-')}</div>
    <div class="cell"><span class="k">Locator</span>page {esc(str((r.get('locator') or {}).get('page')))} / section {esc(str((r.get('locator') or {}).get('section')))}</div>
    <div class="cell"><span class="k">Tradition / religious scope</span><span class="{'ok' if r['religious_scope'] in ('CORE_STHANAKAVASI','HIGH_STHANAKAVASI_RELEVANCE') else 'warn'}">{esc(r['religious_scope'])}</span></div>
    <div class="cell"><span class="k">Sect (manifest)</span>{esc(r.get('sect'))} <span class="mono">{esc(r.get('sect_confidence'))}</span></div>
    <div class="cell"><span class="k">Knowledge layer</span><span class="ok">{esc(r['knowledge_layer'])}</span></div>
    <div class="cell"><span class="k">Canonical status</span>{esc(r['canonical_status'])}</div>
    <div class="cell"><span class="k">Teacher / author</span>{esc(r.get('teacher_or_author') or '-')}</div>
    <div class="cell"><span class="k">Lineage</span>{esc(r.get('lineage') or '-')}</div>
    <div class="cell"><span class="k">Rights status</span><span class="{'ok' if 'TRAINING_ALLOWED' in r['rights_status'] else 'bad2'}">{esc(r['rights_status'])}</span><div class="mono">{esc(r.get('rights_basis'))}</div></div>
    <div class="cell"><span class="k">Candidate origin</span>{esc(r['origin'].get('method'))} / synthetic={esc(str(r['origin'].get('synthetic')))} / confidence={esc(r['origin'].get('confidence'))}</div>
    <div class="cell"><span class="k">Split (candidate)</span>{esc(r['split'])} <span class="mono">raw={esc(r.get('split_candidate'))}</span></div>
    <div class="cell"><span class="k">Provenance text_id</span><span class="mono">{esc(r['provenance'].get('text_id'))}</span></div>
    <div class="cell"><span class="k">Citation text</span>{esc(r['provenance'].get('citation_text'))}</div>
    <div class="cell"><span class="k">Review id</span><span class="mono">{esc(r['review_id'])}</span></div>
  </div>
  <details style="margin-top:12px"><summary>Full provenance object</summary>
    <div class="txt">{esc(json.dumps(r.get('provenance', {}), ensure_ascii=False, indent=2))}</div></details>
  <details><summary>Manifest row fields</summary>
    <div class="grid" style="margin-top:8px">{''.join(man_bits)}</div></details>
  <details><summary>Provenance detail fields</summary>
    <div class="grid" style="margin-top:8px">{''.join(prov_bits)}</div></details>
</div>

<div class="card">
  <div class="lab">Why this candidate is in this queue</div>
  <div style="font-size:14px">{esc(r.get('queue_reason',''))}</div>
</div>

<div class="rule">
  <b>Task 62 review rubric</b> — APPROVE only if every relevant condition passes.
  <ol>
    <li><b>Question-answer alignment</b>: the answer answers this question (no tangential or generic Jain filler).</li>
    <li><b>Source grounding</b>: every factual claim needing support is in the supplied source text.</li>
    <li><b>Source attribution</b> (HIGH): no commentary&rarr;Mahavira, modern teacher&rarr;canonical authority,
        translator interpretation&rarr;original scripture, generic Jain claim&rarr;Sthanakavasi doctrine.
        Uncertain attribution must be qualified in the answer.</li>
    <li><b>Sthanakavasi distinction</b> (HIGH): Sthanakavasi / Svetambara / Murtipujaka / Digambara /
        generic Jain stay separate; no tradition-specific claim promoted to universal Jain doctrine.</li>
    <li><b>Canonical vs commentary</b>: the knowledge layer is preserved.</li>
    <li><b>Abstention</b> (HIGH): evidence-gap questions decline honestly instead of inventing.</li>
    <li><b>Practice</b>: practice identity, explanation, tradition attribution, source grounding correct —
        not approved merely because it sounds plausible.</li>
    <li><b>Prakrit / language</b>: terminology, transliteration, Hindi/Gujarati mapping, Sanskrit-vs-Prakrit.
        Do not "correct" a source-supported spelling.</li>
    <li><b>Language quality</b>: natural, grammatical, clear, not verbose.</li>
    <li><b>No fabrication</b>: no invented citations, teachers, Agam refs, dates, sect claims, quotes, certainty.</li>
    <li><b>Pedagogical value</b>: teaches source-aware, tradition-aware behaviour; not a near-duplicate of one already approved.</li>
  </ol>
  <p style="margin-top:8px"><b>APPROVE</b> keeps the exact answer above unless you deliberately edit it below.
  <b>REVISE</b> requires feedback and at least one FAIL rubric item.
  <b>REJECT</b> requires a reason and at least one FAIL rubric item.</p>
</div>

<div class="card">
  <div class="lab">Rubric checklist</div>
  {checklist}
</div>

<form method="POST" action="/review">
  <input type="hidden" name="idx" value="{idx}">
  <input type="hidden" name="example_id" value="{esc(eid)}">
  <div class="card">
    <div class="lab">Decision</div>
    <div class="dec">
      <label><input type="radio" name="decision" value="APPROVE" {checked['APPROVE']}><span class="ap">APPROVE</span></label>
      <label><input type="radio" name="decision" value="REVISE" {checked['REVISE']}><span class="rv">REVISE</span></label>
      <label><input type="radio" name="decision" value="REJECT" {checked['REJECT']}><span class="rj">REJECT</span></label>
    </div>
    <div class="lab">Reviewed answer</div>
    <textarea name="reviewed_answer" rows="7">{esc(edited_default)}</textarea>
    <label style="display:flex;gap:8px;align-items:center;font-size:13.5px;margin-top:8px">
      <input type="checkbox" name="edited_flag" value="1" {edited_flag}>
      I intentionally edited this answer (required if the text above differs from the candidate answer)</label>
    <div class="lab" style="margin-top:14px">Feedback / rejection reason</div>
    <textarea name="feedback" rows="3" placeholder="Required for REVISE and REJECT. What must change, or why is it rejected?">{esc(feedback)}</textarea>
    <button type="submit">Submit review</button>
    <div style="font-size:12.5px;color:#777;margin-top:8px">
      Writes <span class="mono">data/training/sft_human_review_v2.jsonl</span> only.
      Candidate source records are never modified.</div>
  </div>
</form>
</div></body></html>"""


def render_dashboard(queue, reviews):
    total = len(queue)
    counts = Counter(x.get("decision", "") for x in reviews.values())
    answered = sum(1 for r in queue if r["example_id"] in reviews)
    qcounts = Counter(r["queue"] for r in queue)
    qdone = Counter(r["queue"] for r in queue if r["example_id"] in reviews)
    qdec = {q: Counter() for q in qcounts}
    for r in queue:
        rec = reviews.get(r["example_id"])
        if rec:
            qdec[r["queue"]][rec.get("decision", "")] += 1

    stat = ""
    for label, val, color in (
            ("Total candidates", total, "#3f3f8f"), ("Reviewed", answered, "#3f3f8f"),
            ("Pending", total - answered, "#3f3f8f"),
            ("APPROVE", counts.get("APPROVE", 0), "#1a7f37"),
            ("REVISE", counts.get("REVISE", 0), "#b36b00"),
            ("REJECT", counts.get("REJECT", 0), "#b3261e")):
        stat += ('<div class="stat"><div class="n" style="color:%s">%s</div>'
                 '<div class="l">%s</div></div>' % (color, val, label))

    qrows = ""
    for q, spec in ((k, v) for k, v in QUEUE_SPECS):
        n = qcounts.get(q, 0)
        if not n:
            continue
        d = qdec.get(q, Counter())
        qrows += (
            "<tr><td><span class='badge b%s'>%s</span></td><td><a href='/queue?queue=%s'>%s</a></td>"
            "<td class='mono'>%s</td><td>%d / %d</td><td class='mono'>%s</td>"
            "<td style='color:#1a7f37;font-weight:650'>%d</td>"
            "<td style='color:#b36b00;font-weight:650'>%d</td>"
            "<td style='color:#b3261e;font-weight:650'>%d</td></tr>"
            % (q, q, q, esc(spec["name"]), esc(spec["why"]), qdone.get(q, 0), n,
               qdone.get(q, 0) and "%.0f%%" % (100.0 * qdone.get(q, 0) / n) or "0%",
               d.get("APPROVE", 0), d.get("REVISE", 0), d.get("REJECT", 0)))

    catrows = ""
    for cat in sorted({r["category"] for r in queue}):
        rows = [r for r in queue if r["category"] == cat]
        done = [r for r in rows if r["example_id"] in reviews]
        d = Counter(reviews[r["example_id"]].get("decision", "") for r in done)
        catrows += ("<tr><td>%s</td><td>%d</td><td>%d</td><td>%d</td><td>%d</td><td>%d</td></tr>"
                    % (esc(cat), len(rows), len(done), d.get("APPROVE", 0),
                       d.get("REVISE", 0), d.get("REJECT", 0)))

    pendrows = ""
    for i, r in enumerate(queue):
        if r["example_id"] in reviews:
            continue
        pendrows += ("<tr><td><a href='/?idx=%d'>%s</a></td><td><span class='badge b%s'>%s</span></td>"
                     "<td>%s</td><td class='mono'>%s</td><td>%s</td></tr>"
                     % (i, esc(r["example_id"]), r["queue"], esc(r["queue"]),
                        esc(r["category"]), esc(r["source_id"]), esc(r["question"][:90])))

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Task 62 SFT Human Review</title><style>{CSS}</style></head><body>
<div class="wrap">
<div class="top"><div><b>Task 62 — SFT candidate human review gate</b>
 <span class="mono">sft_candidates_v2.jsonl ({total})</span></div>
 <div class="qnav"><a href="/queue?queue=A">Queue A</a><a href="/queue?queue=B">Queue B</a>
 <a href="/queue?queue=C">Queue C</a><a href="/queue?queue=D">Queue D</a><a href="/queue">All</a></div></div>

<div class="rule"><b>How to review.</b> Quality over count — roughly 100&ndash;150 approvals is the target only if
the candidates earn it. Start with Queue A (source attribution), then B (sect distinction), then C (abstention);
these three address the Task 60 regressions. APPROVE keeps the answer exactly as written unless you edit it.
REVISE needs feedback. REJECT needs a reason.</div>

<div class="stats">{stat}</div>

<table><tr><th>Queue</th><th>Name</th><th>Why</th><th>Progress</th><th>Rate</th><th>APPROVE</th><th>REVISE</th><th>REJECT</th></tr>
{qrows}</table>

<h3 style="margin:20px 0 10px;font-size:15px">By category</h3>
<table><tr><th>Category</th><th>Candidates</th><th>Reviewed</th><th>APPROVE</th><th>REVISE</th><th>REJECT</th></tr>
{catrows}</table>

<h3 style="margin:20px 0 10px;font-size:15px">Pending ({total - answered})</h3>
<table><tr><th>Example</th><th>Queue</th><th>Category</th><th>Source</th><th>Question</th></tr>
{pendrows}</table>
</div></body></html>"""


QUEUE_SPECS = [
    ("A", {"name": "QUEUE A — SOURCE ATTRIBUTION",
           "why": "Task 60: unsupported source-attributed claims 6 → 20"}),
    ("B", {"name": "QUEUE B — STHANAKAVASI DISTINCTION",
           "why": "Task 60: sect confusion 1 → 4; category keyterm −0.25"}),
    ("C", {"name": "QUEUE C — ABSTENTION",
           "why": "Task 60: abstention 0/4 both arms — the model never declines"}),
    ("R", {"name": "QUEUE R — RE-ADJUDICATE PRIOR VERIFIED ROWS",
           "why": "Prior HUMAN_VERIFIED rows with a broken decision history "
                  "(Task 61 gaps: 2025 ends REVISE, 2029 ends REJECT, 0038 conflicting)"}),
    ("D", {"name": "QUEUE D — REMAINING CANDIDATES",
           "why": "All other categories, reviewed after A/B/C"}),
]


def render_queue_view(queue, reviews, want=None):
    rows = [r for r in queue if want is None or r["queue"] == want]
    out = []
    for i, r in enumerate(queue):
        if want is not None and r["queue"] != want:
            continue
        rec = reviews.get(r["example_id"], {})
        dec = rec.get("decision", "PENDING")
        color = {"APPROVE": "#1a7f37", "REVISE": "#b36b00", "REJECT": "#b3261e"}.get(dec, "#8a8a99")
        out.append("<tr><td><a href='/?idx=%d'>%d</a></td><td class='mono'>%s</td>"
                   "<td><span class='badge b%s'>%s</span></td><td>%s</td><td class='mono'>%s</td>"
                   "<td>%s</td><td style='color:%s;font-weight:650'>%s</td></tr>"
                   % (i, i + 1, esc(r["example_id"]), r["queue"], esc(r["queue"]),
                      esc(r["category"]), esc(r["source_id"]), esc(r["question"][:100]), color, dec))
    counts = Counter(reviews[r["example_id"]].get("decision", "")
                     for r in rows if r["example_id"] in reviews)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Task 62 queue {want or 'all'}</title><style>{CSS}</style></head><body><div class="wrap">
<div class="top"><div><b>Queue {esc(want or 'all')}</b> — {len(rows)} candidates</div>
<div class="qnav"><a href="/dashboard">Dashboard</a><a href="/queue?queue=A">A</a><a href="/queue?queue=B">B</a>
<a href="/queue?queue=C">C</a><a href="/queue?queue=D">D</a><a href="/queue">All</a></div></div>
<div class="stats">
 <div class="stat"><div class="n">{len(rows)}</div><div class="l">Candidates</div></div>
 <div class="stat"><div class="n" style="color:#1a7f37">{counts.get('APPROVE',0)}</div><div class="l">Approve</div></div>
 <div class="stat"><div class="n" style="color:#b36b00">{counts.get('REVISE',0)}</div><div class="l">Revise</div></div>
 <div class="stat"><div class="n" style="color:#b3261e">{counts.get('REJECT',0)}</div><div class="l">Reject</div></div>
</div>
<table><tr><th>#</th><th>Example</th><th>Queue</th><th>Category</th><th>Source</th><th>Question</th><th>Status</th></tr>
{''.join(out)}</table></div></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, html, code=200):
        data = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        try:
            queue = load_queue()
            reviews = load_reviews()
        except Exception as exc:  # pragma: no cover - surfaced to the operator
            self._send("<h1>Queue load failed</h1><pre>%s</pre>" % esc(exc), 500)
            return
        if parsed.path == "/dashboard":
            self._send(render_dashboard(queue, reviews))
        elif parsed.path == "/queue":
            want = (params.get("queue", [""])[0] or "").strip().upper() or None
            if want and want not in ("A", "B", "C", "D", "R"):
                want = None
            self._send(render_queue_view(queue, reviews, want))
        elif parsed.path == "/":
            idx = int(params.get("idx", ["0"])[0] or 0)
            saved = params.get("saved", ["0"])[0] == "1"
            self._send(render_example(idx, queue, reviews, saved=saved))
        else:
            self._send("<h1>404</h1>", 404)

    def do_POST(self):
        if urlparse(self.path).path != "/review":
            self._send("<h1>404</h1>", 404)
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length).decode("utf-8", "replace")
        params = parse_qs(body, keep_blank_values=True)
        try:
            queue = load_queue()
            reviews = load_reviews()
        except Exception as exc:
            self._send("<h1>Queue load failed</h1><pre>%s</pre>" % esc(exc), 500)
            return

        idx = int((params.get("idx", ["0"])[0] or 0))
        eid = (params.get("example_id", [""])[0] or "")
        row = next((r for r in queue if r["example_id"] == eid), None)
        if row is None:
            self._send("<h1>Unknown example_id %s</h1>" % esc(eid), 400)
            return

        errors = []
        record = build_record(row, params, errors)
        if errors:
            self._send(render_example(idx, queue, reviews, errors=errors), 400)
            return

        write_review(record)
        print("[review] %s -> %s (writes=%d)" % (eid, record["decision"], WRITES["n"]),
              flush=True)
        self._send(render_example(idx, queue, load_reviews(), saved=True))

    def log_message(self, fmt, *args):
        print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), args[0]), flush=True)


def main():
    if not os.path.exists(QUEUE_PATH):
        raise SystemExit("queue missing: %s (run build_review_queue.py first)" % QUEUE_PATH)
    print("Task 62 human review server")
    print("  queue:    %s" % QUEUE_PATH)
    print("  reviews:  %s" % REVIEW_PATH)
    print("  history:  %s" % HISTORY_PATH)
    print("  reviewer: %s" % REVIEWER)
    print("  open:     http://localhost:%d/  (dashboard: /dashboard)" % PORT)
    with socketserver.ThreadingTCPServer(("", PORT), Handler) as httpd:
        httpd.daemon_threads = True
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nserver stopped")


if __name__ == "__main__":
    main()
