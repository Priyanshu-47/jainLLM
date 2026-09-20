#!/usr/bin/env python3
"""SFT Human Review Server - lightweight local web UI."""
import os, json, http.server, socketserver
from urllib.parse import parse_qs, urlparse
from datetime import datetime

BASE_DIR = "/home/azureuser/jainLLM/svk-corpus"
GOLD_PATH = os.path.join(BASE_DIR, "data/training/sft_gold_v1.jsonl")
REVIEW_PATH = os.path.join(BASE_DIR, "data/training/sft_human_review_results_v1.jsonl")
PORT = 8080

def load_examples():
    examples = []
    with open(GOLD_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            try: examples.append(json.loads(line.strip()))
            except: pass
    return examples

def load_reviews():
    reviews = {}
    if os.path.exists(REVIEW_PATH):
        with open(REVIEW_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    rec = json.loads(line.strip())
                    reviews[rec['example_id']] = rec
                except: pass
    return reviews

def save_review(review):
    with open(REVIEW_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(review, ensure_ascii=False) + '\n')

class ReviewHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        from sft_review_html import render_example, render_dashboard
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        examples = load_examples()
        reviews = load_reviews()

        if parsed.path == '/':
            idx = int(params.get('idx', ['0'])[0])
            idx = max(0, min(idx, len(examples)-1))
            ex = examples[idx]
            html = render_example(ex, idx, len(examples), reviews)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        elif parsed.path == '/dashboard':
            html = render_dashboard(examples, reviews)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        from sft_review_html import render_example
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        params = parse_qs(body)

        example_id = params.get('example_id', [''])[0]
        idx = int(params.get('idx', ['0'])[0])
        decision = params.get('decision', [''])[0]
        notes = params.get('notes', [''])[0]
        changes = params.get('changes', [''])[0]

        review = {
            "example_id": example_id,
            "reviewer": "HUMAN_REVIEWER",
            "review_timestamp": datetime.utcnow().isoformat() + "Z",
            "decision": decision,
            "review_notes": notes,
            "required_changes": [changes] if changes else [],
            "source_verified": params.get('source_verified', ['false'])[0] == 'true',
            "answer_grounded": params.get('answer_grounded', ['false'])[0] == 'true',
            "citation_verified": params.get('citation_verified', ['false'])[0] == 'true',
            "teacher_verified": params.get('teacher_verified', ['false'])[0] == 'true',
            "agam_verified": params.get('agam_verified', ['false'])[0] == 'true',
            "practice_verified": params.get('practice_verified', ['false'])[0] == 'true',
            "sthanakavasi_verified": params.get('sth_verified', ['false'])[0] == 'true',
            "provenance_verified": params.get('provenance_verified', ['false'])[0] == 'true',
        }

        save_review(review)

        examples = load_examples()
        reviews = load_reviews()
        idx = max(0, min(idx, len(examples)-1))
        html = render_example(examples[idx], idx, len(examples), reviews)
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    os.chdir(os.path.dirname(__file__))
    print(f"SFT Review Server starting on http://localhost:{PORT}")
    print(f"Dashboard: http://localhost:{PORT}/dashboard")
    print(f"Gold dataset: {GOLD_PATH}")
    print(f"Review results: {REVIEW_PATH}")
    print("Press Ctrl+C to stop")
    with socketserver.TCPServer(("", PORT), ReviewHandler) as httpd:
        try: httpd.serve_forever()
        except KeyboardInterrupt: print("\nServer stopped")
