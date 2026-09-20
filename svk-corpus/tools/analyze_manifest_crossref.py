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

print("=== MANIFEST SUMMARY ===")
print(f"Total sources in manifest: {len(manifest)}")
print(f"Sources with training units: {len(training_sources)}")
print()

# Classify all sources
print("=== ALL 62 SOURCES — TRAINING ELIGIBILITY ===")
print(f"{'SID':<10} {'Title':<55} {'Training':<20} {'Religious Scope':<30} {'Knowledge Layer':<25} {'Lang'}")
print("-" * 170)

for sid in sorted(manifest.keys()):
    m = manifest[sid]
    title = m.get("title", "")[:53]
    training_gate = m.get("training_gate_decision", "")
    religious_scope = m.get("religious_scope", "")
    knowledge_layer = m.get("knowledge_layer", "")
    language = m.get("primary_language", "")
    in_training = "YES" if sid in training_sources else "NO"
    print(f"{sid:<10} {title:<55} {training_gate:<20} {religious_scope:<30} {knowledge_layer:<25} {language}")

print()
print("=== TRAINING GATE DECISION DISTRIBUTION ===")
gate_counts = defaultdict(list)
for sid, m in manifest.items():
    gate = m.get("training_gate_decision", "UNKNOWN")
    gate_counts[gate].append(sid)
for gate, sids in sorted(gate_counts.items()):
    in_train = sum(1 for s in sids if s in training_sources)
    print(f"  {gate}: {len(sids)} sources ({in_train} in training corpus)")

print()
print("=== RELIGIOUS SCOPE DISTRIBUTION ===")
scope_counts = defaultdict(list)
for sid, m in manifest.items():
    scope = m.get("religious_scope", "UNKNOWN")
    scope_counts[scope].append(sid)
for scope, sids in sorted(scope_counts.items()):
    in_train = sum(1 for s in sids if s in training_sources)
    print(f"  {scope}: {len(sids)} sources ({in_train} in training corpus)")

print()
print("=== KNOWLEDGE LAYER DISTRIBUTION ===")
layer_counts = defaultdict(list)
for sid, m in manifest.items():
    layer = m.get("knowledge_layer", "UNKNOWN")
    layer_counts[layer].append(sid)
for layer, sids in sorted(layer_counts.items()):
    in_train = sum(1 for s in sids if s in training_sources)
    print(f"  {layer}: {len(sids)} sources ({in_train} in training corpus)")

print()
print("=== SOURCES IN TRAINING BUT NOT TRAINING_ALLOWED ===")
for sid in sorted(training_sources):
    m = manifest.get(sid, {})
    gate = m.get("training_gate_decision", "")
    if gate not in ("TRAINING_ALLOWED", "TRAINING_ALLOWED (R70_PRE_1930_PUBLICATION)", "TRAINING_ALLOWED (R60_INSTITUTION_RIGHTS_STATEMENT)", "TRAINING_ALLOWED (R25_LIFE_PLUS_60_EXPIRED)"):
        print(f"  {sid}: gate={gate}, title={m.get('title', '')[:60]}")

print()
print("=== HIGH-PRIORITY STHANAKAVASI SOURCES ===")
for sid in sorted(manifest.keys()):
    m = manifest[sid]
    scope = m.get("religious_scope", "")
    if "CORE_STHANAKAVASI" in scope or "HIGH_STHANAKAVASI_RELEVANCE" in scope:
        in_train = "IN TRAINING" if sid in training_sources else "NOT IN TRAINING"
        gate = m.get("training_gate_decision", "")
        print(f"  {sid}: {m.get('title', '')[:55]} | {scope} | {gate} | {in_train}")
