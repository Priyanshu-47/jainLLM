#!/usr/bin/env python3
"""SFT Human Review Server - Task 51: Filtered Review Queue."""
import os, json, http.server, socketserver
from urllib.parse import parse_qs, urlparse
from datetime import datetime

BASE_DIR = "/home/azureuser/jainLLM/svk-corpus"
CANDIDATES_PATH = os.path.join(BASE_DIR, "data/training/sft_task51_review_priority_v1.jsonl")
REVIEW_PATH = os.path.join(BASE_DIR, "data/training/sft_task51_human_review_v1.jsonl")
PORT = 8083

def load_candidates():
    candidates = []
    with open(CANDIDATES_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            try: candidates.append(json.loads(line.strip()))
            except: pass
    return candidates

def load_reviews():
    reviews = {}
    if os.path.exists(REVIEW_PATH):
        with open(REVIEW_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    rec = json.loads(line.strip())
                    reviews[rec['candidate_id']] = rec
                except: pass
    return reviews

def save_review(review):
    with open(REVIEW_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(review, ensure_ascii=False) + '\n')

class ReviewHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        candidates = load_candidates()
        reviews = load_reviews()

        if parsed.path == '/':
            idx = int(params.get('idx', ['0'])[0])
            idx = max(0, min(idx, len(candidates)-1))
            c = candidates[idx]
            html = render_task51_example(c, idx, len(candidates), reviews)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        elif parsed.path == '/dashboard':
            html = render_task51_dashboard(candidates, reviews)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        params = parse_qs(body)

        candidate_id = params.get('candidate_id', [''])[0]
        idx = int(params.get('idx', ['0'])[0])
        decision = params.get('decision', [''])[0]
        notes = params.get('notes', [''])[0]
        changes = params.get('changes', [''])[0]

        review = {
            "candidate_id": candidate_id,
            "reviewer": "HUMAN_REVIEWER",
            "reviewed_at": datetime.utcnow().isoformat() + "Z",
            "decision": decision,
            "reviewer_notes": notes,
            "required_changes": [changes] if changes else [],
            "question_quality": params.get('question_quality', [''])[0],
            "alignment_quality": params.get('alignment_quality', [''])[0],
            "explanation_quality": params.get('explanation_quality', [''])[0],
            "source_grounding_quality": params.get('source_grounding_quality', [''])[0],
            "doctrinal_attribution_quality": params.get('doctrinal_attribution_quality', [''])[0],
            "language_quality": params.get('language_quality', [''])[0],
            "sft_value": params.get('sft_value', [''])[0],
        }

        save_review(review)

        candidates = load_candidates()
        reviews = load_reviews()
        idx = max(0, min(idx, len(candidates)-1))
        html = render_task51_example(candidates[idx], idx, len(candidates), reviews)
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def render_task51_example(c, idx, total, reviews):
    cid = c.get('candidate_id', '')
    question = c.get('question', '')
    answer = c.get('answer', '')
    source_id = c.get('source_id', '')
    source_title = c.get('source_title', '')
    agam_id = c.get('agam_id', '')
    category = c.get('category', '')
    concepts = ', '.join(c.get('concepts', []))
    practices = ', '.join(c.get('practices', []))
    language = c.get('language', '')
    lineage = c.get('lineage', '')
    layer = c.get('knowledge_layer', '')
    alignment = c.get('question_answer_alignment', '')
    grounding = c.get('source_grounding_confidence', '')
    tier = c.get('quality_tier', '')
    lang_issues = ', '.join(c.get('language_issues', []))

    existing = reviews.get(cid, {})
    prev_decision = existing.get('decision', '')

    checked_approve = 'checked' if prev_decision == 'APPROVE' else ''
    checked_revise = 'checked' if prev_decision == 'REVISE' else ''
    checked_reject = 'checked' if prev_decision == 'REJECT' else ''

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Task 51 Review - {cid}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,sans-serif;background:#f5f5f5;color:#333;line-height:1.6}}
.c{{max-width:950px;margin:0 auto;padding:20px}}
.nav{{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding:12px 16px;background:#fff;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,.1)}}
.nav a{{color:#4a4a8a;text-decoration:none;padding:6px 12px;border-radius:4px}}
.nav a:hover{{background:#f0f0f0}}
.card{{background:#fff;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,.1);padding:24px;margin-bottom:20px}}
.sec{{margin-bottom:20px}}
.st{{font-size:11px;text-transform:uppercase;color:#888;letter-spacing:1px;margin-bottom:8px;font-weight:600}}
.q{{font-size:18px;font-weight:600;color:#1a1a2e;line-height:1.5}}
.a{{font-size:15px;line-height:1.7;color:#444;background:#f8f9fa;padding:16px;border-radius:6px;border-left:4px solid #4a4a8a;white-space:pre-wrap}}
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
select{{padding:8px;border:1px solid #ddd;border-radius:6px;font-size:14px}}
.flag{{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;margin-right:4px}}
.flag-yes{{background:#c8e6c9;color:#2e7d32}}
.flag-no{{background:#ffcdd2;color:#c62828}}
.flag-warn{{background:#fff3cd;color:#856404}}
</style></head><body>
<div class="c">
<div class="nav">
<a href="/?idx={max(0,idx-1)}">&laquo; Previous</a>
<span>Example {idx+1} of {total} | {cid}</span>
<a href="/?idx={min(total-1,idx+1)}">Next &raquo;</a>
</div>

<div class="card">
<div class="sec"><div class="st">Question</div><div class="q">{question}</div></div>
<div class="sec"><div class="st">Answer</div><div class="a">{answer}</div></div>

<div class="sec"><div class="st">Source Information</div>
<div class="meta">
<div class="mi"><span class="ml">Source ID:</span> {source_id}</div>
<div class="mi"><span class="ml">Source Title:</span> {source_title}</div>
<div class="mi"><span class="ml">Agam ID:</span> {agam_id or 'N/A'}</div>
<div class="mi"><span class="ml">Category:</span> {category}</div>
<div class="mi"><span class="ml">Concepts:</span> {concepts or 'N/A'}</div>
<div class="mi"><span class="ml">Practices:</span> {practices or 'N/A'}</div>
</div></div>

<div class="sec"><div class="st">Quality Indicators</div>
<div>
<span class="flag {'flag-yes' if alignment == 'HIGH' else 'flag-warn' if alignment == 'MEDIUM' else 'flag-no'}">Alignment: {alignment}</span>
<span class="flag {'flag-yes' if grounding == 'HIGH' else 'flag-warn' if grounding == 'MEDIUM' else 'flag-no'}">Grounding: {grounding}</span>
<span class="flag {'flag-yes' if tier == 'TIER_A' else 'flag-warn'}">Tier: {tier}</span>
<span class="flag {'flag-no' if lang_issues else 'flag-yes'}">Language: {'ISSUES: ' + lang_issues if lang_issues else 'OK'}</span>
</div></div>

<div class="sec"><div class="st">Metadata</div>
<div class="meta">
<div class="mi"><span class="ml">Language:</span> {language}</div>
<div class="mi"><span class="ml">Lineage:</span> {lineage}</div>
<div class="mi"><span class="ml">Knowledge Layer:</span> {layer}</div>
</div></div>
</div>

<div class="rules"><h3>Review Criteria</h3><ul>
<li><b>APPROVE</b> if: question makes sense, answer addresses the question, answer explains the concept, language is understandable, source grounding is real, attribution is correct, no fabricated doctrine</li>
<li><b>REVISE</b> if: concept/source is useful, answer is mostly correct, wording needs improvement</li>
<li><b>REJECT</b> if: source doesn't support it, question is fundamentally wrong, answer teaches incorrect attribution, answer is fundamentally mismatched, content is unusable</li>
</ul></div>

<form method="POST" action="/review">
<input type="hidden" name="candidate_id" value="{cid}">
<input type="hidden" name="idx" value="{idx}">
<div class="rf">
<div class="sec"><div class="st">Decision</div>
<div class="rg">
<label><input type="radio" name="decision" value="APPROVE" {checked_approve}><span>APPROVE</span></label>
<label><input type="radio" name="decision" value="REVISE" {checked_revise}><span>REVISE</span></label>
<label><input type="radio" name="decision" value="REJECT" {checked_reject}><span>REJECT</span></label>
</div></div>

<div class="sec"><div class="st">Quality Ratings</div>
<div class="meta">
<div class="mi"><label>Question Quality<br><select name="question_quality"><option value="">--</option><option value="PASS">PASS</option><option value="FAIL">FAIL</option></select></label></div>
<div class="mi"><label>Alignment<br><select name="alignment_quality"><option value="">--</option><option value="PASS">PASS</option><option value="FAIL">FAIL</option></select></label></div>
<div class="mi"><label>Explanation<br><select name="explanation_quality"><option value="">--</option><option value="PASS">PASS</option><option value="FAIL">FAIL</option></select></label></div>
<div class="mi"><label>Source Grounding<br><select name="source_grounding_quality"><option value="">--</option><option value="PASS">PASS</option><option value="FAIL">FAIL</option></select></label></div>
<div class="mi"><label>Doctrinal Attribution<br><select name="doctrinal_attribution_quality"><option value="">--</option><option value="PASS">PASS</option><option value="FAIL">FAIL</option></select></label></div>
<div class="mi"><label>Language Quality<br><select name="language_quality"><option value="">--</option><option value="PASS">PASS</option><option value="FAIL">FAIL</option></select></label></div>
<div class="mi"><label>SFT Value<br><select name="sft_value"><option value="">--</option><option value="HIGH">HIGH</option><option value="MEDIUM">MEDIUM</option><option value="LOW">LOW</option></select></label></div>
</div></div>

<div class="sec"><div class="st">Reviewer Notes</div>
<textarea name="notes" rows="3" placeholder="Observations..."></textarea></div>
<div class="sec"><div class="st">Required Changes (for REVISE)</div>
<textarea name="changes" rows="2" placeholder="What needs to change..."></textarea></div>
<button type="submit" class="btn">Submit Review</button>
</div></form>
</div></body></html>"""


def render_task51_dashboard(candidates, reviews):
    total = len(candidates)
    reviewed = sum(1 for c in candidates if c['candidate_id'] in reviews)
    approved = sum(1 for r in reviews.values() if r.get('decision') == 'APPROVE')
    revised = sum(1 for r in reviews.values() if r.get('decision') == 'REVISE')
    rejected = sum(1 for r in reviews.values() if r.get('decision') == 'REJECT')

    rows = ""
    for i, c in enumerate(candidates):
        cid = c['candidate_id']
        r = reviews.get(cid, {})
        decision = r.get('decision', 'PENDING')
        cat = c.get('category', '')
        tier = c.get('quality_tier', '')
        alignment = c.get('question_answer_alignment', '')
        css = {'APPROVE': 'green', 'REVISE': 'orange', 'REJECT': 'red', 'PENDING': 'gray'}.get(decision, 'gray')
        rows += f'<tr><td>{i+1}</td><td><a href="/?idx={i}">{cid}</a></td><td>{cat}</td><td>{tier}</td><td>{alignment}</td><td style="color:{css};font-weight:600">{decision}</td></tr>\n'

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Task 51 Review Dashboard - JainLLM</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,sans-serif;background:#f5f5f5;color:#333}}
.c{{max-width:1100px;margin:0 auto;padding:20px}}
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
.warn{{background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:16px;margin-bottom:20px}}
</style></head><body>
<div class="c">
<h1>Task 51: Filtered SFT Candidate Review</h1>
<p class="sub">JainLLM | {total} filtered candidates from Task 49 | Awaiting human review</p>
<div class="warn"><b>Context:</b> These candidates passed automated filtering. Review for SFT training value.</div>
<div class="stats">
<div class="stat"><div class="stat-n">{total}</div><div class="stat-l">Total</div></div>
<div class="stat"><div class="stat-n">{reviewed}</div><div class="stat-l">Reviewed</div></div>
<div class="stat"><div class="stat-n">{total-reviewed}</div><div class="stat-l">Pending</div></div>
<div class="stat"><div class="stat-n" style="color:green">{approved}</div><div class="stat-l">Approved</div></div>
<div class="stat"><div class="stat-n" style="color:orange">{revised}</div><div class="stat-l">Revised</div></div>
<div class="stat"><div class="stat-n" style="color:red">{rejected}</div><div class="stat-l">Rejected</div></div>
</div>
<table><tr><th>#</th><th>Candidate ID</th><th>Category</th><th>Tier</th><th>Alignment</th><th>Status</th></tr>
{rows}</table>
</div></body></html>"""


if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    os.chdir(os.path.dirname(__file__))
    print(f"Task 51 Review Server starting on http://localhost:{PORT}")
    print(f"Dashboard: http://localhost:{PORT}/dashboard")
    print(f"Candidates: {CANDIDATES_PATH}")
    print(f"Review results: {REVIEW_PATH}")
    print("Press Ctrl+C to stop")
    with socketserver.TCPServer(("", PORT), ReviewHandler) as httpd:
        try: httpd.serve_forever()
        except KeyboardInterrupt: print("\nServer stopped")
