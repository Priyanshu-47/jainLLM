"""OCR calibration, not OCR training.

WHAT THIS MODULE IS FOR
The research phase found the Internet Archive's own OCR reporting **Bengali at
46.6% confidence on a Gujarati book**. That single observation is the reason this
module exists: OCR language detection is not evidence about a text's language, and
any pipeline that trusts it will mislabel an entire Gujarati corpus as Bengali and
then train a Gujarati model on Bengali-labelled data.

So this module does three things and refuses to do a fourth:

  1. MEASURES the OCR text we have, using script evidence rather than the OCR
     engine's own opinion, and compares the two. Disagreement is the finding.
  2. COMPARES engines where more than one is actually available in this
     environment, and reports honestly when only one is (no invented benchmarks).
  3. REPORTS a per-source OCR quality record with `manual_review_required`.
  4. REFUSES to build or fine-tune an OCR model. The v0.1 objective is to choose
     the extraction route, and that is a decision, not a training run.

ENGINE STANCE
Tesseract is consulted if the binary is present; PaddleOCR and any VLM route are
recorded as unavailable with the exact reason, because inventing a comparison
against a tool that is not installed would be fabricating a result.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from svk_corpus.normalization.indic import detect_script, script_profile
from svk_corpus.normalization.unicode import unicode_quality

OCR_ENGINES: tuple[tuple[str, str], ...] = (
    ("tesseract", "Tesseract (tesseract-ocr), installed if the binary is on PATH"),
    ("paddleocr", "PaddleOCR — not installed in this environment"),
    ("vlm", "Multimodal/document OCR model — no local weights, requires a GPU "
            "and a separate evaluation budget"),
    ("indic-ocr", "Specialised Indic OCR — no maintained, openly licensed "
                  "checkpoint was verified in the research phase"),
)

# Tesseract language packs relevant to this corpus.
TESSERACT_LANGS = {"Gujarati": "guj", "Devanagari": "hin+san", "Bengali": "ben"}


@dataclass
class OcrReport:
    source_id: str
    engine: str
    page_count: int = 0
    detected_language: str = "unknown"
    detected_script: str = "unknown"
    language_confidence: str = "unknown"
    script_purity: float = 0.0
    character_count: int = 0
    replacement_character_count: int = 0
    unicode_error_count: int = 0
    estimated_ocr_noise: float = 0.0
    script_distribution: dict[str, int] = field(default_factory=dict)
    engines_evaluated: list[str] = field(default_factory=list)
    manual_review_required: bool = False
    sample_pages: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return dict(vars(self))


def available_engines() -> dict[str, bool]:
    return {
        "tesseract": shutil.which("tesseract") is not None,
        "paddleocr": False,
        "vlm": False,
        "indic-ocr": False,
    }


def engine_availability_note() -> str:
    avail = available_engines()
    if not any(avail.values()):
        return (
            "no OCR engine is installed in this environment, so OCR was NOT "
            "performed and no OCR quality claim is made. The pipeline's OCR stage "
            "is exercised only on text the Internet Archive already OCR'd, whose "
            "quality is measured below against independent script evidence."
        )
    return "available engines: " + ", ".join(sorted(k for k, v in avail.items() if v))


def probe_engines() -> list[dict[str, Any]]:
    """Record what is installed rather than what we wish were installed."""
    avail = available_engines()
    out: list[dict[str, Any]] = []
    for name, description in OCR_ENGINES:
        entry: dict[str, Any] = {
            "engine": name,
            "available": avail.get(name, False),
            "description": description,
        }
        if name == "tesseract" and avail.get("tesseract"):
            try:
                result = subprocess.run(["tesseract", "--version"], capture_output=True,
                                        text=True, timeout=20)
                entry["version"] = (result.stdout or result.stderr).splitlines()[0].strip()
                langs = subprocess.run(["tesseract", "--list-langs"], capture_output=True,
                                       text=True, timeout=20)
                entry["languages"] = sorted(
                    line.strip() for line in langs.stdout.splitlines()[1:] if line.strip()
                )
            except (OSError, subprocess.SubprocessError, IndexError) as exc:
                entry["version"] = f"probe failed: {type(exc).__name__}: {exc}"
        out.append(entry)
    return out


def ocr_pdf(path: Path, language: str = "guj", engine: str = "tesseract",
            max_pages: int = 4, dpi: int = 300) -> dict[str, Any]:
    """Run OCR on a few pages only. Returns a structured result, never raises.

    `max_pages` is small on purpose: the goal is a calibration reading, not a
    corpus-wide OCR pass. OCRing thousands of pages to prove a point we can
    establish from four pages would waste the whole milestone.
    """
    if engine != "tesseract":
        return {"status": "UNAVAILABLE", "engine": engine,
                "error": f"{engine} is not installed in this environment"}
    if shutil.which("tesseract") is None:
        return {"status": "UNAVAILABLE", "engine": "tesseract",
                "error": "tesseract binary not found on PATH"}
    if shutil.which("pdftoppm") is None:
        return {"status": "UNAVAILABLE", "engine": "tesseract",
                "error": "pdftoppm (poppler) not found, so the PDF cannot be "
                         "rasterised; Tesseract cannot read PDF directly"}

    with tempfile.TemporaryDirectory() as tmp:
        prefix = Path(tmp) / "page"
        try:
            subprocess.run(
                ["pdftoppm", "-r", str(dpi), "-f", "1", "-l", str(max_pages),
                 "-png", str(path), str(prefix)],
                check=True, capture_output=True, timeout=300,
            )
        except (subprocess.CalledProcessError, subprocess.SubprocessError, OSError) as exc:
            return {"status": "FAILED", "engine": "tesseract",
                    "error": f"rasterisation failed: {type(exc).__name__}: {exc}"}

        images = sorted(Path(tmp).glob("page*.png"))
        if not images:
            return {"status": "FAILED", "engine": "tesseract",
                    "error": "no page images produced"}
        pages: list[str] = []
        for image in images:
            try:
                result = subprocess.run(
                    ["tesseract", str(image), "stdout", "-l", language],
                    capture_output=True, text=True, timeout=300,
                )
                pages.append(result.stdout)
            except (subprocess.SubprocessError, OSError) as exc:
                pages.append("")
                pages.append(f"[page failed: {type(exc).__name__}: {exc}]")
        return {
            "status": "OK", "engine": "tesseract", "language": language,
            "dpi": dpi, "pages_attempted": len(images), "pages": pages,
        }


def build_report(source_id: str, text: str, pages: Sequence[str] | None = None,
                 engine: str = "internet-archive-derived",
                 declared_language: str = "unknown",
                 declared_script: str = "unknown",
                 native_language_claim: str | None = None) -> OcrReport:
    """Measure an OCR text layer and compare it to independent script evidence."""
    report = OcrReport(source_id=source_id, engine=engine)
    report.character_count = len(text)
    report.page_count = len(pages) if pages else 0

    script_evidence = detect_script(text, min_chars=40)
    report.detected_script = script_evidence.script
    report.script_purity = round(script_evidence.purity, 4)
    report.script_distribution = dict(
        sorted(script_evidence.distribution.items(), key=lambda kv: -kv[1])[:8]
    )

    uq = unicode_quality(text)
    report.replacement_character_count = uq["replacement_chars"]
    report.unicode_error_count = uq["control_chars"] + uq["unassigned"]

    # The language claim of the OCR engine itself, when we have one, is recorded
    # separately from anything we conclude.
    if native_language_claim:
        report.findings.append(
            f"OCR engine reported language '{native_language_claim}'; independent "
            f"script evidence says '{report.detected_script}' "
            f"({report.script_purity:.1%} purity)"
        )
        if not _agrees(native_language_claim, report.detected_script):
            report.findings.append(
                "DISAGREEMENT between the OCR engine's language detection and "
                "Unicode script evidence. The script evidence is derived from the "
                "bytes themselves and is the one to trust; non-Latin-script books "
                "are routinely misdetected by OCR language models."
            )
            report.manual_review_required = True

    report.detected_language = _infer_language_label(report.detected_script)
    report.language_confidence = "low" if report.detected_script == "unknown" else "medium"

    if declared_script not in ("unknown", "", None) and \
            report.detected_script != "unknown" and \
            declared_script != report.detected_script:
        report.findings.append(
            f"declared script '{declared_script}' but measured script is "
            f"'{report.detected_script}'"
        )
        report.manual_review_required = True

    noise = 0.0
    if report.character_count:
        noise += min(1.0, uq["replacement_chars"] / report.character_count * 200) * 0.4
        noise += min(1.0, report.unicode_error_count / report.character_count * 200) * 0.2
        if report.detected_script != "unknown":
            noise += (1.0 - report.script_purity) * 0.4
    report.estimated_ocr_noise = round(min(1.0, noise), 4)

    if report.script_purity < 0.85 and report.detected_script != "unknown":
        report.findings.append(
            f"script purity {report.script_purity:.1%} is below 85%, which in an "
            f"OCR text layer usually means either mixed-language content or "
            f"character confusion in the OCR"
        )
        report.manual_review_required = True
    if report.estimated_ocr_noise > 0.35:
        report.findings.append(
            f"estimated OCR noise {report.estimated_ocr_noise:.2f} exceeds the 0.35 "
            f"triage threshold"
        )
        report.manual_review_required = True
    if report.character_count < 2000:
        report.findings.append("fewer than 2000 characters extracted; too little "
                               "to judge OCR quality")
        report.manual_review_required = True

    if pages:
        step = max(1, len(pages) // 3)
        report.sample_pages = [
            (p[:400] + ("..." if len(p) > 400 else "")) for p in pages[::step][:3]
        ]
    return report


_SCRIPT_TO_LANGUAGE = {
    "Gujarati": "Gujarati",
    "Devanagari": "unknown (Hindi/Sanskrit/Prakrit share this script)",
    "Bengali": "Bengali",
    "Latin": "unknown (Latin script)",
}


def _infer_language_label(script: str) -> str:
    return _SCRIPT_TO_LANGUAGE.get(script, script)


def _agrees(native_claim: str, detected_script: str) -> bool:
    claim = (native_claim or "").strip().lower()
    if detected_script == "unknown":
        return True
    if detected_script == "Devanagari":
        return claim.startswith(("hin", "san", "devanagari", "mar", "nep"))
    if detected_script == "Gujarati":
        return claim.startswith(("guj", "gujarati"))
    if detected_script == "Bengali":
        return claim.startswith("ben")
    return True


def write_reports(reports: Sequence[OcrReport], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "engines": probe_engines(),
        "engine_availability": engine_availability_note(),
        "reports": [r.as_dict() for r in reports],
        "manual_review_required": sum(1 for r in reports if r.manual_review_required),
        "sources": len(reports),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_reports_csv(reports: Sequence[OcrReport], path: Path) -> Path:
    import csv
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ("source_id", "engine", "page_count", "detected_language",
              "detected_script", "language_confidence", "character_count",
              "replacement_character_count", "unicode_error_count",
              "estimated_ocr_noise", "script_purity", "manual_review_required")
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for report in reports:
            row = report.as_dict()
            writer.writerow({k: row.get(k, "") for k in fields})
    return path
