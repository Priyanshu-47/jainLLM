"""Quality metrics that report their evidence, individually."""

from svk_corpus.quality.checks import (  # noqa: F401
    CORE_METADATA_FIELDS,
    PROVENANCE_FIELDS,
    RepeatedLine,
    TextQuality,
    aggregate,
    assess_text,
    detect_running_headers,
    metadata_completeness,
    provenance_completeness,
    strip_running_headers,
)

__all__ = [
    "CORE_METADATA_FIELDS",
    "PROVENANCE_FIELDS",
    "RepeatedLine",
    "TextQuality",
    "aggregate",
    "assess_text",
    "detect_running_headers",
    "metadata_completeness",
    "provenance_completeness",
    "strip_running_headers",
]
