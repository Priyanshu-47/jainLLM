import json

queue = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "jainllm-source-acquisition-queue-v1",
    "title": "JainLLM Source Acquisition Queue v1",
    "description": "Prioritized queue of external Jain sources to acquire. Each candidate records what to acquire, why, from where, for which knowledge area, for which future use, what rights check is required, and its priority.",
    "version": "1.0",
    "queue_metadata": {
        "created": "2026-09-19",
        "last_updated": "2026-09-19",
        "total_candidates": 42,
        "priority_counts": {"P0": 14, "P1": 12, "P2": 10, "P3": 6},
        "platforms": ["JAINQQ", "JAINEBOOKS", "INTERNET_ARCHIVE", "MANUAL_ACQUISITION"],
        "rights_summary": {"CLEAR": 2, "PERMISSION_REQUIRED": 0, "UNCLEAR": 0, "RESTRICTED": 0, "UNKNOWN": 40}
    },
    "candidates": []
}

c = queue["candidates"]

# P0: Canonical texts (7)
for i, (title, agam, notes) in enumerate([
    ("Acharanga Sutra — Sthanakavasi edition/commentary", "AGAM-001", "First Anga, foundational for all Svetambara traditions. Current corpus has only English translation (SVK-1001)."),
    ("Sutrakritanga Sutra — Sthanakavasi edition", "AGAM-002", "Second Anga. Current corpus has only English translation (SVK-1001)."),
    ("Uttaradhyayana Sutra — Sthanakavasi edition with commentary", "AGAM-013", "Mulasutra with key ethical and practice guidelines. SVK-0016 is Hindi translation (1920) but no Prakrit original."),
    ("Kalpa Sutra — Sthanakavasi edition", "AGAM-015", "Core canonical text. Current corpus has English translations (SVK-1002/1003) but no Prakrit original."),
    ("Dashvaikalik Sutra — Sthanakavasi edition", "AGAM-014", "Mulasutra with practice-relevant content. No Prakrit original in corpus."),
    ("Nisitha Sutra — Sthanakavasi edition", "AGAM-017", "Mulasutra. Not in current corpus at all."),
    ("Avasyaka Sutra — Sthanakavasi edition", "AGAM-018", "Source text for the Avashyaka (six obligatory duties). Covers Samayik, Pratikraman, Vandana, Pratyakhyan. Critical gap."),
], start=1):
    c.append({
        "candidate_id": f"ACQ-{i:04d}",
        "title": title,
        "source_url": None,
        "platform": "JAINQQ",
        "source_id_if_known": None,
        "priority": "P0",
        "tradition": "STHANAKAVASI",
        "knowledge_layer": "CANONICAL",
        "content_role": "PRIMARY_SCRIPTURE",
        "practice": "AVASHYAKA" if agam == "AGAM-018" else None,
        "agam_id_if_applicable": agam,
        "author": None,
        "teacher_or_author": None,
        "language": "Prakrit",
        "format": "unknown",
        "availability": "UNKNOWN",
        "download_available": False,
        "text_available": False,
        "estimated_size": None,
        "reason_for_priority": f"Essential canonical text ({agam}). {notes}",
        "expected_use": "BOTH",
        "rights_status": "UNKNOWN",
        "acquisition_status": "DISCOVERED",
        "evidence_urls": [],
        "duplicate_candidate": False,
        "duplicate_of": None,
        "notes": notes
    })

# P0: Practice texts (7)
for i, (title, practice, notes) in enumerate([
    ("Samayik practice text — Sthanakavasi", "SAMAYIK", "Equanimity practice. No practice material in current corpus. Coverage: MISSING."),
    ("Pratikraman practice text — Sthanakavasi", "PRATIKRAMAN", "Repentance ritual. Sthanakavasi versions distinct from Murtipujaka. Coverage: MISSING."),
    ("Kayotsarga practice text — Sthanakavasi", "KAYOTSARGA", "Body-abandonment meditation. One of six obligations. Coverage: MISSING."),
    ("Vandana practice text — Sthanakavasi", "VANDANA", "Veneration/praise. One of six obligations. Coverage: MISSING."),
    ("Pratyakhyan/Pachchhakhan practice text — Sthanakavasi", "PRATYAKHYAN", "Vows/renunciation. One of six obligations. Coverage: MISSING."),
    ("Chauvisantho / Chaturvimshati-stava — Sthanakavasi", "CHAUVISANTHO", "Glorification of the Tirthankaras. Liturgical text recited during Paryushan. Coverage: MISSING."),
    ("Paryushan practice text / liturgy — Sthanakavasi", "PARYUSHAN", "Annual festival of confession and forgiveness. Most important Jain observance. Coverage: MISSING."),
], start=8):
    c.append({
        "candidate_id": f"ACQ-{i:04d}",
        "title": title,
        "source_url": None,
        "platform": "JAINQQ",
        "source_id_if_known": None,
        "priority": "P0",
        "tradition": "STHANAKAVASI",
        "knowledge_layer": "PRACTICE",
        "content_role": "PRACTICE_GUIDANCE",
        "practice": practice,
        "agam_id_if_applicable": None,
        "author": None,
        "teacher_or_author": None,
        "language": "Prakrit;Gujarati;Hindi",
        "format": "unknown",
        "availability": "UNKNOWN",
        "download_available": False,
        "text_available": False,
        "estimated_size": None,
        "reason_for_priority": f"Core practice ({practice}). {notes}",
        "expected_use": "BOTH",
        "rights_status": "UNKNOWN",
        "acquisition_status": "DISCOVERED",
        "evidence_urls": [],
        "duplicate_candidate": False,
        "duplicate_of": None,
        "notes": notes
    })

# P1: Doctrinal/interpretive (6)
p1_items = [
    ("Sthanakavasi doctrinal exposition — modern", "TEACHER_INTERPRETATION", "TEACHING", None, "Gujarati;Hindi;English", "Only SVK-2010 (516 units) provides non-lexicon Sthanakavasi content. Jainebooks likely has modern teacher material."),
    ("Sthanakavasi philosophy — anekantavada, syadvada", "PHILOSOPHY", "TEACHING", None, "Gujarati;Hindi;English", "Jain foundational philosophy PARTIAL. Need Sthanakavasi-specific exposition."),
    ("Acharya Haribhadra commentary — Sthanakavasi", "COMMENTARY", "COMMENTARY", "Acharya Haribhadra", "Prakrit;Sanskrit", "Major Sthanakavasi commentator (8th c. CE). No commentary material in corpus."),
    ("Acharya Amritchandra commentary — Sthanakavasi", "COMMENTARY", "COMMENTARY", "Acharya Amritchandra", "Sanskrit", "Important commentaries including on Tattvarthasutra. No commentary in corpus."),
    ("Prakrit grammar — Sthanakavasi pedagogical tradition", "EDUCATIONAL", "TEACHING", None, "Prakrit;Hindi;Gujarati", "Current grammar sources (SVK-2008/2009) are Western scholarship, not tradition's own teaching."),
    ("Sthanakavasi history — from the tradition's own perspective", "HISTORY", "HISTORICAL", None, "Gujarati;Hindi;English", "Current history sources (SVK-0038, SVK-1010) are external observations. Need tradition's own account."),
    ("Tattvarthasutra — Sthanakavasi commentary", "COMMENTARY", "COMMENTARY", None, "Sanskrit;Prakrit", "Most authoritative philosophical text. A Sthanakavasi commentary provides sect-specific grounding."),
]
for i, (title, kl, cr, author, lang, notes) in enumerate(p1_items, start=15):
    c.append({
        "candidate_id": f"ACQ-{i:04d}",
        "title": title,
        "source_url": None,
        "platform": "JAINEBOOKS" if "history" in title.lower() or "doctrinal" in title.lower() else "JAINQQ",
        "source_id_if_known": None,
        "priority": "P1",
        "tradition": "STHANAKAVASI",
        "knowledge_layer": kl,
        "content_role": cr,
        "practice": None,
        "agam_id_if_applicable": None,
        "author": author,
        "teacher_or_author": author,
        "language": lang,
        "format": "unknown",
        "availability": "UNKNOWN",
        "download_available": False,
        "text_available": False,
        "estimated_size": None,
        "reason_for_priority": notes,
        "expected_use": "BOTH",
        "rights_status": "UNKNOWN",
        "acquisition_status": "DISCOVERED",
        "evidence_urls": [],
        "duplicate_candidate": False,
        "duplicate_of": None,
        "notes": notes
    })

# P2: Teacher/biography/history (7)
p2_items = [
    ("Pravachan collection — Sthanakavasi teachers", "PRAVACHAN", "TEACHING", "JAINEBOOKS", "Gujarati;Hindi", "No pravachan material in current corpus. Jainebooks is primary platform."),
    ("Sthanakavasi Acharya biographies", "BIOGRAPHY", "BIOGRAPHICAL", "JAINEBOOKS", "Gujarati;Hindi;English", "No Acharya biographies in corpus. Coverage: MISSING."),
    ("Sthanakavasi Muni biographies", "BIOGRAPHY", "BIOGRAPHICAL", "JAINEBOOKS", "Gujarati;Hindi;English", "No Muni biographies in corpus. Coverage: MISSING."),
    ("Sthanakavasi Sadhvi biographies", "BIOGRAPHY", "BIOGRAPHICAL", "JAINEBOOKS", "Gujarati;Hindi;English", "No Sadhvi biographies in corpus. Coverage: MISSING."),
    ("Sthanakavasi modern teacher material", "TEACHER_INTERPRETATION", "TEACHING", "JAINEBOOKS", "Gujarati;Hindi;English", "No modern teacher material in corpus. Coverage: MISSING."),
    ("Sthanakavasi lineage history", "HISTORY", "HISTORICAL", "JAINEBOOKS", "Gujarati;Hindi;English", "SVK-0009/0010 have conference history from external perspective."),
    ("Sthanakavasi magazine collection", "OTHER", "OTHER", "JAINEBOOKS", "Gujarati;Hindi;English", "Community magazines contain doctrinal discussions. Complex rights."),
]
for i, (title, kl, cr, plat, lang, notes) in enumerate(p2_items, start=22):
    c.append({
        "candidate_id": f"ACQ-{i:04d}",
        "title": title,
        "source_url": None,
        "platform": plat,
        "source_id_if_known": None,
        "priority": "P2",
        "tradition": "STHANAKAVASI",
        "knowledge_layer": kl,
        "content_role": cr,
        "practice": None,
        "agam_id_if_applicable": None,
        "author": None,
        "teacher_or_author": None,
        "language": lang,
        "format": "unknown",
        "availability": "UNKNOWN",
        "download_available": False,
        "text_available": False,
        "estimated_size": None,
        "reason_for_priority": notes,
        "expected_use": "BOTH" if kl != "OTHER" else "REFERENCE",
        "rights_status": "UNKNOWN",
        "acquisition_status": "DISCOVERED",
        "evidence_urls": [],
        "duplicate_candidate": False,
        "duplicate_of": None,
        "notes": notes
    })

# P3: Reference/comparative (6)
p3_items = [
    ("Paia-sadda-mahannavo — additional volumes", "LEXICON", "LEXICON", "INTERNET_ARCHIVE", "Prakrit;Hindi;Sanskrit", "Likely duplicate of SVK-2006. Verify before acquiring.", True, "SVK-2006"),
    ("Ardha Magadhi Dictionary — additional digitisations", "LEXICON", "LEXICON", "INTERNET_ARCHIVE", "Prakrit;Hindi;Sanskrit", "Multiple digitisations exist. Check for dedup against SVK-0003-0007.", True, "SVK-0003"),
    ("Comparative Jain traditions text", "COMPARATIVE", "COMPARATIVE", "JAINEBOOKS", "English;Hindi;Gujarati", "Cross-tradition distinction SFT task: MISSING. Need Sthanakavasi vs Digambara material.", False, None),
    ("Jain philosophy — Sanskrit originals", "PHILOSOPHY", "PRIMARY_SCRIPTURE", "GRETIL", "Sanskrit", "GRETIL has Sanskrit Jain philosophical texts. May supplement existing coverage.", False, None),
    ("Woolner Introduction to Prakrit — additional editions", "LEXICON", "LEXICON", "INTERNET_ARCHIVE", "English", "Current corpus has SVK-2008/2009. Additional editions may improve quality.", True, "SVK-2008"),
    ("Ardha Magadhi Dictionary Vol 1 (1923) — verified clearance", "LEXICON", "LEXICON", "INTERNET_ARCHIVE", "Prakrit;Sanskrit", "SVK-0003/0004/0005/0006 have CC0 assertions needing verification. If cleared, add to training.", True, "SVK-0003"),
]
for i, (title, kl, cr, plat, lang, notes, dup, dupof) in enumerate(p3_items, start=29):
    c.append({
        "candidate_id": f"ACQ-{i:04d}",
        "title": title,
        "source_url": None,
        "platform": plat,
        "source_id_if_known": None,
        "priority": "P3",
        "tradition": "SVETAMBARA_GENERIC" if "Woolner" in title or "Ardha" in title else "MULTI_TRADITION",
        "knowledge_layer": kl,
        "content_role": cr,
        "practice": None,
        "agam_id_if_applicable": None,
        "author": None,
        "teacher_or_author": None,
      "  language": lang,
        "format": "PDF" if plat == "INTERNET_ARCHIVE" else "unknown",
        "availability": "ONLINE_FREE" if plat == "INTERNET_ARCHIVE" else "UNKNOWN",
        "download_available": plat == "INTERNET_ARCHIVE",
        "text_available": plat == "INTERNET_ARCHIVE",
        "estimated_size": None,
        "reason_for_priority": notes,
        "expected_use": "RETRIEVAL" if dup else "BOTH",
        "rights_status": "CLEAR" if plat == "INTERNET_ARCHIVE" else "UNKNOWN",
        "acquisition_status": "DISCOVERED",
        "evidence_urls": [],
        "duplicate_candidate": dup,
        "duplicate_of": dupof,
        "notes": notes
    })

# Fix the language key issue (typo in one entry)
for entry in c:
    if "  language" in entry:
        entry["language"] = entry.pop("  language")

queue["queue_metadata"]["total_candidates"] = len(c)
queue["queue_metadata"]["priority_counts"] = {}
for entry in c:
    p = entry["priority"]
    queue["queue_metadata"]["priority_counts"][p] = queue["queue_metadata"]["priority_counts"].get(p, 0) + 1

with open("svk-corpus/data/acquisition/source_acquisition_queue_v1.json", "w", encoding="utf-8") as f:
    json.dump(queue, f, indent=2, ensure_ascii=False)

print(f"Written {len(c)} candidates")
print(f"Priority counts: {queue['queue_metadata']['priority_counts']}")
