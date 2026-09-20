"""Internet Archive acquisition.

Two decisions are made here and both are recorded:

  1. WHICH derivative to fetch. A scanned book offers many: an OCR text layer
     (`DjVuTXT`), an OCR XML with word positions (`Djvu XML` / `hOCR`), PDFs, an
     EPUB, or page images. We prefer the cheapest machine-readable text, and we
     explicitly do NOT treat the OCR text layer as ground truth — its quality is
     measured downstream.

  2. WHETHER to download at all. Sources that fail the licence gate are NOT
     downloaded; only their metadata is retained, as an evidence trail.
"""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

from svk_corpus.acquisition.downloader import FetchResult, fetch, fetch_json
from svk_corpus.config import Config
from svk_corpus.schemas.records import ArtifactRecord, SourceRecord

# File extensions per IA format, used only to name the local artifact.
_FORMAT_EXTENSIONS = {
    "DjVuTXT": ".txt",
    "Text PDF": ".pdf",
    "Image Container PDF": ".pdf",
    "EPUB": ".epub",
    "hOCR": ".html",
    "Djvu XML": ".xml",
    "JP2": ".jp2",
    "MPEG4": ".mp4",
}


def metadata_url(identifier: str, config: Config) -> str:
    return f"{config.get('acquisition', 'ia_endpoint', 'https://archive.org').rstrip('/')}" \
           f"/metadata/{identifier}"


def download_url(identifier: str, filename: str, config: Config) -> str:
    """Build a download URL, percent-encoding the path.

    Internet Archive filenames routinely contain spaces (e.g.
    'Jaina psychology_djvu.txt'). Passing those into urllib raises
    `InvalidURL: URL can't contain control characters`, so the path is quoted
    here rather than at the call site.
    """
    base = config.get("acquisition", "ia_endpoint", "https://archive.org").rstrip("/")
    safe_id = urllib.parse.quote(identifier, safe="")
    safe_name = urllib.parse.quote(filename, safe="")
    return f"{base}/download/{safe_id}/{safe_name}"


def fetch_item_metadata(source: SourceRecord, config: Config) -> dict | None:
    identifier = source.get("acquisition_identifier")
    if not identifier:
        return None
    data, _ = fetch_json(metadata_url(identifier, config), config)
    return data if isinstance(data, dict) else None


def select_derivative(metadata: dict, config: Config) -> dict | None:
    """Pick the best machine-readable derivative using the configured preference."""
    preference = list(config.get("acquisition", "ia_derivative_preference", []))
    denied = set(config.get("acquisition", "ia_derivative_denylist", []))
    files = metadata.get("files", []) or []

    ranked: list[tuple[int, dict]] = []
    for entry in files:
        fmt = entry.get("format", "")
        name = entry.get("name", "")
        if fmt in denied or not name:
            continue
        if fmt not in preference:
            continue
        rank = preference.index(fmt)
        size = _int_or_none(entry.get("size")) or 0
        ranked.append((rank, {"format": fmt, "name": name, "size": size,
                              "sha1": entry.get("sha1", ""),
                              "md5": entry.get("md5", "")}))
    if not ranked:
        return None
    ranked.sort(key=lambda item: (item[0], -item[1]["size"]))
    return ranked[0][1]


def _int_or_none(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def acquire_item(source: SourceRecord, config: Config,
                 releasable: bool) -> tuple[list[ArtifactRecord], list[dict[str, str]]]:
    """Acquire one Internet Archive item.

    Returns (artifacts, failures). When `releasable` is False only metadata is
    written, into the quarantine area, and no text is downloaded.
    """
    identifier = source.get("acquisition_identifier")
    artifacts: list[ArtifactRecord] = []
    failures: list[dict[str, str]] = []
    if not identifier:
        failures.append({"source_id": source.source_id, "url": "",
                         "error": "no acquisition_identifier in the manifest",
                         "kind": "configuration"})
        return artifacts, failures

    metadata = fetch_item_metadata(source, config)
    if metadata is None:
        failures.append({"source_id": source.source_id,
                         "url": metadata_url(identifier, config),
                         "error": "could not fetch item metadata", "kind": "metadata"})
        return artifacts, failures

    base = (config.path("paths", "raw") if releasable
            else config.path("paths", "quarantine")) / source.source_id
    base.mkdir(parents=True, exist_ok=True)

    meta_path = base / "metadata.json"
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    artifacts.append(ArtifactRecord({
        "artifact_id": ArtifactRecord.new_id(source.source_id, "metadata",
                                             _pseudo_hash(meta_path)),
        "source_id": source.source_id,
        "artifact_type": "SOURCE_METADATA",
        "filename": "metadata.json",
        "sha256": _pseudo_hash(meta_path),
        "bytes": str(meta_path.stat().st_size),
        "mime_type": "application/json",
        "status": "OK",
        "source_url": metadata_url(identifier, config),
        "error": "",
    }))

    if not releasable:
        # Evidence trail only. We do not download text we are not allowed to hold.
        return artifacts, failures

    chosen = select_derivative(metadata, config)
    if chosen is None:
        failures.append({"source_id": source.source_id,
                         "url": metadata_url(identifier, config),
                         "error": "no acceptable derivative found among the item files",
                         "kind": "no_derivative"})
        _write_metadata_only(base, source, "NO_DERIVATIVE", artifacts)
        return artifacts, failures

    extension = _FORMAT_EXTENSIONS.get(chosen["format"], ".bin")
    dest = base / f"original{extension}"
    url = download_url(identifier, chosen["name"], config)
    result: FetchResult = fetch(url, dest, config)

    if not result.ok:
        failures.append({"source_id": source.source_id, "url": url,
                         "error": result.error, "kind": "download"})
        _write_metadata_only(base, source, "DOWNLOAD_FAILED", artifacts)
        return artifacts, failures

    artifact = ArtifactRecord(
        result.to_row(ArtifactRecord.new_id(source.source_id, chosen["format"],
                                            result.sha256),
                      source.source_id, chosen["format"])
    )
    if extension == ".txt":
        artifact.values["extraction_method"] = "SOURCE_TEXT_LAYER"
    elif extension in (".html", ".xml"):
        artifact.values["extraction_method"] = "SOURCE_OCR_MARKUP"
    artifacts.append(artifact)

    (base / "checksums.sha256").write_text(
        f"{result.sha256}  {dest.name}\n", encoding="utf-8")
    return artifacts, failures


def _pseudo_hash(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_metadata_only(base: Path, source: SourceRecord, status: str,
                         artifacts: list[ArtifactRecord]) -> None:
    """Record why an item yielded no text, inside the artifact directory."""
    payload = {
        "source_id": source.source_id,
        "identifier": source.get("acquisition_identifier"),
        "status": status,
    }
    (base / "acquisition_status.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    artifacts.append(ArtifactRecord({
        "artifact_id": ArtifactRecord.new_id(source.source_id, "status", status),
        "source_id": source.source_id,
        "artifact_type": "ACQUISITION_STATUS",
        "filename": "acquisition_status.json",
        "sha256": _pseudo_hash(base / "acquisition_status.json"),
        "bytes": str((base / "acquisition_status.json").stat().st_size),
        "mime_type": "application/json",
        "status": status,
        "source_url": source.get("source_url"),
        "error": status,
    }))
