"""Hugging Face dataset acquisition.

Round 2: v0.1 recorded HF sources but never implemented the fetch. This module
fetches the dataset metadata (verbatim, for provenance) and the raw data file,
hashes both, and writes checksums exactly like the Internet Archive path. The
HF Hub API is plain HTTPS with no authentication for public datasets, so no new
dependencies are introduced: urllib only.

Why the parquet-branch URL rather than resolve/main: the Hub converts CSV
uploads to parquet under /api/.../parquet, but the ORIGINAL uploaded file stays
at resolve/<branch>/<filename>. We take the original CSV so the stored artifact
is byte-identical to what the authors published; it is also human-readable.
The exact filename is resolved from the file tree at fetch time rather than
hard-coded, because the listing is the only authority on it.
"""

from __future__ import annotations

import json
from typing import Any

from svk_corpus.schemas.records import ArtifactRecord, SourceRecord
from svk_corpus.acquisition.downloader import FetchResult, fetch, fetch_json

_DATASET_API = "https://huggingface.co/api/datasets"
_RESOLVE = "https://huggingface.co/datasets/{}/resolve/main/{}"


def dataset_api_url(repo_id: str) -> str:
    return f"{_DATASET_API}/{repo_id}"


def pick_data_file(tree: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Choose the original data file from the repo file tree.

    Prefers the largest CSV/JSONL/TSV/parquet under the repo root. Nothing is
    guessed beyond "a data file"; READMEs and configs are never selected.
    """
    wanted_exts = (".csv", ".jsonl", ".tsv", ".parquet", ".json")
    candidates = [f for f in tree
                  if str(f.get("path", "")).lower().endswith(wanted_exts)
                  and f.get("type") == "file"]
    if not candidates:
        return None
    return max(candidates, key=lambda f: int(f.get("size", 0) or 0))


def acquire_huggingface(source: SourceRecord, config) -> tuple[list[ArtifactRecord],
                                                              list[dict[str, str]]]:
    """Acquire one public HF dataset. Returns (artifacts, failures)."""
    from pathlib import Path  # local import keeps module import graph flat

    repo_id = source.get("acquisition_identifier")
    artifacts: list[ArtifactRecord] = []
    failures: list[dict[str, str]] = []
    if not repo_id:
        failures.append({"source_id": source.source_id, "url": "",
                         "error": "no acquisition_identifier in the manifest",
                         "kind": "configuration"})
        return artifacts, failures

    meta_url = dataset_api_url(repo_id)
    metadata, result = fetch_json(meta_url, config)
    if metadata is None:
        failures.append({"source_id": source.source_id, "url": meta_url,
                         "error": result.error or "could not fetch dataset metadata",
                         "kind": "metadata"})
        return artifacts, failures

    base = Path(config.path("paths", "raw")) / source.source_id
    base.mkdir(parents=True, exist_ok=True)
    meta_path = base / "metadata.json"
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    artifacts.append(ArtifactRecord({
        "artifact_id": ArtifactRecord.new_id(source.source_id, "HF_METADATA",
                                             result.sha256 or "nometa"),
        "source_id": source.source_id,
        "artifact_type": "SOURCE_METADATA",
        "filename": "metadata.json",
        "sha256": result.sha256 or "",
        "bytes": str(meta_path.stat().st_size),
        "mime_type": "application/json",
        "status": "OK",
        "source_url": f"https://huggingface.co/datasets/{repo_id}",
        "error": "",
    }))

    # The file tree needs a second API call; datasets payloads embed "siblings"
    # (file listing) directly, so prefer that before falling back to /tree/main.
    siblings = metadata.get("siblings") or []
    tree = [{"path": s.get("rfilename", ""), "type": "file"} for s in siblings
            if s.get("rfilename")]
    if not tree:
        tree_json, tree_res = fetch_json(f"{meta_url}/tree/main", config)
        if tree_json is None:
            failures.append({"source_id": source.source_id,
                             "url": f"{meta_url}/tree/main",
                             "error": tree_res.error or "could not list dataset files",
                             "kind": "metadata"})
            return artifacts, failures
        tree = tree_json

    chosen = pick_data_file(tree)
    if chosen is None:
        failures.append({"source_id": source.source_id, "url": meta_url,
                         "error": "no data file found in the dataset tree",
                         "kind": "no_derivative"})
        return artifacts, failures

    url = _RESOLVE.format(repo_id, chosen["path"])
    dest = base / Path(chosen["path"]).name
    dl: FetchResult = fetch(url, dest, config)
    if not dl.ok:
        failures.append({"source_id": source.source_id, "url": url,
                         "error": dl.error, "kind": "download"})
        return artifacts, failures

    artifact = ArtifactRecord(
        dl.to_row(ArtifactRecord.new_id(source.source_id, "CSV", dl.sha256),
                  source.source_id, "CSV")
    )
    artifact.values["extraction_method"] = "SOURCE_STRUCTURED_DATA"
    artifacts.append(artifact)
    (base / "checksums.sha256").write_text(
        f"{dl.sha256}  {dest.name}\n", encoding="utf-8")
    return artifacts, failures
