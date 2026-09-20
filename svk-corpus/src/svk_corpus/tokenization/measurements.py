"""Token measurement against real candidate tokenizers.

THIS IS THE OUTPUT THAT DECIDES THE MODEL QUESTION
Everything else in this milestone describes the corpus. This module answers the
only question that actually constrains model choice: how many tokens does each
candidate tokenizer charge us for the text we have?

It reports, per tokenizer, tokens/character and tokens/word, broken down by
language, script, source, sect and text role. A tokenizer that charges three
times as much per Gujarati character triples the cost of continued pretraining
and shrinks the effective context window for retrieval, and that has to be a
measured number rather than an impression.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from svk_corpus.tokenization.bpe import BPETokenizer, UnsupportedTokenizer

# Fallback candidate list, used only when configs/policy.toml declares none.
# The config is authoritative; `check_candidates_match_config` reports a drift so
# that the code and the policy cannot silently disagree about what was measured.
CANDIDATE_TOKENIZERS: tuple[tuple[str, str], ...] = (
    ("qwen3-0.6b",
     "https://huggingface.co/Qwen/Qwen3-0.6B/resolve/main/tokenizer.json"),
    ("qwen3-embed-0.6b",
     "https://huggingface.co/Qwen/Qwen3-Embedding-0.6B/resolve/main/tokenizer.json"),
    ("sarvam-30b",
     "https://huggingface.co/sarvamai/sarvam-30b/resolve/main/tokenizer.json"),
    ("gemma-3-4b-it-unsloth",
     "https://huggingface.co/unsloth/gemma-3-4b-it/resolve/main/tokenizer.json"),
)

# Which of the above is authoritative for the CPT decision. Recorded so the
# decision names its measuring instrument rather than asserting a universal
# "token". Overridden by [tokenizers].primary in policy.toml.
PRIMARY_TOKENIZER = "sarvam-30b"


def candidates_from_config(config) -> list[dict[str, str]]:
    """Read [[tokenizers.candidate]] entries, falling back to the module list."""
    raw = config.get("tokenizers", "candidate", None)
    if not raw:
        return [{"name": n, "url": u, "model": "", "role": ""}
                for n, u in CANDIDATE_TOKENIZERS]
    out: list[dict[str, str]] = []
    for entry in raw:
        if isinstance(entry, dict) and entry.get("name") and entry.get("url"):
            out.append({k: str(v) for k, v in entry.items()})
    return out


def primary_from_config(config) -> str:
    return str(config.get("tokenizers", "primary", PRIMARY_TOKENIZER))


def check_candidates_match_config(config) -> list[str]:
    """Report drift between the code's fallback list and the policy file."""
    configured = {c["name"] for c in candidates_from_config(config)}
    coded = {name for name, _ in CANDIDATE_TOKENIZERS}
    problems = []
    if not coded <= configured:
        problems.append(
            f"tokenizers in code but not in policy: {sorted(coded - configured)}"
        )
    if primary_from_config(config) not in configured:
        problems.append(
            f"primary tokenizer '{primary_from_config(config)}' is not in the "
            f"candidate list"
        )
    return problems


def fetch_tokenizers(config) -> list[dict[str, str]]:
    """Download each candidate tokenizer.json, recording every outcome."""
    from svk_corpus.acquisition.downloader import fetch

    cache = config.path("paths", "cache") / "tokenizers"
    cache.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, str]] = []
    for candidate in candidates_from_config(config):
        dest = cache / f"{candidate['name']}.tokenizer.json"
        result = fetch(candidate["url"], dest, config)
        results.append({
            "name": candidate["name"],
            "model": candidate.get("model", ""),
            "url": candidate["url"],
            "role": candidate.get("role", ""),
            "status": result.status,
            "http_status": str(result.http_status or ""),
            "bytes": str(result.bytes),
            "sha256": result.sha256,
            "error": result.error,
        })
    return results


@dataclass
class TextCounts:
    characters: int = 0
    words: int = 0
    codepoints: int = 0
    utf8_bytes: int = 0
    tokens: dict[str, int] = field(default_factory=dict)

    def add(self, other: "TextCounts") -> None:
        self.characters += other.characters
        self.words += other.words
        self.codepoints += other.codepoints
        self.utf8_bytes += other.utf8_bytes
        for key, value in other.tokens.items():
            self.tokens[key] = self.tokens.get(key, 0) + value

    def as_dict(self) -> dict[str, Any]:
        return {
            "characters": self.characters,
            "words": self.words,
            "codepoints": self.codepoints,
            "utf8_bytes": self.utf8_bytes,
            "tokens": dict(sorted(self.tokens.items())),
        }

    def ratios(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for name, count in self.tokens.items():
            out[f"{name}.tokens_per_character"] = (
                round(count / self.characters, 4) if self.characters else 0.0
            )
            out[f"{name}.tokens_per_word"] = (
                round(count / self.words, 4) if self.words else 0.0
            )
        return out


def basic_counts(text: str) -> TextCounts:
    return TextCounts(
        characters=len(text),
        words=len(text.split()),
        codepoints=len(text),
        utf8_bytes=len(text.encode("utf-8")),
    )


class TokenizerRegistry:
    """Loads the candidate tokenizers from data/cache/tokenizers/."""

    def __init__(self, cache_dir: Path,
                 candidates: Sequence[tuple[str, str]] | None = None,
                 roles: dict[str, str] | None = None,
                 primary: str = PRIMARY_TOKENIZER) -> None:
        self.cache_dir = Path(cache_dir)
        self.candidates = tuple(candidates or CANDIDATE_TOKENIZERS)
        self.roles = dict(roles or {})
        self.primary = primary
        self.tokenizers: dict[str, BPETokenizer] = {}
        self.unavailable: dict[str, str] = {}
        self.sources: dict[str, str] = {}

    @classmethod
    def from_config(cls, config) -> "TokenizerRegistry":
        entries = candidates_from_config(config)
        registry = cls(
            cache_dir=config.path("paths", "cache") / "tokenizers",
            candidates=tuple((c["name"], c["url"]) for c in entries),
            roles={c["name"]: c.get("role", "") for c in entries},
            primary=primary_from_config(config),
        )
        return registry.load_available()

    def load_available(self) -> "TokenizerRegistry":
        for name, url in self.candidates:
            path = self.cache_dir / f"{name}.tokenizer.json"
            if not path.is_file():
                self.unavailable[name] = f"not cached at {path}"
                continue
            try:
                self.tokenizers[name] = BPETokenizer.load(name, path)
                self.sources[name] = url
            except UnsupportedTokenizer as exc:
                self.unavailable[name] = str(exc)
            except Exception as exc:  # pragma: no cover - reported, not raised
                self.unavailable[name] = f"{type(exc).__name__}: {exc}"
        return self

    @property
    def names(self) -> list[str]:
        return sorted(self.tokenizers)

    @property
    def verified_names(self) -> list[str]:
        return sorted(n for n, t in self.tokenizers.items() if t.roundtrip_verified)

    def measure(self, text: str) -> TextCounts:
        counts = basic_counts(text)
        for name, tokenizer in self.tokenizers.items():
            counts.tokens[name] = len(tokenizer.encode(text))
        return counts

    def describe(self) -> list[dict[str, Any]]:
        out = []
        for name in self.names:
            info = self.tokenizers[name].describe()
            info["url"] = self.sources.get(name, "")
            info["role"] = self.roles.get(name, "")
            info["primary"] = name == self.primary
            out.append(info)
        for name, reason in sorted(self.unavailable.items()):
            out.append({"name": name, "unavailable": reason,
                        "role": self.roles.get(name, ""),
                        "url": dict(self.candidates).get(name, "")})
        return out


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
GROUPINGS = ("language", "script", "source_id", "sect", "text_role", "tradition")


def measure_units(units: Iterable[Any], registry: TokenizerRegistry) -> None:
    """Attach token counts to each unit's `quality` block, in place."""
    for unit in units:
        text = unit.normalized_text or unit.text
        counts = registry.measure(text)
        if unit.quality is None:
            unit.quality = {}
        unit.quality["counts"] = counts.as_dict()


def group_totals(units: Sequence[Any]) -> dict[str, dict[str, TextCounts]]:
    """Nested totals: {grouping: {value: TextCounts}}."""
    out: dict[str, dict[str, TextCounts]] = {name: {} for name in GROUPINGS}
    for unit in units:
        counts = _counts_from_quality(unit.quality)
        for grouping in GROUPINGS:
            value = getattr(unit, grouping, None) or "unknown"
            bucket = out[grouping].setdefault(str(value), TextCounts())
            bucket.add(counts)
    return out


def _counts_from_quality(quality: dict[str, Any] | None) -> TextCounts:
    data = (quality or {}).get("counts")
    if not isinstance(data, dict):
        return TextCounts()
    return TextCounts(
        characters=int(data.get("characters", 0)),
        words=int(data.get("words", 0)),
        codepoints=int(data.get("codepoints", 0)),
        utf8_bytes=int(data.get("utf8_bytes", 0)),
        tokens={k: int(v) for k, v in (data.get("tokens") or {}).items()},
    )


def summarise(units: Sequence[Any], registry: TokenizerRegistry) -> dict[str, Any]:
    totals = TextCounts()
    for unit in units:
        totals.add(_counts_from_quality(unit.quality))

    groups = group_totals(units)
    return {
        "units": len(units),
        "totals": totals.as_dict(),
        "totals_ratios": totals.ratios(),
        "by_group": {
            name: {
                value: {**counts.as_dict(), **counts.ratios()}
                for value, counts in sorted(buckets.items())
            }
            for name, buckets in groups.items()
        },
        "tokenizers": registry.describe(),
        "tokenizers_used_for_totals": registry.names,
        "tokenizers_roundtrip_verified": registry.verified_names,
        "primary_tokenizer": registry.primary,
    }


def cpt_eligibility(clean_training_tokens: int, threshold: int = 50_000_000) -> dict[str, Any]:
    """Answer the CPT question explicitly, with the reasoning attached.

    The threshold is the one this project adopted, not a law of nature, so the
    verdict is reported together with the ratio and the caveats.
    """
    if threshold <= 0:
        raise ValueError("threshold must be positive")
    ratio = clean_training_tokens / threshold
    if clean_training_tokens >= threshold:
        verdict = "YES"
    elif ratio >= 0.5:
        verdict = "BORDERLINE"
    else:
        verdict = "NO"
    return {
        "clean_training_tokens": clean_training_tokens,
        "project_threshold": threshold,
        "ratio_of_threshold": round(ratio, 4),
        "CPT_ELIGIBLE": verdict,
        "caveats": [
            "the 50M figure is this project's adopted heuristic, not a scientific "
            "constant; it is a floor for a domain-adaptation pass to have any "
            "chance of moving the model, not a guarantee that it will",
            "token count alone cannot justify CPT: duplication rate, provenance "
            "quality, language balance and script coverage all have to hold too",
            "a corpus dominated by one language cannot teach the others, however "
            "large it is",
            "below the threshold the correct move is RAG plus a small, verified "
            "SFT set, which is also cheaper and easier to audit",
        ],
    }


def write_measurements(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return path
