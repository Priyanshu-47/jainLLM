"""OCR calibration and measurement. This package does not train OCR models."""

from svk_corpus.ocr.pipeline import (  # noqa: F401
    OCR_ENGINES,
    OcrReport,
    available_engines,
    build_report,
    engine_availability_note,
    ocr_pdf,
    probe_engines,
    write_reports,
    write_reports_csv,
)

__all__ = [
    "OCR_ENGINES",
    "OcrReport",
    "available_engines",
    "build_report",
    "engine_availability_note",
    "ocr_pdf",
    "probe_engines",
    "write_reports",
    "write_reports_csv",
]
