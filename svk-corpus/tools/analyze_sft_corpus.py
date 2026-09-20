import json
from collections import Counter, defaultdict

sources = Counter()
source_details = defaultdict(lambda: {"units": 0, "chars": 0, "languages": set(), "knowledge_layers": set(), "religious_scopes": set(), "authors": set()})

with open("svk-corpus/data/release/training_corpus.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        sid = rec.get("document_id", "").split(":")[0]
        sources[sid] += 1
        sd = source_details[sid]
        sd["units"] += 1
        sd["chars"] += len(rec.get("normalized_text", ""))
        sd["languages"].add(rec.get("language", "unknown"))
        sd["knowledge_layers"].add(rec.get("knowledge_layer", "unknown"))
        sd["religious_scopes"].add(rec.get("religious_scope", "unknown"))
        sd["authors"].add(rec.get("author", "unknown"))

print("Total units:", sum(sources.values()))
print("Sources with training units:", len(sources))
print()
print("=== Per-source training unit counts ===")
for sid, count in sorted(sources.items()):
    d = source_details[sid]
    langs = ",".join(sorted(d["languages"]))
    layers = ",".join(sorted(d["knowledge_layers"]))
    scopes = ",".join(sorted(d["religious_scopes"]))
    authors = ",".join(sorted(d["authors"])[:3])
    print(f"{sid}: {count} units, {d['chars']} chars, langs=[{langs}], layers=[{layers}], scopes=[{scopes}], authors=[{authors}]")
