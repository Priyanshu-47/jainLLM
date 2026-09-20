import csv
import json
from collections import defaultdict

# Load source manifest
manifest = {}
with open("svk-corpus/manifests/source_manifest.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        sid = row["source_id"]
        manifest[sid] = row

# Load training corpus source list
training_sources = set()
with open("svk-corpus/data/release/training_corpus.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        sid = rec.get("document_id", "").split(":")[0]
        training_sources.add(sid)

# Also load rag_corpus for completeness
rag_sources = set()
with open("svk-corpus/data/release/rag_corpus.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        sid = rec.get("document_id", "").split(":")[0]
        rag_sources.add(sid)

print("=== SOURCES NOT IN TRAINING OR RAG ===")
for sid in sorted(manifest.keys()):
    if sid not in training_sources and sid not in rag_sources:
        m = manifest[sid]
        print(f"  {sid}: {m.get('title', '')[:60]} | training_permission={m.get('training_permission', '')} | recommended_use={m.get('recommended_use', '')}")

print()
print("=== TRAINING PERMISSION FOR ALL SOURCES ===")
for sid in sorted(manifest.keys()):
    m = manifest[sid]
    tp = m.get("training_permission", "")
    in_train = "IN_TRAIN" if sid in training_sources else "NOT_IN_TRAIN"
    in_rag = "IN_RAG" if sid in rag_sources else "NOT_IN_RAG"
    ru = m.get("recommended_use", "")
    print(f"  {sid}: training_permission={tp}, {in_train}, {in_rag}, recommended_use={ru}")
