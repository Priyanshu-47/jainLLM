"""Deterministic SFT candidate passage extraction.

Extracts potentially useful source passages for future SFT dataset
construction.  Every category assignment is based on deterministic
metadata/text signals — no LLM inference, no synthetic generation.

Architecture contract:
    training_corpus.jsonl + source_manifest.csv + knowledge metadata
    → sft_candidate_passages_v1.jsonl

The output is a CANDIDATE list, not a verified SFT dataset.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Sources in priority order for SFT candidate extraction
PRIORITY_SOURCES = [
    "SVK-2015",  # Avashyaka Sutra — practice/canonical
    "SVK-2016",  # Panch-pratikraman — practice
    "SVK-2019",  # Kalpa Sutra — canonical
    "SVK-2020",  # Uttaradhyayana Sanskrit — canonical
    "SVK-2010",  # Sthanakavasi exposition
    "SVK-2011",  # Sthanakavasi text
    "SVK-2012",  # Sthanakavasi text
    "SVK-2013",  # Sthanakavasi text
    "SVK-2014",  # Sthanakavasi text
]

# Knowledge layers that are high-value for SFT
HIGH_VALUE_LAYERS = {
    "CANONICAL", "PRACTICE", "COMMENTARY", "TEACHER_INTERPRETATION",
    "PHILOSOPHY", "HISTORY", "BIOGRAPHY",
}

# Content roles that are high-value
HIGH_VALUE_ROLES = {
    "PRIMARY_SCRIPTURE", "PRACTICE_GUIDANCE", "COMMENTARY",
    "TEACHING", "HISTORICAL", "BIOGRAPHICAL",
}

# Practice keywords (evidence-based detection)
PRACTICE_KEYWORDS = {
    "SAMAYIK": ["समयिक", "samayik", "समायिक", "equanimity", "समय"],
    "PRATIKRAMAN": ["प्रतिक्रमण", "pratikraman", "प्रतिक्षमण", "प्रतिक्रम",
                     "पञ्चप्रतिक्रमण", "पच्चप्रतिक्मण", "repentance"],
    "KAYOTSARGA": ["कायोत्सर्ग", "kayotsarga", "कायौत्सर्ग", "body-abandonment",
                    "कायotsarga"],
    "VANDANA": ["वन्दना", "vandana", "वंदना", "veneration", "praise",
                "स्तुति", "stuti"],
    "PRATYAKHYAN": ["प्रत्याख्यान", "pratyakhyan", "प्रत्याख्यान", "vows",
                     "renunciation", "पच्छक्खमण", "पाच्छक्खमण"],
    "CHAUVISANTHO": ["चौवीसठो", "चौवीसअठ्ठाइ", "chauvisantho",
                      "चतुर्विंशति", "twenty-four", "तेइसिं"],
    "AVASHYAKA": ["आवश्यक", "avashyaka", "आवश्यक", "obligatory",
                   "आवश्यकीय", "six duties"],
}

# Canonical text indicators
CANONICAL_INDICATORS = [
    "आचारांग", "acaranga", "सूत्रकृतांग", "sutrakritanga",
    "उत्तराध्ययन", "uttaradhyayana", "कल्प सूत्र", "kalpa sutra",
    "दशवैकालिक", "dashvaikalik", "निशिथ", "nishith",
    "आवश्यक", "avashyaka", "समवाय", "samavaya",
    "व्याख्याप्रज्ञाप्ति", "vyakhyaprajnapti", "प्रज्ञापन", "prajnapan",
    "उपादान", "upadan", "आनुग्रहिक", "anugrahi",
    "प्रश्नव्याकरण", "prashnavyakaran", "विपाक", "vipak",
    "दृष्टिवाद", "drishtivad", "सूत्र", "sutra",
    "मूल", "mula", "अंग", "anga",
]

# Sect indicators (evidence-based)
STHANAKAVASI_INDICATORS = [
    "स्थानकवासी", "sthanakvasi", "sthānakavāsī", "sthanakavasi",
    "स्थानकवास", "स्थानकवासिन्",
]

# Minimum text length for HIGH_CONFIDENCE candidate
MIN_TEXT_LENGTH = 50

# Maximum text length (longer texts are still candidates but may need splitting)
MAX_TEXT_LENGTH = 5000


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SourceMeta:
    """Metadata from the source manifest for classification."""
    source_id: str
    title: str = ""
    author: str = ""
    tradition: str = ""
    sect: str = ""
    knowledge_layer: str = ""
    text_category: str = ""
    text_name: str = ""
    language: str = ""
    script: str = ""
    training_permission: str = ""
    religious_scope: str = ""
    religious_scope_confidence: str = ""
    religious_scope_basis: str = ""
    lineage: str = ""
    teacher_or_author: str = ""
    agam_id: str = ""
    notes: str = ""
    content_description: str = ""
    copyright_basis: str = ""

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> SourceMeta:
        return cls(
            source_id=row.get("source_id", ""),
            title=row.get("title", ""),
            author=row.get("author", ""),
            tradition=row.get("tradition", ""),
            sect=row.get("sect", ""),
            knowledge_layer=row.get("knowledge_layer", ""),
            text_category=row.get("text_category", ""),
            text_name=row.get("text_name", ""),
            language=row.get("language", ""),
            script=row.get("script", ""),
            training_permission=row.get("training_permission", ""),
            religious_scope=row.get("religious_scope", ""),
            religious_scope_confidence=row.get("religious_scope_confidence", ""),
            religious_scope_basis=row.get("religious_scope_basis", ""),
            lineage=row.get("lineage", ""),
            teacher_or_author=row.get("teacher_or_author", ""),
            agam_id=row.get("agam_id", ""),
            notes=row.get("notes", ""),
            content_description=row.get("content_description", ""),
            copyright_basis=row.get("copyright_basis", ""),
        )


@dataclass
class CandidatePassage:
    """A single SFT candidate passage with full provenance."""
    candidate_id: str
    source_id: str
    text_id: str
    text: str
    title: str
    locator: dict[str, Any]
    language: str
    script: str
    tradition: str
    religious_scope: str
    knowledge_layer: str
    content_role: str
    canonical_status: str
    teacher_or_author: str
    lineage: str
    source_quality: str
    candidate_categories: list[str]
    candidate_reason: str
    quality_flags: list[str]
    rights_status: str
    verification_status: str
    sft_status: str
    text_length: int
    duplicate_candidate: bool = False
    priority_rank: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source_id": self.source_id,
            "text_id": self.text_id,
            "text": self.text,
            "title": self.title,
            "locator": self.locator,
            "language": self.language,
            "script": self.script,
            "tradition": self.tradition,
            "religious_scope": self.religious_scope,
            "knowledge_layer": self.knowledge_layer,
            "content_role": self.content_role,
            "canonical_status": self.canonical_status,
            "teacher_or_author": self.teacher_or_author,
            "lineage": self.lineage,
            "source_quality": self.source_quality,
            "candidate_categories": self.candidate_categories,
            "candidate_reason": self.candidate_reason,
            "quality_flags": self.quality_flags,
            "rights_status": self.rights_status,
            "verification_status": self.verification_status,
            "sft_status": self.sft_status,
            "text_length": self.text_length,
            "duplicate_candidate": self.duplicate_candidate,
            "priority_rank": self.priority_rank,
        }


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def _detect_categories(text: str, meta: SourceMeta) -> tuple[list[str], str]:
    """Detect candidate categories from text content and source metadata.

    Returns (categories, reason) where reason explains the basis.
    """
    categories: list[str] = []
    reasons: list[str] = []

    text_lower = text.lower()
    title_lower = (meta.title or "").lower()
    desc_lower = (meta.content_description or "").lower()
    notes_lower = (meta.notes or "").lower()
    combined = f"{text_lower} {title_lower} {desc_lower} {notes_lower}"

    # A. Sthanakavasi sect-aware explanation
    for indicator in STHANAKAVASI_INDICATORS:
        if indicator.lower() in combined:
            categories.append("STHANAKAVASI_EXPLANATION")
            reasons.append(f"Sthanakavasi indicator '{indicator}' found in text/metadata")
            break

    # B. Agam/source-grounded explanation
    if meta.agam_id:
        categories.append("AGAM_GROUNDED")
        reasons.append(f"Source linked to {meta.agam_id}")
    elif meta.knowledge_layer == "CANONICAL":
        categories.append("AGAM_GROUNDED")
        reasons.append("Source classified as CANONICAL")

    # C. Prakrit/Sanskrit term explanation
    if meta.language in ("sa", "pr", "sa;hi", "sa;pr"):
        categories.append("PRAKRIT_SANSKIRT_TERM")
        reasons.append(f"Source language is {meta.language} (Sanskrit/Prakrit)")
    # Also detect if text contains significant Devanagari with Sanskrit markers
    devanagari_count = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    if devanagari_count > len(text) * 0.3 and any(w in text for w in ["ः", "ॐ", "॥", "श्री"]):
        if "PRAKRIT_SANSKIRT_TERM" not in categories:
            categories.append("PRAKRIT_SANSKIRT_TERM")
            reasons.append("Text contains Sanskrit markers in Devanagari")

    # D. Hindi/Gujarati/English multilingual mapping
    if meta.language in ("hi", "gu", "en"):
        categories.append("MULTILINGUAL_MAPPING")
        reasons.append(f"Source language is {meta.language}")
    elif ";" in meta.language:
        categories.append("MULTILINGUAL_MAPPING")
        reasons.append(f"Source has multiple languages: {meta.language}")

    # E. Canonical vs commentary distinction
    if meta.knowledge_layer == "CANONICAL":
        categories.append("CANONICAL_SOURCE")
        reasons.append("Source classified as CANONICAL")
    elif meta.knowledge_layer == "COMMENTARY":
        categories.append("COMMENTARY_SOURCE")
        reasons.append("Source classified as COMMENTARY")
    elif meta.knowledge_layer in ("LEXICON",):
        categories.append("LEXICON_SOURCE")
        reasons.append("Source classified as LEXICON")

    # F. Practice explanation
    for practice, keywords in PRACTICE_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in combined:
                categories.append(f"PRACTICE_{practice}")
                reasons.append(f"Practice indicator '{kw}' for {practice} found")
                break

    # G. Teacher/author attribution
    if meta.teacher_or_author and meta.teacher_or_author not in ("unknown", ""):
        categories.append("TEACHER_ATTRIBUTION")
        reasons.append(f"Teacher/author: {meta.teacher_or_author}")
    elif meta.author and meta.author not in ("unknown", ""):
        categories.append("TEACHER_ATTRIBUTION")
        reasons.append(f"Author: {meta.author}")

    # H. Historical/biographical explanation
    if meta.knowledge_layer in ("HISTORY", "BIOGRAPHY"):
        categories.append("HISTORICAL_BIOGRAPHICAL")
        reasons.append(f"Source classified as {meta.knowledge_layer}")
    elif any(w in combined for w in ["इतिहास", "history", "जीवनी", "biography",
                                      "चरित्र", "charitra"]):
        categories.append("HISTORICAL_BIOGRAPHICAL")
        reasons.append("Text contains historical/biographical indicators")

    # I. Cross-tradition distinction
    if meta.tradition in ("MULTI_TRADITION", "SVETAMBARA_GENERIC"):
        categories.append("CROSS_TRADITION")
        reasons.append(f"Source tradition: {meta.tradition}")

    # J. Abstention / insufficient-evidence behavior
    if any(w in combined for w in ["अनिश्चित", "uncertain", "विवादित", "conflict",
                                     "संदिग्ध", "doubt", "मतभेद", "disagreement",
                                     "परंपरा", "tradition says", "कहा जाता है"]):
        categories.append("ABSTENTION_EVIDENCE")
        reasons.append("Text contains uncertainty/qualification indicators")

    if not categories:
        categories.append("GENERAL_JAIN")
        reasons.append("No specific category detected; classified as general Jain material")

    return categories, "; ".join(reasons)


def _assess_quality(text: str, quality_flags: list[str]) -> str:
    """Classify candidate quality based on text and flags."""
    text_len = len(text.strip())

    # Low quality: too short, mostly garbage
    if text_len < 20:
        return "LOW_QUALITY"
    if text_len < MIN_TEXT_LENGTH:
        return "LOW_QUALITY"

    # Check for severe quality issues
    severe_flags = {"SCRIPT_CONFUSION", "OCR_NOISE_HIGH", "HIGH_SYMBOL_RATIO"}
    if severe_flags.intersection(quality_flags):
        return "REVIEW_REQUIRED"

    # Check for moderate issues
    moderate_flags = {"HIGH_DIGIT_RATIO", "VERY_SHORT", "SCRIPT_MISMATCH"}
    if moderate_flags.intersection(quality_flags):
        return "REVIEW_REQUIRED"

    return "HIGH_CONFIDENCE_CANDIDATE"


def _compute_priority_rank(source_id: str) -> int:
    """Compute priority rank (lower = higher priority)."""
    try:
        return PRIORITY_SOURCES.index(source_id) + 1
    except ValueError:
        return len(PRIORITY_SOURCES) + 1


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def load_source_metadata(manifest_path: Path) -> dict[str, SourceMeta]:
    """Load source metadata from the manifest CSV."""
    import csv
    meta: dict[str, SourceMeta] = {}
    with manifest_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row.get("source_id", "")
            if sid:
                meta[sid] = SourceMeta.from_csv_row(row)
    return meta


def extract_candidates(
    training_path: Path,
    source_meta: dict[str, SourceMeta],
    quality_path: Path | None = None,
) -> list[CandidatePassage]:
    """Extract SFT candidate passages from the training corpus.

    Applies deterministic classification based on metadata and text signals.
    """
    # Load quality data if available
    quality_data: dict[str, list[str]] = {}
    if quality_path and quality_path.is_file():
        with quality_path.open(encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                uid = row.get("unit_id", "")
                quality_data[uid] = row.get("flags", [])

    candidates: list[CandidatePassage] = []
    seen_texts: set[str] = set()

    with training_path.open(encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            source_id = record.get("source_id", "")
            text_id = record.get("id", "")
            text = record.get("normalized_text") or record.get("text", "")

            # Skip empty or very short text
            if not text.strip() or len(text.strip()) < 20:
                continue

            # Skip document-level records
            if record.get("unit_type") == "document":
                continue

            meta = source_meta.get(source_id, SourceMeta(source_id=source_id))

            # Get quality flags
            flags = quality_data.get(text_id, record.get("quality", {}).get("flags", []))
            if isinstance(flags, dict):
                flags = list(flags.keys())

            # Detect categories
            categories, reason = _detect_categories(text, meta)

            # Assess quality
            quality_status = _assess_quality(text, flags)

            # Check for near-duplicate text (simple hash-based)
            text_hash = hashlib.sha256(text.strip().encode()).hexdigest()[:16]
            is_duplicate = text_hash in seen_texts
            seen_texts.add(text_hash)

            # Compute priority
            priority = _compute_priority_rank(source_id)

            # Build candidate
            candidate = CandidatePassage(
                candidate_id=f"sft_{text_id.replace(':', '_')}",
                source_id=source_id,
                text_id=text_id,
                text=text.strip(),
                title=record.get("title", meta.title),
                locator=record.get("source_locator", {}),
                language=record.get("language", meta.language),
                script=record.get("script", meta.script),
                tradition=record.get("tradition", meta.tradition),
                religious_scope=meta.religious_scope,
                knowledge_layer=meta.knowledge_layer,
                content_role=record.get("work_role", "ORIGINAL"),
                canonical_status=meta.text_category,
                teacher_or_author=meta.teacher_or_author or meta.author,
                lineage=meta.lineage,
                source_quality=meta.religious_scope_confidence,
                candidate_categories=categories,
                candidate_reason=reason,
                quality_flags=flags if isinstance(flags, list) else [],
                rights_status=meta.training_permission,
                verification_status="UNVERIFIED",
                sft_status="CANDIDATE",
                text_length=len(text.strip()),
                duplicate_candidate=is_duplicate,
                priority_rank=priority,
            )
            candidates.append(candidate)

    return candidates


def write_candidates(
    candidates: list[CandidatePassage],
    output_path: Path,
) -> int:
    """Write candidate passages to JSONL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count


def compute_statistics(candidates: list[CandidatePassage]) -> dict[str, Any]:
    """Compute statistics about the candidate set."""
    stats: dict[str, Any] = {
        "total": len(candidates),
        "by_source": {},
        "by_category": {},
        "by_language": {},
        "by_tradition": {},
        "by_knowledge_layer": {},
        "by_quality": {"HIGH_CONFIDENCE_CANDIDATE": 0, "REVIEW_REQUIRED": 0, "LOW_QUALITY": 0},
        "by_sft_status": {},
        "duplicate_count": 0,
        "high_priority_count": 0,
        "text_length_stats": {"min": 0, "max": 0, "mean": 0},
    }

    lengths = []
    for c in candidates:
        # By source
        stats["by_source"][c.source_id] = stats["by_source"].get(c.source_id, 0) + 1

        # By category
        for cat in c.candidate_categories:
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

        # By language
        stats["by_language"][c.language] = stats["by_language"].get(c.language, 0) + 1

        # By tradition
        stats["by_tradition"][c.tradition] = stats["by_tradition"].get(c.tradition, 0) + 1

        # By knowledge layer
        stats["by_knowledge_layer"][c.knowledge_layer] = \
            stats["by_knowledge_layer"].get(c.knowledge_layer, 0) + 1

        # By quality
        if c.candidate_categories:
            pass  # quality is per-candidate, computed below

        # By SFT status
        stats["by_sft_status"][c.sft_status] = \
            stats["by_sft_status"].get(c.sft_status, 0) + 1

        # Duplicates
        if c.duplicate_candidate:
            stats["duplicate_count"] += 1

        # Priority
        if c.priority_rank <= len(PRIORITY_SOURCES):
            stats["high_priority_count"] += 1

        lengths.append(c.text_length)

    # Quality counts (need separate pass since quality is computed per-candidate)
    for c in candidates:
        q = _assess_quality(c.text, c.quality_flags)
        stats["by_quality"][q] = stats["by_quality"].get(q, 0) + 1

    if lengths:
        stats["text_length_stats"] = {
            "min": min(lengths),
            "max": max(lengths),
            "mean": round(sum(lengths) / len(lengths), 1),
        }

    return stats
