"""Source-level retrieval channel (Task 13).

Problem it addresses
--------------------
Tasks 11/12 measured a structural failure: some relevant sources can NEVER be
retrieved at unit level because the query term exists only in their source
metadata (author, title, edition family) and in ZERO units of their body text
(q09: SVK-2002/2003/2004/2005 — the name "Ratnachandra" appears in no unit).
No unit-level method — BM25, reranking, or embeddings — can retrieve evidence
that does not exist in unit text.

This channel searches EXISTING manifest metadata only. It is a second,
clearly-labelled retrieval channel; it never mixes metadata into unit BM25
text and never treats a metadata hit as proof that a passage is doctrinally
relevant. A metadata match is an ORDER OF MAGNITUDE weaker signal than a
unit-text match: every source it produces is labelled
``retrieval_channel = source_metadata`` and carries the exact field/value
that matched.

Design rules (all measured-feasible, no invented weights):

*   Deterministic exact-token lookup (shared fold/tokenize pipeline from
    normalization.py — no fuzzy matching, no new aliases).
*   Field weights encode REACH only (how strongly a field identifies a
    source's subject), ordered title/author > text_name > lineage >
    descriptive; they rank SOURCE candidates, never units.
*   source_id tokens are indexed for identifier lookup but marked
    ``identifier_only=True``: they are for provenance/debug convenience and
    never count as a semantic match.
*   Edition-family expansion uses the existing ``edition_of`` /
    ``parent_source_id`` provenance: a family-level match (e.g. via
    text_name) surfaces the whole attested cluster, each member carrying its
    own match provenance.
*   Nothing is removed from the unit channel; combined output preserves
    unit BM25 results first, then appends source-derived units as a clearly
    separate tier.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from svk_corpus.retrieval.documents import RetrievalDocument
from svk_corpus.retrieval.normalization import expand_query_text, tokenize
from svk_corpus.retrieval.fusion import RetrievalResult

# Fields indexed for SEMANTIC matching, with reach weights (deterministic,
# documented; they rank source candidates only). Order = tie-break priority.
FIELD_WEIGHTS: tuple[tuple[str, float], ...] = (
    ("title", 3.0),            # the work's own name — strongest attested signal
    ("author", 3.0),           # named author/editor
    ("text_name", 2.0),        # curated canonical-work name (family-level)
    ("teacher_or_author", 2.0),
    ("lineage", 1.5),
    ("publisher", 1.0),        # often 'unknown'; harmless when so
    ("knowledge_layer", 0.5),  # coarse categories, weak but real
    ("text_category", 0.5),
    ("religious_scope", 0.5),
    ("sect", 0.5),
)
IDENTIFIER_FIELD = "source_id"   # indexed for lookup, never a semantic match


@dataclass
class SourceMatch:
    """One source-level match with its full evidence."""

    source_id: str
    matched_field: str
    matched_value: str
    matched_token: str
    weight: float
    via_family: bool = False
    family_root: str = ""
    identifier_only: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "matched_field": self.matched_field,
            "matched_value": self.matched_value,
            "matched_token": self.matched_token,
            "weight": self.weight,
            "via_family": self.via_family,
            "family_root": self.family_root,
            "identifier_only": self.identifier_only,
        }


@dataclass
class SourceDocument:
    """A source's indexed metadata (manifest projection)."""

    source_id: str
    fields: dict[str, str]
    family_root: str
    family_members: tuple[str, ...] = ()


class SourceIndex:
    """Exact-token inverted index over source metadata fields.

    Built once from the source manifest; queries share the normalization
    pipeline with the unit channel so folded variants meet identically.
    """

    def __init__(self, manifest_path: Path) -> None:
        self.sources: dict[str, SourceDocument] = {}
        # (field_name, token) -> {source_id: matched_value}
        self._postings: dict[tuple[str, str], dict[str, str]] = {}
        rows = list(csv.DictReader(open(manifest_path, encoding="utf-8", newline="")))
        parents = {r.get("source_id", ""): r.get("parent_source_id", "") for r in rows}
        roots: dict[str, str] = {}

        def root_of(sid: str) -> str:
            if sid in roots:
                return roots[sid]
            seen: set[str] = set()
            cur = sid
            while cur in parents and parents[cur] and cur not in seen:
                seen.add(cur)
                cur = parents[cur]
            roots[sid] = cur
            return cur

        for row in rows:
            sid = row.get("source_id", "")
            if not sid:
                continue
            fields = {name: (row.get(name) or "").strip()
                      for name, _ in FIELD_WEIGHTS}
            doc = SourceDocument(source_id=sid, fields=fields,
                                 family_root=root_of(sid))
            self.sources[sid] = doc
            for name, value in fields.items():
                if not value:
                    continue
                for tok in set(expand_query_text(value)):
                    if tok:
                        self._postings.setdefault((name, tok), {})[sid] = value[:200]
            # Identifier lookup uses EXACT keys only: the full lowercased id
            # and its numeric part. Tokenizing 'SVK-2002' into ['svk','2002']
            # would make 'svk' match every source — meaningless noise.
            self._postings.setdefault((IDENTIFIER_FIELD, sid.lower()), {})[sid] = sid
            digits = "".join(ch for ch in sid if ch.isdigit())
            if digits:
                self._postings.setdefault((IDENTIFIER_FIELD, digits), {})[sid] = sid
        # family membership map (attested edition clusters)
        fam: dict[str, list[str]] = {}
        for sid, doc in self.sources.items():
            fam.setdefault(doc.family_root, []).append(sid)
        for sid, doc in self.sources.items():
            doc.family_members = tuple(sorted(fam[doc.family_root]))

    def search(self, query: str, top_k: int = 10) -> list[SourceMatch]:
        """Rank sources by matched-field evidence.

        Deterministic policy (no invented scoring model):
          - a source's score is the max field weight of its semantic matches
          - ties break by: more distinct matched tokens, then more matched
            fields, then source_id (pure determinism, never authority)
        Family expansion: a semantic match also yields its family members as
        via_family matches (weight scaled by 0.5 — documented constant, used
        only to order the family tier, never to outrank direct evidence).
        """
        weight_of = {name: w for name, w in FIELD_WEIGHTS}
        tokens = expand_query_text(query)
        direct: dict[str, list[SourceMatch]] = {}
        for tok in dict.fromkeys(tokens):                 # stable dedup
            for (field_name, tok2), by_sid in self._postings.items():
                if tok2 != tok or field_name == IDENTIFIER_FIELD:
                    continue
                for sid in sorted(by_sid):                # deterministic
                    direct.setdefault(sid, []).append(SourceMatch(
                        source_id=sid, matched_field=field_name,
                        matched_value=by_sid[sid], matched_token=tok,
                        weight=weight_of.get(field_name, 0.0)))

        scored: list[tuple[tuple, SourceMatch]] = []
        for sid, matches in direct.items():
            best = max(matches, key=lambda m: (m.weight, m.matched_token))
            key = (-best.weight, -len({m.matched_token for m in matches}),
                   -len({m.matched_field for m in matches}), sid)
            scored.append((key, best))
        scored.sort(key=lambda kv: kv[0])

        out: list[SourceMatch] = []
        seen_ids: set[str] = set()
        for _, best in scored:
            out.append(best)
            seen_ids.add(best.source_id)
        # family tier: members of matched clusters, in deterministic order.
        # family_added guards against duplicates when several direct matches
        # share one edition cluster.
        family_tier: list[SourceMatch] = []
        family_added: set[str] = set()
        for _, best in list(scored):
            root = self.sources[best.source_id].family_root
            if len(self.sources[best.source_id].family_members) <= 1:
                continue
            for member in self.sources[best.source_id].family_members:
                if member in seen_ids or member in family_added:
                    continue
                family_added.add(member)
                family_tier.append(SourceMatch(
                    source_id=member,
                    matched_field=best.matched_field,
                    matched_value=f"family of {best.source_id}: {best.matched_value}",
                    matched_token=best.matched_token,
                    weight=round(best.weight * 0.5, 3),
                    via_family=True,
                    family_root=root))
        family_tier.sort(key=lambda m: (-m.weight, m.source_id))
        out.extend(family_tier)
        return out[:top_k]

    def search_identifier(self, identifier: str) -> list[SourceMatch]:
        """Exact identifier lookup (never a semantic match).

        Matches the full lowercased identifier first; falls back to the
        numeric part. General tokens (e.g. 'svk') are deliberately NOT
        looked up — they match every source and carry no information.
        """
        probe = identifier.strip().lower()
        hits: list[SourceMatch] = []
        by_sid = self._postings.get((IDENTIFIER_FIELD, probe), {})
        if not by_sid and probe.isdigit():
            by_sid = self._postings.get((IDENTIFIER_FIELD, probe), {})
        if not by_sid:
            digits = "".join(ch for ch in probe if ch.isdigit())
            if digits:
                by_sid = self._postings.get((IDENTIFIER_FIELD, digits), {})
        for sid in sorted(by_sid):
            hits.append(SourceMatch(
                source_id=sid, matched_field=IDENTIFIER_FIELD,
                matched_value=sid, matched_token=probe,
                weight=0.0, identifier_only=True))
        return hits


class SourceUnitExpander:
    """Expands source-level matches into representative units per source.

    Units are drawn from the FULL document list (not the BM25 pool): the
    whole point of this channel is sources with ZERO lexically-matching
    units, which no BM25 pool can contain. Per matched source the expander
    deterministically picks one representative unit (prefer a unit with a
    page locator, then the longest text — deterministic, no scoring).

    Honesty rules: the unit did NOT match the query — the result is labelled
    ``retrieval_channel = source_metadata``, carries the SourceMatch
    evidence, and keeps its source-level provenance. A metadata hit never
    pretends to be a passage-level match.
    """

    def __init__(self, docs: Sequence[RetrievalDocument]) -> None:
        self.by_source: dict[str, list[RetrievalDocument]] = {}
        for d in docs:
            self.by_source.setdefault(d.source_id, []).append(d)

    @staticmethod
    def _representative(units: list[RetrievalDocument]) -> RetrievalDocument:
        def key(d: RetrievalDocument) -> tuple:
            has_page = 0 if (d.locator or {}).get("page") else 1
            return (has_page, -len(d.text), d.text_id)
        return min(units, key=key)

    def expand(self, matches: Sequence[SourceMatch],
               top_k: int = 10) -> list[RetrievalResult]:
        """One representative unit per matched source, in match order."""
        out: list[RetrievalResult] = []
        seen: set[str] = set()
        for m in matches:
            if m.source_id in seen or m.identifier_only:
                continue
            seen.add(m.source_id)
            units = self.by_source.get(m.source_id)
            if not units:
                continue
            doc = self._representative(units)
            res = RetrievalResult(doc=doc, score=0.0, rank=len(out) + 1,
                                  methods={"source_metadata": 1})
            res.extra = {                          # type: ignore[attr-defined]
                "retrieval_channel": "source_metadata",
                "source_metadata_match": m.as_dict(),
                "unit_bm25_rank": None,
                "unit_bm25_score": None,
                "note": ("unit did not lexically match the query; it represents "
                         "a source matched via metadata"),
            }
            out.append(res)
            if len(out) >= top_k:
                break
        return out


def build_source_index(manifest_path: Path) -> SourceIndex:
    return SourceIndex(manifest_path)
