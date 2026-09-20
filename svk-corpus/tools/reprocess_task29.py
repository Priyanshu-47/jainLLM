#!/usr/bin/env python3
"""Re-extract, re-normalize, re-segment, re-assess quality for SVK-2022..2029.

Task 29: the extraction code now skips <script>/<style> HTML tags, the
normalization code detects Romanized Indic, and the quality checks distinguish
alphabetic repeat runs from layout separators.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

ROOT = Path(r"E:\JainLLM\svk-corpus")
sys.path.insert(0, str(ROOT / "src"))

from svk_corpus.config import load_config
from svk_corpus.extraction import extract_any
from svk_corpus.normalization import normalize_text, detect_script, detect_language_hint
from svk_corpus.segmentation import segment_document
from svk_corpus.quality.checks import assess_text

SOURCES = [f"SVK-{i}" for i in range(2022, 2030)]

def _now():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def reprocess():
    config = load_config()
    
    for sid in SOURCES:
        raw_dir = config.path("paths", "raw") / sid
        ext_dir = config.path("paths", "extracted") / sid
        norm_dir = config.path("paths", "normalized") / sid
        seg_dir = config.path("paths", "deduplicated").parent / "segmented" / sid
        
        if not raw_dir.is_dir():
            print(f"  SKIP {sid}: no raw directory")
            continue
        
        # Find HTML file
        html_file = None
        for f in raw_dir.iterdir():
            if f.suffix in (".html", ".htm"):
                html_file = f
                break
        
        if not html_file:
            print(f"  SKIP {sid}: no HTML file found")
            continue
        
        print(f"\n=== {sid} ===")
        
        # 1. Re-extract
        print(f"  Extracting from {html_file.name}...")
        result = extract_any(html_file)
        text = result.text
        
        ext_dir.mkdir(parents=True, exist_ok=True)
        (ext_dir / "text.txt").write_text(text, encoding="utf-8")
        with open(ext_dir / "extraction.json", "w", encoding="utf-8") as f:
            json.dump({
                "source_id": sid,
                "status": result.status,
                "method": result.method,
                "pages": len(result.pages),
                "characters": len(text),
                "error": result.error,
                "warnings": result.warnings,
                "metrics": result.metrics,
                "extracted_at": _now(),
            }, f, indent=2)
        print(f"  Extracted: {len(text)} chars, {len(result.pages)} pages")
        
        # 2. Re-normalize
        print(f"  Normalizing...")
        norm_result = normalize_text(text)
        norm_text = norm_result.normalized
        
        script_ev = detect_script(norm_text)
        lang_hint = detect_language_hint(norm_text, script=script_ev.script)
        
        norm_dir.mkdir(parents=True, exist_ok=True)
        (norm_dir / "text.txt").write_text(norm_text, encoding="utf-8")
        with open(norm_dir / "normalization.json", "w", encoding="utf-8") as f:
            json.dump({
                "source_id": sid,
                "changed": norm_result.changed,
                "declared_language": "",
                "declared_script": "",
                "detected_language_hint": lang_hint.as_dict(),
                "script_evidence": script_ev.as_dict(),
                "stats": {
                    "chars_before": len(text),
                    "chars_after": len(norm_text),
                },
                "generated_at": _now(),
                "version": "1.0",
            }, f, indent=2)
        print(f"  Script: {script_ev.script} (purity={script_ev.purity:.2%}), Lang hint: {lang_hint.language} ({lang_hint.confidence})")
        
        # 3. Re-segment
        print(f"  Segmenting...")
        units, stats = segment_document(
            norm_text,
            source_id=sid,
            language=lang_hint.language,
            script=script_ev.script,
            text_role="canonical",
        )
        seg_dir.mkdir(parents=True, exist_ok=True)
        with open(seg_dir / "units.jsonl", "w", encoding="utf-8") as f:
            for u in units:
                f.write(json.dumps(u.to_dict(), ensure_ascii=False) + "\n")
        with open(seg_dir / "segmentation.json", "w", encoding="utf-8") as f:
            json.dump({
                "source_id": sid,
                "unit_count": len(units),
                "segmented_at": _now(),
            }, f, indent=2)
        print(f"  Units: {len(units)}")
        
        # 4. Re-assess quality
        print(f"  Quality assessment...")
        flag_counts = {}
        for u in units:
            q = assess_text(
                u.text,
                language=lang_hint.language,
                script=script_ev.script,
                structural_quality=0.5,
            )
            for flag in q.flags:
                flag_counts[flag] = flag_counts.get(flag, 0) + 1
        
        print(f"  Quality flags: {dict(sorted(flag_counts.items()))}")
    
    print("\n=== DONE ===")

if __name__ == "__main__":
    reprocess()
