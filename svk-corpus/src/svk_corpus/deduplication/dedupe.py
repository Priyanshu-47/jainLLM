"""Deduplication at three levels of ambition.

LEVEL 1 -- exact. sha256 of `normalized_text`. Cheap, unambiguous, always on.

LEVEL 2 -- near. MinHash over character shingles with LSH banding. Deterministic:
blake2b with a fixed salt per hash slot, so two runs over the same input produce
the same signatures and the same clusters. No random seed anywhere.

LEVEL 3 -- semantic. IMPLEMENTED AS AN INTERFACE ONLY, AND DELIBERATELY DISABLED.
See `SemanticDeduplicator` for why that is the correct call rather than a gap.

THE RULE THAT PREVENTS THIS MODULE FROM DESTROYING THE CORPUS
Deduplication runs *within* a (text_role, language) bucket and never across it.
A Hindi translation and the Prakrit original share no text but are the same
"work"; a commentary contains the mūla verbatim. Collapsing either pair would
delete exactly the material a study corpus exists to hold. Originals,
transcriptions, translations and commentaries are separate populations, and the
deduplicator is only ever allowed to see one population at a time.

THE SECOND RULE: SHORT REPETITION IS CONTENT
A 30-character refrain repeated through a hymn is not a duplicate; it is the hymn.
Near-duplicate detection therefore has a minimum length, and exact duplicates
below `min_signal_chars` are flagged and KEPT rather than dropped.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Iterable

STATUS_UNIQUE = "UNIQUE"
STATUS_EXACT = "EXACT_DUPLICATE"
STATUS_EXACT_LOW_SIGNAL = "EXACT_DUPLICATE_LOW_SIGNAL"
STATUS_NEAR = "NEAR_DUPLICATE"

# Languages whose semantics we trust an embedding model to represent. Anything
# not listed is excluded from semantic dedup on purpose.
SEMANTIC_SAFE_LANGUAGES = frozenset({"English", "Hindi", "Gujarati"})


@dataclass
class DedupDecision:
    unit_id: str
    status: str
    method: str
    canonical_unit_id: str = ""
    similarity: float = 0.0
    kept: bool = True
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "method": self.method,
            "canonical_unit_id": self.canonical_unit_id,
            "similarity": round(self.similarity, 6),
            "kept": self.kept,
            "note": self.note,
        }


class SemanticDeduplicator:  # pragma: no cover - intentionally not run in v0.1
    """Interface for semantic duplicate detection. Not enabled for v0.1.

    WHY IT IS NOT ENABLED
    Semantic dedup needs an embedding model whose vector space actually places
    Prakrit, Ardhamāgadhī, Sanskrit, Gujarati and Hindi sensibly relative to one
    another. The research phase found no publicly documented embedding model that
    gives credible Prakrit coverage, so a cosine threshold tuned in English would
    silently merge distinct Prakrit sūtras that share Sanskrit loanwords and share
    surface vocabulary. That failure is invisible after the fact: you cannot spot
    a wrongly-merged sūtra by looking at the corpus statistics.

    The one place semantic dedup is genuinely safe is the modern-language
    commentary and translation material, and there is not yet enough of it to
    justify the machinery. Hence: interface, threshold config, documented
    availability map, and a hard refusal to run in v0.1.
    """

    def __init__(self, model_name: str = "", threshold: float = 0.95) -> None:
        self.model_name = model_name
        self.threshold = threshold
        self.enabled = False

    @staticmethod
    def is_available(language: str) -> bool:
        return language in SEMANTIC_SAFE_LANGUAGES

    def explain(self) -> str:
        return (
            "semantic dedup is disabled for v0.1: no embedding model in the "
            "research set has credible Prakrit/Ardhamagadhi coverage, and a "
            "wrongly merged sutra is undetectable downstream. Safe only for "
            f"{sorted(SEMANTIC_SAFE_LANGUAGES)}."
        )

    def find_duplicates(self, units: Iterable[Any]) -> list[DedupDecision]:
        raise NotImplementedError(self.explain())


def _shingles(text: str, size: int) -> list[str]:
    if len(text) <= size:
        return [text]
    return [text[i:i + size] for i in range(0, len(text) - size + 1, size)]


class MinHasher:
    """Deterministic MinHash over character shingles.

    Determinism matters more than speed here: a reviewer must be able to
    re-derive the exact same duplicate clusters from the same release.
    """

    def __init__(self, num_hashes: int = 64, shingle_size: int = 5,
                 min_chars: int = 200, max_shingles: int = 4000) -> None:
        self.num_hashes = num_hashes
        self.shingle_size = shingle_size
        self.min_chars = min_chars
        self.max_shingles = max_shingles
        self._salts = [f"svk-minhash-{i}".encode() for i in range(num_hashes)]

    def signature(self, text: str) -> tuple[int, ...]:
        shingles = _shingles(text, self.shingle_size)
        # Cap the shingle count by deterministic stride sampling so that a huge
        # document cannot dominate runtime; the stride keeps it reproducible.
        if len(shingles) > self.max_shingles:
            stride = len(shingles) // self.max_shingles + 1
            shingles = shingles[::stride]
        sig: list[int] = []
        for salt in self._salts:
            best = None
            for shingle in shingles:
                digest = hashlib.blake2b(salt + shingle.encode("utf-8"),
                                         digest_size=8).digest()
                value = int.from_bytes(digest, "big")
                if best is None or value < best:
                    best = value
            sig.append(best if best is not None else 0)
        return tuple(sig)

    @staticmethod
    def similarity(a: tuple[int, ...], b: tuple[int, ...]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        return sum(1 for x, y in zip(a, b) if x == y) / len(a)


class Deduplicator:
    """Streaming exact + near duplicate detection over text units."""

    def __init__(self, *, near_threshold: float = 0.85, num_hashes: int = 64,
                 shingle_size: int = 5, min_signal_chars: int = 120,
                 near_min_chars: int = 200, bands: int = 16) -> None:
        self.near_threshold = near_threshold
        self.min_signal_chars = min_signal_chars
        self.near_min_chars = near_min_chars
        self.bands = bands
        self.minhasher = MinHasher(num_hashes=num_hashes, shingle_size=shingle_size,
                                   min_chars=near_min_chars)
        self._exact: dict[str, str] = {}                 # hash -> unit_id
        self._exact_raw: dict[str, str] = {}
        self._buckets: dict[tuple, list[str]] = {}       # lsh bucket -> unit_ids
        self._signatures: dict[str, tuple[int, ...]] = {}
        self._population: dict[str, tuple[str, str]] = {}  # unit_id -> (role, lang)
        self.counts: dict[str, int] = {
            STATUS_UNIQUE: 0, STATUS_EXACT: 0, STATUS_EXACT_LOW_SIGNAL: 0,
            STATUS_NEAR: 0,
        }
        self.exact_dropped_chars = 0

    # ---- keys --------------------------------------------------------------
    @staticmethod
    def _population_key(role: str, language: str) -> tuple[str, str]:
        return (role or "UNKNOWN", language or "unknown")

    def _band_keys(self, signature: tuple[int, ...], population: tuple[str, str]) -> list[tuple]:
        rows = max(1, self.minhasher.num_hashes // self.bands)
        keys = []
        for b in range(self.bands):
            chunk = signature[b * rows:(b + 1) * rows]
            if chunk:
                # Stable bucket id. Python's built-in hash() is salted per
                # process, which would make the clustering non-reproducible.
                bucket = hashlib.blake2b(
                    b"|".join(str(v).encode() for v in chunk), digest_size=8
                ).hexdigest()
                keys.append((population[0], population[1], b, bucket))
        return keys

    # ---- main --------------------------------------------------------------
    def add(self, unit_id: str, text: str, *, raw_text: str = "",
            text_role: str = "ORIGINAL", language: str = "unknown") -> DedupDecision:
        population = self._population_key(text_role, language)
        self._population[unit_id] = population

        # Population-scoped exact keys: the same string appearing as a translation
        # or as a commentary layer is NOT an exact duplicate of the original.
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        exact_key = f"{population[0]}|{population[1]}|{text_hash}"
        raw_key = (
            f"{population[0]}|{population[1]}|"
            f"{hashlib.sha256(raw_text.encode('utf-8')).hexdigest()}"
        ) if raw_text else ""

        if exact_key in self._exact or (raw_key and raw_key in self._exact_raw):
            canonical = self._exact.get(exact_key) or self._exact_raw.get(raw_key, "")
            self.counts[STATUS_EXACT] += 1
            return DedupDecision(
                unit_id=unit_id, status=STATUS_EXACT,
                method="sha256(normalized_text)",
                canonical_unit_id=canonical, similarity=1.0, kept=False,
                note="byte-identical to an earlier unit in the same (text_role, language) "
                     "population",
            )
        self._exact[exact_key] = unit_id
        if raw_key:
            self._exact_raw.setdefault(raw_key, unit_id)

        if len(text) < self.min_signal_chars:
            # Short, repeated text is expected in liturgical material. Flag, keep.
            self.counts[STATUS_EXACT_LOW_SIGNAL] += 1
            return DedupDecision(
                unit_id=unit_id, status=STATUS_EXACT_LOW_SIGNAL,
                method="length-guard", similarity=0.0, kept=True,
                note=f"shorter than {self.min_signal_chars} characters; short "
                     f"repetition is normal in liturgical text and is kept",
            )

        if len(text) >= self.near_min_chars:
            signature = self.minhasher.signature(text)
            self._signatures[unit_id] = signature
            best_id, best_similarity = "", 0.0
            for key in self._band_keys(signature, population):
                for other in self._buckets.get(key, ()):
                    similarity = self.minhasher.similarity(
                        signature, self._signatures.get(other, ())
                    )
                    if similarity > best_similarity:
                        best_id, best_similarity = other, similarity
            for key in self._band_keys(signature, population):
                self._buckets.setdefault(key, []).append(unit_id)

            if best_similarity >= self.near_threshold:
                self.counts[STATUS_NEAR] += 1
                return DedupDecision(
                    unit_id=unit_id, status=STATUS_NEAR,
                    method=f"minhash/banded(jaccard>={self.near_threshold})",
                    canonical_unit_id=best_id, similarity=best_similarity,
                    kept=False,
                    note="near-identical text in the same role/language population",
                )

        self.counts[STATUS_UNIQUE] += 1
        return DedupDecision(unit_id=unit_id, status=STATUS_UNIQUE, method="sha256+minhash",
                             kept=True)

    # ---- reporting ---------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        total = sum(self.counts.values())
        near_or_exact = self.counts[STATUS_EXACT] + self.counts[STATUS_NEAR]
        return {
            "units_evaluated": total,
            **self.counts,
            "duplicate_rate": round(near_or_exact / total, 6) if total else 0.0,
            "near_threshold": self.near_threshold,
            "num_hashes": self.minhasher.num_hashes,
            "shingle_size": self.minhasher.shingle_size,
            "min_signal_chars": self.min_signal_chars,
            "semantic": {
                "enabled": False,
                "reason": SemanticDeduplicator().explain(),
                "safe_languages": sorted(SEMANTIC_SAFE_LANGUAGES),
            },
        }

    def cluster_summary(self, limit: int = 25) -> list[dict[str, Any]]:
        """Largest duplicate groups, for human inspection."""
        groups: dict[str, list[str]] = {}
        for unit_id, signature in self._signatures.items():
            population = self._population.get(unit_id, ("", ""))
            key = f"{population[0]}|{population[1]}|{signature[:4]}"
            groups.setdefault(key, []).append(unit_id)
        biggest = sorted(groups.items(), key=lambda kv: -len(kv[1]))[:limit]
        return [{"key": k, "unit_count": len(v), "sample_units": v[:5]}
                for k, v in biggest if len(v) > 1]
