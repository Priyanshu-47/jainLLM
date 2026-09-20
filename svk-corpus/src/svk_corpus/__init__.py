"""svk-corpus — a licence-gated, provenance-complete corpus pipeline.

Design constraints (deliberate, see pyproject.toml and docs/REPRODUCIBILITY.md):
  * stdlib only, zero third-party dependencies
  * deterministic: fixed ordering, fixed seeds, hashed outputs
  * never destructive: raw text is always preserved alongside any normalised form
  * never authoritative about law: the gate is deterministic and evidence-recorded,
    and it refuses to guess
"""

__version__ = "0.1.0"

CORPUS_VERSION = "svk-corpus-v0.1"

# The six gate states. Order matters only for display; rules decide membership.
GATE_STATES = (
    "TRAINING_ALLOWED",
    "RAG_ALLOWED",
    "WITH_CONDITIONS",
    "NEEDS_PERMISSION",
    "NOT_ALLOWED",
    "UNKNOWN",
)

# States that may never appear in a released corpus, ever, under any config.
NEVER_RELEASABLE = ("NEEDS_PERMISSION", "NOT_ALLOWED", "UNKNOWN")

# Text roles. These must never be mixed into one undifferentiated field.
TEXT_ROLES = (
    "ORIGINAL",
    "TRANSCRIPTION",
    "TRANSLATION",
    "COMMENTARY",
    "ANNOTATION",
    "OCR",
    "AI_GENERATED",
)

CONFIDENCE_LEVELS = ("high", "medium", "low")

PIPELINE_VERSION = "v0.1.0"
