"""HTTP acquisition primitives (stdlib only).

Design notes:
  * `urllib.request` rather than `requests`, to keep the pipeline install-free.
  * Every download is written to `<dest>.part` and atomically renamed, so an
    interrupted run never leaves a truncated file that looks complete.
  * Every artifact is sha256-hashed while streaming, and the hash is recorded.
  * Failures are recorded with URL + status + error and are NEVER converted into
    a successful-looking result.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from svk_corpus.config import Config

_LAST_REQUEST: dict[str, float] = {}


@dataclass
class FetchResult:
    url: str
    status: str                     # "OK" | "FAILED" | "TOO_LARGE" | "SKIPPED"
    path: Path | None = None
    http_status: int | None = None
    bytes: int = 0
    sha256: str = ""
    content_type: str = ""
    error: str = ""
    attempts: int = 0
    elapsed_seconds: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "OK"

    def to_row(self, artifact_id: str, source_id: str, artifact_type: str) -> dict[str, str]:
        import datetime as _dt
        return {
            "artifact_id": artifact_id,
            "source_id": source_id,
            "artifact_type": artifact_type,
            "filename": self.path.name if self.path else "",
            "sha256": self.sha256,
            "bytes": str(self.bytes),
            "mime_type": self.content_type,
            "download_timestamp": _dt.datetime.now(_dt.timezone.utc)
            .replace(microsecond=0).isoformat(),
            "extraction_method": "",
            "ocr_method": "",
            "normalization_version": "",
            "source_url": self.url,
            "status": self.status,
            "error": self.error,
        }


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _rate_limit(host: str, seconds: float) -> None:
    if seconds <= 0:
        return
    last = _LAST_REQUEST.get(host)
    if last is not None:
        wait = seconds - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)
    _LAST_REQUEST[host] = time.monotonic()


def _open(url: str, config: Config):
    headers = {
        "User-Agent": str(config.get("acquisition", "user_agent", "svk-corpus/0.1")),
        "Accept": "*/*",
        "Accept-Encoding": "identity",
    }
    request = urllib.request.Request(url, headers=headers)
    timeout = float(config.get("acquisition", "timeout_seconds", 90))
    return urllib.request.urlopen(request, timeout=timeout)


def fetch(url: str, dest: Path, config: Config,
          expected_sha256: str | None = None) -> FetchResult:
    """Download `url` to `dest`. Returns a FetchResult; never raises for HTTP errors."""
    retries = int(config.get("acquisition", "retries", 3))
    backoff = float(config.get("acquisition", "retry_backoff_seconds", 2.0))
    limit = int(config.get("acquisition", "max_bytes_per_artifact", 300_000_000))
    rate = float(config.get("acquisition", "rate_limit_seconds", 1.0))
    host = urllib.parse.urlparse(url).netloc

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 0:
        digest = sha256_file(dest)
        if expected_sha256 is None or digest == expected_sha256:
            return FetchResult(url=url, status="OK", path=dest,
                               bytes=dest.stat().st_size, sha256=digest,
                               content_type="cached", error="reused existing artifact")

    part = dest.with_suffix(dest.suffix + ".part")
    last_error = ""
    started = time.monotonic()

    for attempt in range(1, retries + 1):
        try:
            _rate_limit(host, rate)
            with _open(url, config) as response:
                content_type = response.headers.get("Content-Type", "")
                declared = response.headers.get("Content-Length")
                if declared is not None and int(declared) > limit:
                    return FetchResult(url=url, status="TOO_LARGE", http_status=200,
                                       content_type=content_type,
                                       error=f"Content-Length {declared} exceeds limit {limit}",
                                       attempts=attempt)
                digest = hashlib.sha256()
                total = 0
                with part.open("wb") as fh:
                    while True:
                        chunk = response.read(1 << 20)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > limit:
                            fh.close()
                            part.unlink(missing_ok=True)
                            return FetchResult(url=url, status="TOO_LARGE",
                                               content_type=content_type,
                                               error=f"download exceeded limit {limit}",
                                               attempts=attempt)
                        digest.update(chunk)
                        fh.write(chunk)
            digest_hex = digest.hexdigest()
            if expected_sha256 and digest_hex != expected_sha256:
                # A mismatch is an error, not a warning: the artifact is discarded.
                part.unlink(missing_ok=True)
                return FetchResult(url=url, status="FAILED", http_status=200,
                                   bytes=total, sha256=digest_hex,
                                   content_type=content_type, attempts=attempt,
                                   error=f"sha256 mismatch: expected {expected_sha256}, "
                                         f"got {digest_hex}")
            part.replace(dest)
            return FetchResult(url=url, status="OK", path=dest, http_status=200,
                               bytes=total, sha256=digest_hex,
                               content_type=content_type, attempts=attempt,
                               elapsed_seconds=time.monotonic() - started)
        except urllib.error.HTTPError as exc:
            part.unlink(missing_ok=True)
            last_error = f"HTTP {exc.code} {exc.reason}"
            if exc.code in (400, 401, 403, 404, 410):
                break
        except urllib.error.URLError as exc:
            part.unlink(missing_ok=True)
            last_error = f"URLError: {exc.reason}"
        except (TimeoutError, OSError) as exc:
            part.unlink(missing_ok=True)
            last_error = f"{type(exc).__name__}: {exc}"
        except (http.client.HTTPException, UnicodeError, ValueError) as exc:
            # A malformed URL or a protocol-level error is a permanent failure for
            # this artifact. It is RECORDED and the run continues to the next
            # source: an uncaught exception here would abort an entire acquisition
            # pass because of one bad filename, which is exactly the behaviour the
            # failure-recording design exists to prevent.
            part.unlink(missing_ok=True)
            last_error = f"{type(exc).__name__}: {exc}"
            break
        if attempt < retries:
            time.sleep(backoff * attempt)

    return FetchResult(url=url, status="FAILED", path=None, error=last_error,
                       attempts=retries, elapsed_seconds=time.monotonic() - started)


def fetch_json(url: str, config: Config) -> tuple[Any | None, FetchResult]:
    """Fetch and parse JSON. Returns (data, result); data is None on any failure."""
    retries = int(config.get("acquisition", "retries", 3))
    rate = float(config.get("acquisition", "rate_limit_seconds", 1.0))
    host = urllib.parse.urlparse(url).netloc
    last_error = ""
    for attempt in range(1, retries + 1):
        try:
            _rate_limit(host, rate)
            with _open(url, config) as response:
                payload = response.read()
            return json.loads(payload.decode("utf-8", errors="replace")), FetchResult(
                url=url, status="OK", http_status=200, bytes=len(payload),
                content_type="application/json", attempts=attempt)
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code} {exc.reason}"
            if exc.code in (400, 401, 403, 404, 410):
                break
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        except (http.client.HTTPException, UnicodeError, ValueError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            break
        time.sleep(1.0 * attempt)
    return None, FetchResult(url=url, status="FAILED", error=last_error, attempts=retries)
