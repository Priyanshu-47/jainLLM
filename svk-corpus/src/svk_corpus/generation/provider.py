"""Isolated Ollama provider for the experimental generation MVP (Task 89).

Design constraints:
  * Talks ONLY to a loopback Ollama endpoint. Non-loopback endpoints are
    rejected at construction time, so no paid/external AI API can ever be
    called from this component.
  * Never downloads, pulls, installs or trains anything — it only issues
    ``POST /api/generate`` against a model that is already served locally.
  * Configurable endpoint/model/timeouts via constructor or ``SVK_GEN_*``
    environment variables; no credentials anywhere.
  * Safe error taxonomy: connection failure, timeout and malformed responses
    are distinct exceptions so the answer service can report them without
    crashing.

Requires ``httpx`` (already present in the repo ``.venv``; declared in
``docs/generation_mvp.md``).  The stdlib pipeline never imports this module.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlparse

try:                              # optional: stdlib-only envs must still import
    import httpx
except ImportError:               # pragma: no cover - exercised on system python
    httpx = None  # type: ignore[assignment]

if httpx is not None:
    _TimeoutExc: type[BaseException] = httpx.TimeoutException
    _HTTPExc: type[BaseException] = httpx.HTTPError
else:                             # never raised: client cannot be built
    _TimeoutExc = type("_TimeoutExc", (Exception,), {})
    _HTTPExc = type("_HTTPExc", (Exception,), {})

DEFAULT_ENDPOINT = "http://127.0.0.1:11434"   # existing local Ollama
DEFAULT_MODEL = "qwen2.5:7b-instruct"          # verified via `ollama list`
DEFAULT_TIMEOUT_S = 300.0                      # CPU generation headroom
DEFAULT_CONNECT_TIMEOUT_S = 5.0
DEFAULT_NUM_PREDICT = 256
DEFAULT_NUM_CTX = 4096                         # prompt must never be truncated
DEFAULT_TEMPERATURE = 0.0

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "[::1]"})


class GenerationError(Exception):
    """Base class for provider failures (message safe to log)."""


class GenerationUnavailable(GenerationError):
    """Connection refused, model missing, or any non-200 Ollama response."""


class GenerationTimeout(GenerationError):
    """The local model did not answer within the configured timeout."""


class MalformedGenerationResponse(GenerationError):
    """Ollama replied with a payload we cannot use."""


@dataclass(frozen=True)
class GenerationConfig:
    endpoint: str = DEFAULT_ENDPOINT
    model: str = DEFAULT_MODEL
    timeout_s: float = DEFAULT_TIMEOUT_S
    num_predict: int = DEFAULT_NUM_PREDICT
    num_ctx: int = DEFAULT_NUM_CTX
    temperature: float = DEFAULT_TEMPERATURE


@dataclass(frozen=True)
class GenerationResult:
    text: str
    model: str
    latency_s: float
    eval_count: int | None = None
    done: bool = True


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default) or default


def config_from_env() -> GenerationConfig:
    """Build a config from ``SVK_GEN_*`` env vars (all optional)."""
    return GenerationConfig(
        endpoint=_env("SVK_GEN_ENDPOINT", DEFAULT_ENDPOINT),
        model=_env("SVK_GEN_MODEL", DEFAULT_MODEL),
        timeout_s=float(_env("SVK_GEN_TIMEOUT_S", str(DEFAULT_TIMEOUT_S))),
        num_predict=int(_env("SVK_GEN_NUM_PREDICT", str(DEFAULT_NUM_PREDICT))),
        num_ctx=int(_env("SVK_GEN_NUM_CTX", str(DEFAULT_NUM_CTX))),
        temperature=float(_env("SVK_GEN_TEMPERATURE", str(DEFAULT_TEMPERATURE))),
    )


def _require_loopback(endpoint: str) -> None:
    parsed = urlparse(endpoint)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https") or host not in LOOPBACK_HOSTS:
        raise ValueError(
            "generation provider only accepts loopback endpoints "
            f"(127.0.0.1/localhost/::1); got host {host!r}")


class OllamaProvider:
    """Minimal ``/api/generate`` client for an already-served local model."""

    def __init__(self, config: GenerationConfig | None = None, *,
                 client: Any | None = None,
                 clock: Callable[[], float] = time.perf_counter) -> None:
        self.config = config or config_from_env()
        _require_loopback(self.config.endpoint)
        self._clock = clock
        if client is None and httpx is None:
            raise GenerationUnavailable(
                "httpx is required to build an Ollama client "
                "(install into .venv; see docs/generation_mvp.md)")
        self._owns_client = client is None
        self._client = client if client is not None else httpx.Client(
            timeout=httpx.Timeout(self.config.timeout_s,
                                  connect=DEFAULT_CONNECT_TIMEOUT_S))

    # ---- introspection ----------------------------------------------------
    @property
    def endpoint(self) -> str:
        return self.config.endpoint

    @property
    def model(self) -> str:
        return self.config.model

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "OllamaProvider":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---- API ---------------------------------------------------------------
    def generate(self, *, system: str, prompt: str) -> GenerationResult:
        """One non-streaming completion. Raises on any provider failure."""
        payload = {
            "model": self.config.model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": self.config.num_predict,
                "num_ctx": self.config.num_ctx,
                "temperature": self.config.temperature,
            },
        }
        t0 = self._clock()
        try:
            resp = self._client.post(f"{self.config.endpoint}/api/generate",
                                     json=payload)
        except _TimeoutExc as exc:
            raise GenerationTimeout(
                f"ollama generate timed out after {self.config.timeout_s}s"
            ) from exc
        except _HTTPExc as exc:
            raise GenerationUnavailable(
                f"cannot reach local ollama at {self.config.endpoint}: "
                f"{type(exc).__name__}") from exc

        latency = self._clock() - t0
        if resp.status_code != 200:
            detail = (resp.text or "").strip()[:200]
            raise GenerationUnavailable(
                f"ollama responded {resp.status_code}: {detail or 'no body'}")

        try:
            data: Any = resp.json()
        except ValueError as exc:
            raise MalformedGenerationResponse("ollama returned non-JSON body") from exc
        if not isinstance(data, dict):
            raise MalformedGenerationResponse("ollama returned a non-object body")
        text = data.get("response")
        if not isinstance(text, str):
            raise MalformedGenerationResponse("ollama response has no string 'response'")
        eval_count = data.get("eval_count")
        return GenerationResult(
            text=text,
            model=str(data.get("model") or self.config.model),
            latency_s=latency,
            eval_count=eval_count if isinstance(eval_count, int) else None,
            done=bool(data.get("done", True)),
        )

    def model_status(self) -> dict[str, Any]:
        """GET /api/tags — is the configured model already present locally?"""
        try:
            resp = self._client.get(f"{self.config.endpoint}/api/tags",
                                    timeout=10.0)
            if hasattr(resp, "raise_for_status"):
                resp.raise_for_status()
            data = resp.json()
            names = [m.get("name", "") for m in data.get("models", [])]
        except Exception as exc:                 # noqa: BLE001 - health probe
            return {"reachable": False, "model_present": False,
                    "error": type(exc).__name__}
        present = any(n == self.config.model or
                      n.split(":")[0] == self.config.model.split(":")[0]
                      for n in names)
        return {"reachable": True, "model_present": present,
                "models": sorted(names)}
