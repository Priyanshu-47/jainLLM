"""Deterministic SFT candidate passage extraction — v2 (strict eligibility).

CORRECTED from v1 which was too permissive:
- v1 classified every training unit as a candidate
- v1 used source-level metadata as passage-level evidence
- v1 conflated language with multilingual mapping
- v1 conflated source author with teacher attribution

v2 rules:
- A candidate must contain enough information to support a meaningful
  future instruction example
- Categories require PASSAGE-LEVEL evidence, not just source metadata
- Source metadata provides provenance, not automatic eligibility
- Every category assignment records its evidence basis

Architecture contract:
    training_corpus.jsonl + source_manifest.csv + quality data
    → sft_candidate_passages_v2.jsonl
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

# Minimum text length for any candidate
MIN_TEXT_LENGTH = 40

# Minimum text length for HIGH_CONFIDENCE
MIN_HIGH_CONFIDENCE_LENGTH = 80

# Maximum text length
MAX_TEXT_LENGTH = 5000

# ---------------------------------------------------------------------------
# Passage-level evidence patterns
# ---------------------------------------------------------------------------

# Teacher attribution: passage must contain explicit attribution
TEACHER_ATTRIBUTION_PATTERNS = [
    # Hindi/Hindi-style attribution
    r"(?:आचार्य|मुनि|साध्वी|स्वामी|गणिवर|पंडित|शास्त्री)\s+\S+",
    r"(?:कहते हैं|कहा|बोले|उपदेश|प्रवचन|वचन)",
    r"(?:according to|says|said|states|writes|teaches)",
    # English attribution
    r"(?:Acharya|Muni|Sadhvi|Swami|Ganivar|Pandit)\s+\S+",
    r"(?:pravachan|discourse|sermon)",
]

# Multilingual mapping: passage must contain actual cross-language content
MULTILINGUAL_PATTERNS = [
    # Prakrit/Sanskrit term followed by Hindi/Gujarati explanation
    r"[\u0900-\u097F]{2,}\s*[-=:]\s*[\u0900-\u097F]{2,}",
    # English term followed by Indic explanation or vice versa
    r"[a-zA-Z]{3,}\s*[-=:]\s*[\u0900-\u097F]{2,}",
    r"[\u0900-\u097F]{2,}\s*[-=:]\s*[a-zA-Z]{3,}",
    # Bilingual heading/label pattern
    r"\(.*[\u0900-\u097F].*\)|\(.*[a-zA-Z].*\)",
]

# Practice explanation: passage must explain, define, or describe practice
PRACTICE_EXPLANATION_PATTERNS = {
    "SAMAYIK": [
        r"समयिक.{0,30}(?:कर्म|विधि|अर्थ|महत्व|क्या है)",
        r"samayik.{0,30}(?:practice|meaning|observance|equanimity)",
    ],
    "PRATIKRAMAN": [
        r"प्रतिक्रमण.{0,30}(?:कर्म|विधि|अर्थ|महत्व|क्या है|पञ्च)",
        r"pratikraman.{0,30}(?:practice|meaning|repentance|ritual)",
    ],
    "KAYOTSARGA": [
        r"कायोत्सर्ग.{0,30}(?:कर्म|विधि|अर्थ|महत्व|क्या है)",
        r"kayotsarga.{0,30}(?:practice|meaning|meditation|body-abandonment)",
    ],
    "VANDANA": [
        r"वन्दना.{0,30}(?:कर्म|विधि|अर्थ|महत्व|क्या है)",
        r"vandana.{0,30}(?:practice|meaning|veneration|praise)",
    ],
    "PRATYAKHYAN": [
        r"प्रत्याख्यान.{0,30}(?:कर्म|विधि|अर्थ|महत्व|क्या है|दीक्षा)",
        r"pratyakhyan.{0,30}(?:practice|meaning|vows|renunciation)",
    ],
    "CHAUVISANTHO": [
        r"चौवीस.{0,30}(?:स्तोत्र|स्तुति|अर्थ|महत्व|क्या है)",
        r"chauvisantho.{0,30}(?:praise|glorification|twenty-four)",
    ],
    "AVASHYAKA": [
        r"आवश्यक.{0,30}(?:कर्म|विधि|अर्थ|महत्व|क्या है|छह)",
        r"avashyaka.{0,30}(?:practice|meaning|duties|obligatory)",
    ],
}

# Sthanakavasi explanation: passage must explain something specific to Sthanakavasi
STHANAKAVASI_PASSAGE_PATTERNS = [
    r"स्थानकवासी.{0,40}(?:सम्प्रदाय|परम्परा|मत|विचार|धर्म|क्या है)",
    r"sthanakvasi.{0,40}(?:tradition|sect|school|practice|belief)",
    r"स्थानकवासी.{0,40}(?:विरोध|भेद|तुलना|अंतर)",
    r"sthanakvasi.{0,40}(?:versus|differs|contrast|distinction)",
]

# Agam citation: passage must reference a specific Agam
AGAM_CITATION_PATTERNS = [
    r"(?:आचारांग|सूत्रकृतांग|उत्तराध्ययन|कल्प|दशवैकालिक|निशिथ|आवश्यक)",
    r"(?:acaranga|sutrakritanga|uttaradhyayana|kalpa|dashvaikalik|nishith|avashyaka)",
    r"(?:अंग\s*\d|anga\s*\d|सूत्र\s*\d|sutra\s*\d)",
]

# Term + explanation pattern for lexicon candidates
TERM_EXPLANATION_PATTERNS = [
    # Devanagari term followed by explanation (allow spaces in explanation)
    r"[\u0900-\u097F]{2,8}\s*[-=:]\s*[\u0900-\u097F\s]{10,}",
    # English term followed by explanation
    r"[a-zA-Z]{3,15}\s*[-=:]\s*[a-zA-Z\s]{10,}",
    # Definition-style patterns
    r"(?:अर्थ|meaning|definition|व्याख्या)\s*[:=]",
]

# Historical/biographical evidence patterns
HISTORICAL_PATTERNS = [
    r"(?:इतिहास|history|ऐतिहासिक|historical)",
    r"(?:जीवनी|biography|चरित्र|charitra|वंशावली|genealogy)",
    r"(?:स्थापना|established|founded|founded in)",
    r"(?:\d{3,4}\s*(?:ईस्वी|ई\.|AD|CE|बीसी|BC))",
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SourceMeta:
    """Metadata from the source manifest for classification."""
    source_id: str = ""
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
    evidence_fields: dict[str, str]
    quality_flags: list[str]
    rights_status: str
    verification_status: str
    sft_status: str
    text_length: int
    duplicate_candidate: bool = False
    priority_rank: int = 0
    excluded: bool = False
    exclusion_reason: str = ""

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
            "evidence_fields": self.evidence_fields,
            "quality_flags": self.quality_flags,
            "rights_status": self.rights_status,
            "verification_status": self.verification_status,
            "sft_status": self.sft_status,
            "text_length": self.text_length,
            "duplicate_candidate": self.duplicate_candidate,
            "priority_rank": self.priority_rank,
            "excluded": self.excluded,
            "exclusion_reason": self.exclusion_reason,
        }


# ---------------------------------------------------------------------------
# Passage-level evidence detection (STRICT)
# ---------------------------------------------------------------------------

def _match_any(patterns: list[str], text: str) -> str | None:
    """Return first matching pattern, or None."""
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return None


def _detect_categories_strict(text: str, meta: SourceMeta) -> tuple[list[str], str, dict[str, str]]:
    """Detect candidate categories using PASSAGE-LEVEL evidence only.

    Returns (categories, reason, evidence_fields).
    Source metadata provides provenance context but does NOT automatically
    create semantic categories.
    """
    categories: list[str] = []
    reasons: list[str] = []
    evidence: dict[str, str] = {}

    # --- Minimum quality gate ---
    text_stripped = text.strip()
    text_len = len(text_stripped)

    if text_len < MIN_TEXT_LENGTH:
        return ["EXCLUDED"], "Text too short for meaningful classification", {}

    # --- LEXICON_REFERENCE (check before MULTILINGUAL since = patterns overlap) ---
    if meta.knowledge_layer == "LEXICON":
        term_match = _match_any(TERM_EXPLANATION_PATTERNS, text_stripped)
        if term_match:
            categories.append("LEXICON_REFERENCE")
            reasons.append("Lexicon passage with meaningful term + explanation")
            evidence["lexicon_type"] = "term_with_explanation"
            evidence["term_explanation_signal"] = term_match[:100]

    # --- A. TEACHER ATTRIBUTION (passage-level only) ---
    teacher_match = _match_any(TEACHER_ATTRIBUTION_PATTERNS, text_stripped)
    if teacher_match:
        categories.append("TEACHER_ATTRIBUTION")
        reasons.append(f"Passage contains explicit teacher attribution: '{teacher_match[:50]}'")
        evidence["teacher_attribution_signal"] = teacher_match[:100]

    # --- B. MULTILINGUAL_MAPPING (passage must contain cross-language content) ---
    # Skip if already classified as LEXICON_REFERENCE (the = pattern overlaps)
    if "LEXICON_REFERENCE" not in categories:
        ml_match = _match_any(MULTILINGUAL_PATTERNS, text_stripped)
        if ml_match:
            categories.append("MULTILINGUAL_MAPPING")
            reasons.append(f"Passage contains cross-language content: '{ml_match[:50]}'")
            evidence["multilingual_signal"] = ml_match[:100]

    # --- C. PRACTICE_EXPLANATION (passage must explain practice) ---
    for practice, patterns in PRACTICE_EXPLANATION_PATTERNS.items():
        match = _match_any(patterns, text_stripped)
        if match:
            categories.append(f"PRACTICE_{practice}")
            reasons.append(f"Passage explains {practice}: '{match[:50]}'")
            evidence[f"practice_{practice.lower()}_signal"] = match[:100]

    # --- D. STHANAKAVASI_EXPLANATION (passage must explain Sthanakavasi-specific content) ---
    sthana_match = _match_any(STHANAKAVASI_PASSAGE_PATTERNS, text_stripped)
    if sthana_match:
        categories.append("STHANAKAVASI_EXPLANATION")
        reasons.append(f"Passage explains Sthanakavasi-specific content: '{sthana_match[:50]}'")
        evidence["sthanakvasi_signal"] = sthana_match[:100]

    # --- E. AGAM_GROUNDED (passage must reference specific Agam) ---
    agam_match = _match_any(AGAM_CITATION_PATTERNS, text_stripped)
    if agam_match:
        categories.append("AGAM_GROUNDED")
        reasons.append(f"Passage references Agam: '{agam_match[:50]}'")
        evidence["agam_citation_signal"] = agam_match[:100]
        if meta.agam_id:
            evidence["source_agam_id"] = meta.agam_id

    # --- F. PRAKRIT_SANSKIRT_TERM (passage must contain term + explanation) ---
    if "LEXICON_REFERENCE" not in categories:
        term_match = _match_any(TERM_EXPLANATION_PATTERNS, text_stripped)
        if term_match:
            categories.append("PRAKRIT_SANSKIRT_TERM")
            reasons.append(f"Passage contains term + explanation: '{term_match[:50]}'")
            evidence["term_explanation_signal"] = term_match[:100]

    # --- G. HISTORICAL_BIOGRAPHICAL (passage must contain historical evidence) ---
    hist_match = _match_any(HISTORICAL_PATTERNS, text_stripped)
    if hist_match:
        categories.append("HISTORICAL_BIOGRAPHICAL")
        reasons.append(f"Passage contains historical/biographical evidence: '{hist_match[:50]}'")
        evidence["historical_signal"] = hist_match[:100]

    # --- H. CANONICAL_SOURCE (source-level provenance, not passage category) ---
    # This is provenance metadata, not a passage category — record but don't count
    # as a semantic category
    if meta.agam_id:
        evidence["source_agam_id"] = meta.agam_id
    if meta.knowledge_layer:
        evidence["source_knowledge_layer"] = meta.knowledge_layer



    # --- Fallback: check if passage has enough semantic content ---
    if not categories:
        # Check for general semantic completeness
        if text_len >= MIN_HIGH_CONFIDENCE_LENGTH:
            # Has substantial text but no specific category detected
            categories.append("GENERAL_JAIN_CONTENT")
            reasons.append("Substantial text without specific category markers")
        else:
            # Short text without specific markers — exclude
            return ["EXCLUDED"], "Text too short and lacks specific category markers", {}

    return categories, "; ".join(reasons), evidence


def _assess_quality_strict(text: str, quality_flags: list[str]) -> str:
    """Strict quality assessment."""
    text_len = len(text.strip())

    if text_len < MIN_TEXT_LENGTH:
        return "LOW_QUALITY"

    # Severe flags → exclude
    severe_flags = {"SCRIPT_CONFUSION", "OCR_NOISE_HIGH", "HIGH_SYMBOL_RATIO"}
    if severe_flags.intersection(quality_flags):
        return "REVIEW_REQUIRED"

    # Moderate flags → review
    moderate_flags = {"HIGH_DIGIT_RATIO", "SCRIPT_MISMATCH"}
    if moderate_flags.intersection(quality_flags):
        return "REVIEW_REQUIRED"

    # VERY_SHORT is a quality flag but we already check length above
    if "VERY_SHORT" in quality_flags and text_len < MIN_HIGH_CONFIDENCE_LENGTH:
        return "REVIEW_REQUIRED"

    if text_len >= MIN_HIGH_CONFIDENCE_LENGTH:
        return "HIGH_CONFIDENCE_CANDIDATE"

    return "REVIEW_REQUIRED"


def _is_excluded(categories: list[str], text: str, quality_flags: list[str]) -> tuple[bool, str]:
    """Determine if a passage should be excluded entirely."""
    text_len = len(text.strip())

    # Too short
    if text_len < MIN_TEXT_LENGTH:
        return True, f"Text too short ({text_len} chars < {MIN_TEXT_LENGTH})"

    # Only EXCLUDED category
    if categories == ["EXCLUDED"]:
        return True, "Failed category eligibility"

    # OCR garbage
    if "OCR_NOISE_HIGH" in quality_flags and text_len < MIN_HIGH_CONFIDENCE_LENGTH:
        return True, "OCR noise with insufficient length"

    # Mostly digits/symbols
    if "HIGH_DIGIT_RATIO" in quality_flags and "HIGH_SYMBOL_RATIO" in quality_flags:
        return True, "High digit + symbol ratio"

    return False, ""


def _compute_priority_rank(source_id: str) -> int:
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
) -> tuple[list[CandidatePassage], dict[str, Any]]:
    """Extract SFT candidate passages with strict eligibility.

    Returns (candidates, stats) where stats includes exclusion counts.
    """
    quality_data: dict[str, list[str]] = {}
    if quality_path and quality_path.is_file():
        with quality_path.open(encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                uid = row.get("unit_id", "")
                quality_data[uid] = row.get("flags", [])

    candidates: list[CandidatePassage] = []
    excluded_count = 0
    exclusion_reasons: dict[str, int] = {}
    seen_texts: set[str] = set()
    total_read = 0

    with training_path.open(encoding="utf-8") as f:
        for line in f:
            total_read += 1
            record = json.loads(line)
            source_id = record.get("source_id", "")
            text_id = record.get("id", "")
            text = record.get("normalized_text") or record.get("text", "")

            if record.get("unit_type") == "document":
                continue

            if not text.strip():
                continue

            meta = source_meta.get(source_id, SourceMeta(source_id=source_id))

            flags = quality_data.get(text_id, record.get("quality", {}).get("flags", []))
            if isinstance(flags, dict):
                flags = list(flags.keys())

            # Strict category detection
            categories, reason, evidence = _detect_categories_strict(text, meta)

            # Quality assessment
            quality_status = _assess_quality_strict(text, flags)

            # Exclusion check
            excluded, excl_reason = _is_excluded(categories, text, flags)
            if excluded:
                excluded_count += 1
                exclusion_reasons[excl_reason] = exclusion_reasons.get(excl_reason, 0) + 1
                continue

            # Duplicate check
            text_hash = hashlib.sha256(text.strip().encode()).hexdigest()[:16]
            is_duplicate = text_hash in seen_texts
            seen_texts.add(text_hash)

            priority = _compute_priority_rank(source_id)

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
                evidence_fields=evidence,
                quality_flags=flags if isinstance(flags, list) else [],
                rights_status=meta.training_permission,
                verification_status="UNVERIFIED",
                sft_status="CANDIDATE",
                text_length=len(text.strip()),
                duplicate_candidate=is_duplicate,
                priority_rank=priority,
                excluded=excluded,
                exclusion_reason=excl_reason,
            )
            candidates.append(candidate)

    stats = {
        "total_read": total_read,
        "eligible_candidates": len(candidates),
        "excluded": excluded_count,
        "exclusion_reasons": exclusion_reasons,
    }
    return candidates, stats


def write_candidates(candidates: list[CandidatePassage], output_path: Path) -> int:
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
        stats["by_source"][c.source_id] = stats["by_source"].get(c.source_id, 0) + 1
        for cat in c.candidate_categories:
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
        stats["by_language"][c.language] = stats["by_language"].get(c.language, 0) + 1
        stats["by_tradition"][c.tradition] = stats["by_tradition"].get(c.tradition, 0) + 1
        stats["by_knowledge_layer"][c.knowledge_layer] = \
            stats["by_knowledge_layer"].get(c.knowledge_layer, 0) + 1
        stats["by_sft_status"][c.sft_status] = \
            stats["by_sft_status"].get(c.sft_status, 0) + 1
        if c.duplicate_candidate:
            stats["duplicate_count"] += 1
        if c.priority_rank <= len(PRIORITY_SOURCES):
            stats["high_priority_count"] += 1
        lengths.append(c.text_length)

    for c in candidates:
        q = _assess_quality_strict(c.text, c.quality_flags)
        stats["by_quality"][q] = stats["by_quality"].get(q, 0) + 1

    if lengths:
        stats["text_length_stats"] = {
            "min": min(lengths),
            "max": max(lengths),
            "mean": round(sum(lengths) / len(lengths), 1),
        }

    return stats
