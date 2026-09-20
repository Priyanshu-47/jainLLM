import csv
import json
from collections import Counter

manifest = {}
with open("svk-corpus/manifests/source_manifest.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        manifest[row["source_id"]] = row

uses = Counter(m.get("recommended_use", "") for m in manifest.values())
print("=== recommended_use distribution ===")
for use, count in uses.most_common():
    print(f"  {use}: {count}")

scopes = Counter(m.get("religious_scope", "") for m in manifest.values())
print()
print("=== religious_scope distribution ===")
for scope, count in scopes.most_common():
    print(f"  {scope}: {count}")

layers = Counter(m.get("knowledge_layer", "") for m in manifest.values())
print()
print("=== knowledge_layer distribution ===")
for layer, count in layers.most_common():
    print(f"  {layer}: {count}")

print()
print("=== CORE_STHANAKAVASI sources needing permission ===")
for sid, m in sorted(manifest.items()):
    if m.get("religious_scope") == "CORE_STHANAKAVASI" and m.get("recommended_use") == "NEEDS_PERMISSION":
        title = m["title"][:55]
        tp = m.get("training_permission", "")
        print(f"  {sid}: {title} | tp={tp}")

print()
print("=== Sources with practice-related content ===")
for sid, m in sorted(manifest.items()):
    kl = m.get("knowledge_layer", "").lower()
    title = m.get("title", "").lower()
    if any(w in kl or w in title for w in ["practice", "pratikraman", "samayik", "avashyaka", "kayotsarga", "vandana", "pratyakhyan", "chauvi", "paryushan"]):
        print(f"  {sid}: {m['title'][:60]} | kl={m.get('knowledge_layer','')}")
