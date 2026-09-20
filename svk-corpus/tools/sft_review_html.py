"""HTML rendering for SFT review server."""

def render_example(ex, idx, total, reviews):
    eid = ex.get('example_id', '')
    question = ex.get('messages', [{}])[0].get('content', '')
    answer = ex.get('messages', [{}, {}])[1].get('content', '') if len(ex.get('messages', [])) > 1 else ''
    citations = ex.get('citations', [])
    cit_text = citations[0].get('text_excerpt', '') if citations else 'N/A'
    source_id = ex.get('source_ids', [''])[0]
    unit_id = ex.get('source_units', [''])[0] if ex.get('source_units') else 'N/A'
    teacher = ex.get('teacher', '') or 'N/A'
    agam = ex.get('agam_id', '') or 'N/A'
    practice = ex.get('practice', '') or 'N/A'
    lineage = ex.get('lineage', '') or 'N/A'
    layer = ex.get('knowledge_layer', '') or 'N/A'
    role = ex.get('content_role', '') or 'N/A'
    tradition = ex.get('tradition', '') or 'N/A'

    existing = reviews.get(eid, {})
    prev_decision = existing.get('decision', '')

    checked_approve = 'checked' if prev_decision == 'APPROVE' else ''
    checked_revise = 'checked' if prev_decision == 'REVISE' else ''
    checked_reject = 'checked' if prev_decision == 'REJECT' else ''

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SFT Review - {eid}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,sans-serif;background:#f5f5f5;color:#333;line-height:1.6}}
.c{{max-width:900px;margin:0 auto;padding:20px}}
.nav{{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding:12px 16px;background:#fff;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,.1)}}
.nav a{{color:#4a4a8a;text-decoration:none;padding:6px 12px;border-radius:4px}}
.nav a:hover{{background:#f0f0f0}}
.card{{background:#fff;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,.1);padding:24px;margin-bottom:20px}}
.sec{{margin-bottom:20px}}
.st{{font-size:11px;text-transform:uppercase;color:#888;letter-spacing:1px;margin-bottom:8px;font-weight:600}}
.q{{font-size:18px;font-weight:600;color:#1a1a2e;line-height:1.5}}
.a{{font-size:15px;line-height:1.6;color:#444;background:#f8f9fa;padding:16px;border-radius:6px;border-left:4px solid #4a4a8a;white-space:pre-wrap}}
.sp{{font-size:14px;line-height:1.5;color:#555;background:#fff3cd;padding:12px;border-radius:6px;font-style:italic;white-space:pre-wrap}}
.meta{{display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13px}}
.mi{{background:#f8f9fa;padding:8px 12px;border-radius:4px}}
.ml{{font-weight:600;color:#666}}
.rules{{background:#e8f5e9;border:1px solid #4caf50;border-radius:6px;padding:16px;margin-bottom:20px;font-size:13px}}
.rules h3{{color:#2e7d32;margin-bottom:8px}}
.rules ul{{margin-left:20px}}
.rules li{{margin-bottom:4px}}
.rf{{background:#f0f0f0;border-radius:8px;padding:20px}}
.rg{{display:flex;gap:20px;margin-bottom:16px}}
.rg label{{display:flex;align-items:center;gap:6px;cursor:pointer;padding:8px 16px;background:#fff;border-radius:6px;border:2px solid #ddd}}
.rg label:hover{{border-color:#4a4a8a}}
textarea{{width:100%;padding:12px;border:1px solid #ddd;border-radius:6px;font-family:inherit;font-size:14px;resize:vertical}}
textarea:focus{{outline:none;border-color:#4a4a8a}}
.btn{{background:#4a4a8a;color:#fff;border:none;padding:12px 24px;border-radius:6px;font-size:15px;cursor:pointer;margin-top:12px}}
.btn:hover{{background:#3a3a7a}}
</style></head><body>
<div class="c">
<div class="nav">
<a href="/?idx={max(0,idx-1)}">&laquo; Previous</a>
<span>Example {idx+1} of {total} | {eid}</span>
<a href="/?idx={min(total-1,idx+1)}">Next &raquo;</a>
</div>
<div class="card">
<div class="sec"><div class="st">Question</div><div class="q">{question}</div></div>
<div class="sec"><div class="st">Proposed Answer</div><div class="a">{answer}</div></div>
<div class="sec"><div class="st">Source Evidence (Cited Passage)</div><div class="sp">{cit_text}</div></div>
<div class="sec"><div class="st">Source Metadata</div>
<div class="meta">
<div class="mi"><span class="ml">Source:</span> {source_id}</div>
<div class="mi"><span class="ml">Unit ID:</span> {unit_id}</div>
<div class="mi"><span class="ml">Teacher:</span> {teacher}</div>
<div class="mi"><span class="ml">Agam:</span> {agam}</div>
<div class="mi"><span class="ml">Practice:</span> {practice}</div>
<div class="mi"><span class="ml">Tradition:</span> {tradition}</div>
</div></div>
<div class="sec"><div class="st">Classification</div>
<div class="meta">
<div class="mi"><span class="ml">Lineage:</span> {lineage}</div>
<div class="mi"><span class="ml">Knowledge Layer:</span> {layer}</div>
<div class="mi"><span class="ml">Content Role:</span> {role}</div>
</div></div>
</div>
<div class="rules"><h3>Review Rules</h3><ul>
<li><b>APPROVE</b> if: cited passage supports answer, no unsupported claims, citation correct, teacher/Agam/practice supported, STH claim supported</li>
<li><b>REVISE</b> if: source supports concept but wording needs correction, citation correct but answer needs fixing</li>
<li><b>REJECT</b> if: source does not support answer, depends on outside knowledge, attribution unreliable, citation wrong</li>
</ul></div>
<form method="POST" action="/review">
<input type="hidden" name="example_id" value="{eid}">
<input type="hidden" name="idx" value="{idx}">
<div class="rf">
<div class="sec"><div class="st">Decision</div>
<div class="rg">
<label><input type="radio" name="decision" value="APPROVE" {checked_approve}><span>APPROVE</span></label>
<label><input type="radio" name="decision" value="REVISE" {checked_revise}><span>REVISE</span></label>
<label><input type="radio" name="decision" value="REJECT" {checked_reject}><span>REJECT</span></label>
</div></div>
<div class="sec"><div class="st">Reviewer Notes</div>
<textarea name="notes" rows="3" placeholder="Optional notes..."></textarea></div>
<div class="sec"><div class="st">Required Changes (for REVISE)</div>
<textarea name="changes" rows="2" placeholder="What needs to change..."></textarea></div>
<div class="sec"><div class="st">Verification Checkboxes</div>
<div class="meta">
<div class="mi"><label><input type="checkbox" name="source_verified" value="true"> Source verified</label></div>
<div class="mi"><label><input type="checkbox" name="answer_grounded" value="true"> Answer grounded</label></div>
<div class="mi"><label><input type="checkbox" name="citation_verified" value="true"> Citation verified</label></div>
<div class="mi"><label><input type="checkbox" name="teacher_verified" value="true"> Teacher verified</label></div>
<div class="mi"><label><input type="checkbox" name="agam_verified" value="true"> Agam verified</label></div>
<div class="mi"><label><input type="checkbox" name="practice_verified" value="true"> Practice verified</label></div>
<div class="mi"><label><input type="checkbox" name="sth_verified" value="true"> STH claim verified</label></div>
<div class="mi"><label><input type="checkbox" name="provenance_verified" value="true"> Provenance verified</label></div>
</div></div>
<button type="submit" class="btn">Submit Review</button>
</div></form>
</div></body></html>"""


def render_dashboard(examples, reviews):
    total = len(examples)
    reviewed = sum(1 for ex in examples if ex['example_id'] in reviews)
    approved = sum(1 for r in reviews.values() if r.get('decision') == 'APPROVE')
    revised = sum(1 for r in reviews.values() if r.get('decision') == 'REVISE')
    rejected = sum(1 for r in reviews.values() if r.get('decision') == 'REJECT')

    rows = ""
    for i, ex in enumerate(examples):
        eid = ex['example_id']
        r = reviews.get(eid, {})
        decision = r.get('decision', 'PENDING')
        layer = ex.get('knowledge_layer', '')
        teacher = ex.get('teacher', '') or '-'
        practice = ex.get('practice', '') or '-'
        lineage = ex.get('lineage', '') or '-'
        css = {'APPROVE': 'green', 'REVISE': 'orange', 'REJECT': 'red', 'PENDING': 'gray'}.get(decision, 'gray')
        rows += f'<tr><td>{i+1}</td><td><a href="/?idx={i}">{eid}</a></td><td>{layer}</td><td>{teacher}</td><td>{practice}</td><td>{lineage}</td><td style="color:{css};font-weight:600">{decision}</td></tr>\n'

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SFT Review Dashboard - JainLLM</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,sans-serif;background:#f5f5f5;color:#333}}
.c{{max-width:1000px;margin:0 auto;padding:20px}}
h1{{color:#1a1a2e;margin-bottom:8px}}
.sub{{color:#666;margin-bottom:20px}}
.stats{{display:flex;gap:16px;margin-bottom:24px;flex-wrap:wrap}}
.stat{{background:#fff;padding:16px 24px;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,.1);text-align:center;min-width:120px}}
.stat-n{{font-size:28px;font-weight:700;color:#4a4a8a}}
.stat-l{{font-size:11px;text-transform:uppercase;color:#888;letter-spacing:1px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 4px rgba(0,0,0,.1)}}
th{{background:#4a4a8a;color:#fff;padding:12px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:1px}}
td{{padding:10px 12px;border-bottom:1px solid #eee;font-size:14px}}
tr:hover{{background:#f8f9fa}}
a{{color:#4a4a8a;text-decoration:none}}
a:hover{{text-decoration:underline}}
.warn{{background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:16px;margin-bottom:20px}}
</style></head><body>
<div class="c">
<h1>SFT Human Review Dashboard</h1>
<p class="sub">JainLLM Stage-A Gold Dataset | 12 candidates awaiting human review</p>
<div class="warn"><b>IMPORTANT:</b> All examples are HUMAN_REVIEW_REQUIRED. No examples are HUMAN_VERIFIED. Only actual human review can produce HUMAN_VERIFIED status.</div>
<div class="stats">
<div class="stat"><div class="stat-n">{total}</div><div class="stat-l">Total</div></div>
<div class="stat"><div class="stat-n">{reviewed}</div><div class="stat-l">Reviewed</div></div>
<div class="stat"><div class="stat-n">{total-reviewed}</div><div class="stat-l">Pending</div></div>
<div class="stat"><div class="stat-n" style="color:green">{approved}</div><div class="stat-l">Approved</div></div>
<div class="stat"><div class="stat-n" style="color:orange">{revised}</div><div class="stat-l">Revised</div></div>
<div class="stat"><div class="stat-n" style="color:red">{rejected}</div><div class="stat-l">Rejected</div></div>
</div>
<table><tr><th>#</th><th>Example ID</th><th>Layer</th><th>Teacher</th><th>Practice</th><th>Lineage</th><th>Status</th></tr>
{rows}</table>
</div></body></html>"""
