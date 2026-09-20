"""Tests for the retrieval prototype (Task 8).

Scope: BM25 ranking behaviour, metadata prefiltering, RRF determinism,
provenance preservation, and the honesty contract of the dense interface.
The corpus used here is synthetic and tiny; these tests never touch the
release files.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from svk_corpus.retrieval import (BM25Index, HashDense, HybridRetriever,
                                  RetrievalDocument, UnavailableDense,
                                  reciprocal_rank_fusion)
from svk_corpus.retrieval.fusion import RetrievalResult
from svk_corpus.retrieval.rerank import Reranker


def _doc(text_id: str, text: str, **over) -> RetrievalDocument:
    base = dict(
        text_id=text_id, source_id=f"SRC-{text_id}", title=f"Title {text_id}",
        text=text, language="en", script="Latin", sect="unknown",
        religious_scope="CONTEXTUAL_JAIN", religious_scope_confidence="MEDIUM",
        knowledge_layer="SECONDARY SCHOLARSHIP", teacher_or_author="unknown",
        lineage="none", unit_type="paragraph", section="",
        locator={"citation": f"Title {text_id} [SRC-{text_id}]", "page": 3},
        publication_year="1900", author="Someone",
    )
    base.update(over)
    return RetrievalDocument(**base)


class TestBM25(unittest.TestCase):
    def test_exact_term_ranks_first(self):
        docs = [
            _doc("a", "The Kalpa Sutra translation of the Kalpa Sutra text."),
            _doc("b", "A study of monastic conduct and ordination."),
            _doc("c", "Kalpa references in unrelated poetry."),
        ]
        index = BM25Index(docs)
        hits = index.search("Kalpa Sutra", top_k=3)
        # BM25 returns only docs sharing at least one query term: a and c, not b.
        self.assertEqual([h.doc.text_id for h in hits], ["a", "c"])
        self.assertEqual([h.rank for h in hits], [1, 2])
        self.assertGreater(hits[0].score, 0.0)

    def test_indic_token_matching(self):
        docs = [_doc("d1", "अहिंसा परमो धर्मः teaching"), _doc("d2", "plain english text")]
        index = BM25Index(docs)
        hits = index.search("अहिंसा", top_k=2)
        self.assertEqual(hits[0].doc.text_id, "d1")

    def test_allowed_restriction(self):
        docs = [_doc("x", "pratikramaṇa sutra ritual"), _doc("y", "pratikramaṇa ritual guide")]
        index = BM25Index(docs)
        hits = index.search("pratikramaṇa", top_k=2, allowed=[1])
        self.assertEqual([h.doc.text_id for h in hits], ["y"])


class TestRRF(unittest.TestCase):
    def test_fusion_prefers_items_in_both_lists(self):
        a, b, c, d = "a", "b", "c", "d"
        fused = reciprocal_rank_fusion([[a, b, c], [b, a, d]])
        order = [item for item, _, _ in fused]
        # a and b carry identical fused scores (swapped ranks), so the
        # documented first-appearance tie-break puts a first; both still beat
        # the single-list items c and d.
        self.assertEqual(order, ["a", "b", "c", "d"])

    def test_fusion_is_deterministic(self):
        lists = [["a", "b"], ["b", "a"], ["c", "a"]]
        again = reciprocal_rank_fusion([list(l) for l in lists])
        self.assertEqual([i for i, _, _ in reciprocal_rank_fusion(lists)],
                         [i for i, _, _ in again])


class TestHybridAndProvenance(unittest.TestCase):
    def _retriever(self, docs, dense=None):
        return HybridRetriever(docs, BM25Index(docs), dense=dense)

    def test_metadata_filter_restricts_results(self):
        docs = [
            _doc("svk1", "Sthanakvasi sect history", religious_scope="CORE_STHANAKAVASI",
                 sect="STHANAKAVASI"),
            _doc("gen1", "Sthanakvasi mention in general history"),
        ]
        retriever = self._retriever(docs)
        hits = retriever.search("Sthanakvasi", top_k=5,
                                where={"religious_scope": "CORE_STHANAKAVASI"})
        self.assertEqual([h.doc.source_id for h in hits], ["SRC-svk1"])

    def test_filter_to_empty_is_empty(self):
        docs = [_doc("a", "samayika practice")]
        retriever = self._retriever(docs)
        self.assertEqual(retriever.search("samayika", top_k=5,
                                          where={"sect": "NOPE"}), [])

    def test_provenance_preserved(self):
        docs = [_doc("p1", "uttaradhyayana sutra text", teacher_or_author="Muni X",
                     lineage="Test lineage")]
        retriever = self._retriever(docs)
        results = retriever.search("uttaradhyayana", top_k=1)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], RetrievalResult)
        prov = results[0].provenance()
        for key in ("source_id", "title", "citation", "locator", "religious_scope",
                    "knowledge_layer", "teacher_or_author", "lineage", "methods",
                    "fused_score", "text_id"):
            self.assertIn(key, prov)
        self.assertEqual(prov["teacher_or_author"], "Muni X")
        self.assertEqual(prov["locator"]["page"], 3)

    def test_dense_unavailable_is_lexical_only(self):
        docs = [_doc("a", "unique terminology here"), _doc("b", "other words")]
        retriever = self._retriever(docs, dense=UnavailableDense())
        self.assertEqual(UnavailableDense().search("anything"), [])
        hits = retriever.search("unique terminology", top_k=2)
        self.assertTrue(all("dense" not in r.methods for r in hits))

    def test_dense_double_fuses_and_labels_methods(self):
        docs = [
            _doc("a", "alphabet sequence alpha beta"),
            _doc("b", "alphabet sequence alpha gamma"),
            _doc("c", "completely different content"),
        ]
        retriever = self._retriever(docs, dense=HashDense(docs))
        hits = retriever.search("alphabet sequence alpha", top_k=3)
        self.assertTrue(hits)
        fused_hit = next((h for h in hits if "dense" in h.methods), None)
        self.assertIsNotNone(fused_hit)  # the dense path contributed


class TestRomanizationFoldingAndAliases(unittest.TestCase):
    """Task 9: deterministic folding + evidenced aliases.

    Contract under test: deterministic, retrieval-only (original text and
    provenance untouched), evidence-bounded (no accidental merges).
    """

    def test_fold_is_deterministic_and_idempotent(self):
        from svk_corpus.retrieval.normalization import fold_token
        pairs = {"Sthānakavāsī": "Sthanakavasi", "Tattvārtha": "Tattvartha",
                 "pratikramaṇa": "pratikramana", "śramaṇa": "shramana",
                 "Sūtrakṛtāṅga": "Sutrakritanga", "sādhvī": "sadhvi"}
        for raw, expected in pairs.items():
            once = fold_token(raw)
            self.assertEqual(once, expected)
            self.assertEqual(fold_token(once), once)  # idempotent
        # Deterministic across calls.
        self.assertEqual(fold_token("Sūtrakṛtāṅga"), fold_token("Sūtrakṛtāṅga"))

    def test_indic_tokens_pass_through_untouched(self):
        from svk_corpus.retrieval.normalization import fold_token
        for tok in ("अहिंसा", "જૈન", "उत्तराध्ययन"):
            self.assertEqual(fold_token(tok), tok)

    def test_alias_expansion_is_deterministic(self):
        from svk_corpus.retrieval.normalization import expand_token
        first = expand_token("sutrakritanga")
        self.assertEqual(first, expand_token("sutrakritanga"))
        self.assertIn("sutrakrtanga", first)
        self.assertEqual(first[0], "sutrakritanga")  # original term always first
        # Fold+alias compose: a diacritic query reaches the ASCII alias.
        self.assertIn("sutrakrtanga", expand_token("sūtrakritanga"))

    def test_sutrakritanga_vs_sutrakrtanga_meet(self):
        docs = [_doc("a", "The Sutrakrtanga begins with the ascetic's conduct."),
                _doc("b", "Unrelated monastic rules.")]
        index = BM25Index(docs)
        hits = index.search("Sutrakritanga", top_k=2)      # query-side variant
        self.assertEqual([h.doc.text_id for h in hits], ["a"])
        hits_rev = index.search("Sutrakrtanga", top_k=2)   # reverse direction
        self.assertEqual([h.doc.text_id for h in hits_rev], ["a"])

    def test_uttaradhyayana_historical_and_prakrit_forms(self):
        docs = [_doc("h", "The Utradhyayan sutra, historical romanization."),
                _doc("p", "Uttarajjhayana is the Prakrit title form."),
                _doc("o", "Nothing relevant here.")]
        index = BM25Index(docs)
        self.assertEqual([h.doc.text_id for h in index.search("Uttaradhyayana", top_k=3)],
                         ["h", "p"])
        self.assertEqual([h.doc.text_id for h in index.search("Utradhyayan", top_k=3)],
                         ["h", "p"])

    def test_spaced_honorific_query_reaches_fused_corpus_form(self):
        docs = [_doc("r", "Preface by Ratnachandraji Maharaj, lexicographer."),
                _doc("x", "A completely different entry.")]
        index = BM25Index(docs)
        hits = index.search("Ratna Chandra Ji", top_k=2)
        self.assertEqual([h.doc.text_id for h in hits], ["r"])

    def test_no_accidental_merges_from_multi_token_parts(self):
        # "ji" (a PART of the spaced variant) must never become an alias key:
        # a "ji" query must not summon Ratnachandra units, and a "chandra"
        # query must not match the fused token "Ratnachandraji".
        from svk_corpus.retrieval.normalization import expand_token
        self.assertEqual(expand_token("ji"), ("ji",))
        self.assertEqual(expand_token("chandra"), ("chandra",))
        docs = [_doc("r", "Preface by Ratnachandraji Maharaj."),
                _doc("j", "The word ji appears alone in this line.")]
        index = BM25Index(docs)
        self.assertEqual([h.doc.text_id for h in index.search("ji", top_k=2)], ["j"])
        self.assertEqual(index.search("chandra", top_k=2), [])

    def test_unrelated_terms_are_not_merged(self):
        # No stemming / fuzzy matching: near-miss tokens stay distinct.
        docs = [_doc("s", "samayika vow of equanimity"),
                _doc("t", "another entry entirely")]
        index = BM25Index(docs)
        self.assertEqual(index.search("samaya", top_k=2), [])      # prefix does not match
        self.assertEqual([h.doc.text_id for h in index.search("samayika", top_k=2)],
                         ["s"])

    def test_original_text_and_provenance_untouched(self):
        docs = [_doc("a", "The Sutrakrtanga text proper.", teacher_or_author="Muni Y",
                     lineage="Lineage Z", locator={"citation": "c", "page": 7})]
        text_before = docs[0].text
        search_before = docs[0].search_text
        index = BM25Index(docs)
        hits = index.search("Sutrakritanga", top_k=1)   # alias-driven match
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].doc.text, text_before)         # original preserved
        self.assertIn("Sutrakrtanga", hits[0].doc.text)         # corpus spelling intact
        self.assertEqual(hits[0].doc.search_text, search_before)
        self.assertEqual(hits[0].doc.teacher_or_author, "Muni Y")
        self.assertEqual(hits[0].doc.lineage, "Lineage Z")
        self.assertEqual(hits[0].doc.locator["page"], 7)

    def test_alias_config_is_evidence_bounded(self):
        from svk_corpus.retrieval import normalization
        from svk_corpus.retrieval.normalization import _ALIASES
        # The default config must be loaded and sane.
        self.assertGreater(len(_ALIASES), 0)
        for key in ("sutrakritanga", "sutrakrtanga", "uttaradhyayana",
                    "utradhyayan", "uttarajjhayana", "ratnachandra", "ratnachandraji"):
            self.assertIn(key, _ALIASES)
        # Rejected variants must NOT be keys (no accidental merges).
        for banned in ("ji", "chandra", "ratna", "sthankavasi"):
            self.assertNotIn(banned, _ALIASES)
        # Config file documents rejections explicitly.
        cfg = json.loads((Path(__file__).resolve().parents[1] / "configs"
                          / "retrieval_aliases_v1.json").read_text(encoding="utf-8"))
        self.assertTrue(cfg["rejected_variants"])
        self.assertIn("orthographic_only", cfg["policy"])


class TestGujaratiAliasesAndTokenization(unittest.TestCase):
    """Task 10: Gujarati within-script aliases + the tokenizer fix.

    Task 10 found the dominant Gujarati failure was NOT spelling variance but
    the old tokenizer dropping Indic combining marks (matras/viramas), which
    mangled all Indic tokens AND falsely merged જિન with જૈન. These tests pin
    both the fix and the two evidence-cited Gujarati alias groups.
    """

    def test_gujarati_words_tokenize_intact(self):
        from svk_corpus.retrieval.normalization import tokenize
        self.assertEqual(tokenize("જૈન"), ["જૈન"])
        self.assertEqual(tokenize("ધર્મ"), ["ધર્મ"])
        self.assertEqual(tokenize("જૈન ધર્મ"), ["જૈન", "ધર્મ"])
        # The pre-fix false merge must stay dead: જિન and જૈન are distinct.
        self.assertNotEqual(tokenize("જિન"), tokenize("જૈન"))
        # Devanagari is equally protected.
        self.assertEqual(tokenize("अहिंसा"), ["अहिंसा"])

    def test_dharm_no_virama_alias(self):
        docs = [_doc("g1", "એ ધરમ બનાવી દઈએ."),
                _doc("g2", "અન્ય કંઈ નથી.")]
        index = BM25Index(docs)
        self.assertEqual([h.doc.text_id for h in index.search("ધર્મ", top_k=2)],
                         ["g1"])   # standard query reaches no-virama doc
        self.assertEqual([h.doc.text_id for h in index.search("ધરમ", top_k=2)],
                         ["g1"])   # and the historical spelling still works

    def test_compound_spaced_bidirectional(self):
        docs = [_doc("sp", "આ જૈન ધર્મ છે."),          # spaced (attested form)
                _doc("cp", "જૈનધર્મ એક ઉત્તમ જીવન."),  # compound (attested form)
                _doc("o", "બીજું કંઈ નથી.")]
        index = BM25Index(docs)
        # Compound query reaches the spaced doc (via its attested parts) and
        # vice versa; the compound doc also matches the spaced query (phrase rule).
        self.assertEqual(set(h.doc.text_id for h in index.search("જૈનધર્મ", top_k=3)),
                         {"sp", "cp"})
        self.assertEqual(set(h.doc.text_id for h in index.search("જૈન ધર્મ", top_k=3)),
                         {"cp", "sp"})

    def test_phrase_parts_never_become_search_terms(self):
        from svk_corpus.retrieval.normalization import expand_query_text, expand_token
        # જૈન alone is a phrase DETECTOR part, not an alias key: no extras.
        self.assertEqual(expand_token("જૈન"), ("જૈન",))
        # A compound query expands to BOTH attested compound spellings PLUS
        # the group's attested constituent words (parts_as_search_terms) —
        # that is how a compound reaches spaced-form docs. Nothing else enters.
        self.assertEqual(expand_query_text("જૈનધર્મ"),
                         ["જૈનધર્મ", "જેનધરમ", "જૈન", "ધર્મ", "જેન"])
        # A bare જૈન query must not match a doc that only has ધર્મ.
        docs = [_doc("d", "ધર્મ વિશે વાત કરે છે."), _doc("j", "જૈન વિશે વાત કરે છે.")]
        index = BM25Index(docs)
        self.assertEqual([h.doc.text_id for h in index.search("જૈન", top_k=2)], ["j"])

    def test_unrelated_gujarati_terms_stay_unrelated(self):
        # જયન (inside વિજયની 'victory') must never match જૈન ('Jain') queries.
        docs = [_doc("v", "વિજય અને પુષ્કલાવતી નગરી."),
                _doc("j", "જૈન ધર્મનો ઇતિહાસ.")]
        index = BM25Index(docs)
        self.assertEqual([h.doc.text_id for h in index.search("જૈન", top_k=2)], ["j"])
        self.assertEqual([h.doc.text_id for h in index.search("વિજય", top_k=2)], ["v"])

    def test_unicode_normalization_forms_fold_identically(self):
        import unicodedata
        from svk_corpus.retrieval.normalization import expand_query_text
        nfc = unicodedata.normalize("NFC", "Sthānakavāsī")
        nfd = unicodedata.normalize("NFD", "Sthānakavāsī")
        # NFC diacritics fold via the map; NFD combining marks are dropped by
        # the tokenizer; both routes must land on the same token stream.
        self.assertEqual(expand_query_text(nfc), expand_query_text(nfd))
        self.assertEqual(expand_query_text(nfc), ["sthanakavasi"])

    def test_provenance_unchanged_on_alias_hit(self):
        docs = [_doc("g", "જૈન ધર્મનો સિદ્ધાંત.", teacher_or_author="Swami Jitmal",
                     lineage="Sthanakvasi", locator={"citation": "c", "page": 11})]
        text_before = docs[0].text
        index = BM25Index(docs)
        hits = index.search("જૈનધર્મ", top_k=1)   # alias/phrase-driven match
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].doc.text, text_before)   # original bytes intact
        self.assertIn("ધર્મનો", hits[0].doc.text)          # corpus spelling intact
        self.assertEqual(hits[0].doc.teacher_or_author, "Swami Jitmal")
        self.assertEqual(hits[0].doc.lineage, "Sthanakvasi")
        self.assertEqual(hits[0].doc.locator["page"], 11)


class TestRerankStrategies(unittest.TestCase):
    """Task 11: experimental post-BM25 reranking (tie-break + diversity).

    Contract under test: BM25 stays primary, nothing removed, original
    BM25 rank/score preserved, deterministic, existing metadata only, and
    no authority smuggled in via source_id ordering.
    """

    def _results(self, docs_and_scores):
        from svk_corpus.retrieval.fusion import RetrievalResult
        return [RetrievalResult(doc=d, score=s, rank=i + 1, methods={"bm25": i + 1})
                for i, (d, s) in enumerate(docs_and_scores)]

    def _cluster(self, n_per_source=5):
        # Simulates the q09 tie region: many units of one source, identical
        # scores and metadata, plus one unit of an alternate edition source.
        docs = [_doc(f"u{i}", f"dictionary entry {i}", source_id="SVK-0007",
                     religious_scope="CORE_STHANAKAVASI",
                     religious_scope_confidence="MEDIUM", publication_year="1927")
                for i in range(n_per_source)]
        docs.append(_doc("v0", "dictionary entry alt", source_id="SVK-0037",
                         religious_scope="CORE_STHANAKAVASI",
                         religious_scope_confidence="MEDIUM", publication_year="1923"))
        return docs

    def test_identity_strategy_returns_unchanged(self):
        docs = self._cluster()
        res = self._results([(d, 4.2) for d in docs])
        out = Reranker(strategy="bm25").rerank(res)
        self.assertEqual([r.doc.text_id for r in out], [d.text_id for d in docs])
        self.assertEqual([r.rank for r in out], [h.rank for h in res])

    def test_tiebreak_orders_by_metadata_within_exact_tie(self):
        docs = self._cluster()
        # All identical scores: the HIGH-scope-confidence source must surface.
        docs[-1].religious_scope_confidence = "HIGH"
        res = self._results([(d, 4.2) for d in docs])
        out = Reranker(strategy="tiebreak").rerank(res)
        self.assertEqual(out[0].doc.source_id, "SVK-0037")

    def test_bm25_score_gap_not_overridden(self):
        docs = self._cluster()
        docs[-1].religious_scope_confidence = "HIGH"
        res = self._results([(d, 4.2) for d in docs[:-1]] + [(docs[-1], 4.1)])
        out = Reranker(strategy="tiebreak").rerank(res)
        # 4.1 is a genuinely weaker match: metadata must NOT lift it above.
        self.assertEqual(out[0].doc.source_id, "SVK-0007")
        self.assertEqual(out[-1].doc.source_id, "SVK-0037")

    def test_bm25_rank_and_score_preserved(self):
        docs = self._cluster()
        res = self._results([(d, 4.2) for d in docs])
        docs[0].religious_scope_confidence = "HIGH"
        out = Reranker(strategy="tiebreak").rerank(res)
        by_id = {r.doc.text_id: r for r in out}
        self.assertEqual(by_id["u0"].extra.bm25_rank, 1)   # was BM25 rank 1
        self.assertEqual(by_id["u0"].score, 4.2)           # score untouched
        self.assertEqual(by_id["u3"].extra.bm25_rank, 4)   # moved, evidence kept
        self.assertIn("tiebreak", by_id["u3"].extra.strategies)

    def test_no_results_removed_by_diversify(self):
        docs = self._cluster(n_per_source=15)
        res = self._results([(d, 4.2) for d in docs])
        out = Reranker(strategy="diversify", max_per_source=3).rerank(res)
        self.assertEqual(len(out), len(res))                       # nothing dropped
        self.assertEqual({r.doc.text_id for r in out}, {d.text_id for d in docs})
        # Input list untouched.
        self.assertEqual([h.rank for h in res], list(range(1, len(docs) + 1)))

    def test_diversify_caps_single_source_monopoly(self):
        docs = self._cluster(n_per_source=9)
        res = self._results([(d, 4.2) for d in docs])
        out = Reranker(strategy="diversify", max_per_source=3).rerank(res)
        # Year tie-break surfaces the 1923 alternate first; the cap then keeps
        # the monopolising source to 3 of the first 4 slots.
        self.assertEqual(out[0].doc.source_id, "SVK-0037")
        self.assertEqual(sum(1 for r in out[:4] if r.doc.source_id == "SVK-0007"), 3)

    def test_rerank_is_deterministic(self):
        docs = self._cluster()
        res = self._results([(d, 4.2) for d in docs])
        a = Reranker(strategy="diversify").rerank(res)
        b = Reranker(strategy="diversify").rerank(res)
        self.assertEqual([r.doc.text_id for r in a], [r.doc.text_id for r in b])

    def test_missing_metadata_sorts_deterministically(self):
        docs = [_doc("m1", "entry one", source_id="SVK-X", publication_year=""),
                _doc("m2", "entry two", source_id="SVK-Y", publication_year="1930")]
        res = self._results([(d, 4.2) for d in docs])
        out = Reranker(strategy="tiebreak").rerank(res)
        self.assertEqual([r.doc.text_id for r in out], ["m2", "m1"])  # year-known first

    def test_no_sourceid_ordering_preference(self):
        # Identical metadata: stable sort must keep BM25 order, NOT reorder
        # by source_id alphabetics.
        docs = [_doc("b1", "entry", source_id="SVK-B"),
                _doc("a1", "entry", source_id="SVK-A")]
        res = self._results([(d, 4.2) for d in docs])   # SVK-B matched first
        out = Reranker(strategy="tiebreak").rerank(res)
        self.assertEqual([r.doc.source_id for r in out], ["SVK-B", "SVK-A"])

    def test_edition_cluster_root_walk(self):
        from svk_corpus.retrieval.rerank import _edition_cluster_key
        parents = {"SVK-2002": "SVK-2004", "SVK-2003": "SVK-2004", "SVK-2004": "SVK-0007",
                   "SVK-2005": "SVK-0007"}
        self.assertEqual(_edition_cluster_key("SVK-2002", parents)[0], "SVK-0007")
        self.assertEqual(_edition_cluster_key("SVK-2004", parents)[0], "SVK-0007")
        self.assertEqual(_edition_cluster_key("SVK-0007", parents)[0], "SVK-0007")
        self.assertNotEqual(_edition_cluster_key("SVK-2002", parents),
                            _edition_cluster_key("SVK-2005", parents))  # siblings distinct

    def test_manifest_join_carries_relation_and_quality(self):
        import tempfile, os
        from svk_corpus.retrieval.documents import load_source_scope
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "m.csv")
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write("source_id,title,author,publication_year,religious_scope,"
                        "religious_scope_confidence,knowledge_layer,teacher_or_author,"
                        "lineage,parent_source_id,source_quality\n")
                f.write("SVK-0007,T,A,1927,CORE_STHANAKAVASI,MEDIUM,LEXICON,Muni R,"
                        "Conference,SVK-PARENT,HIGH\n")
            scope = load_source_scope(Path(p))
            self.assertEqual(scope["SVK-0007"]["parent_source_id"], "SVK-PARENT")
            self.assertEqual(scope["SVK-0007"]["source_quality"], "HIGH")


class TestSourceChannel(unittest.TestCase):
    """Task 13: source-level metadata retrieval channel.

    Contract under test: manifest-only exact-token matching, deterministic
    ranking (no authority from source_id), family expansion, source-to-unit
    expansion that NEVER pretends the unit matched the query, and channel
    labels that keep the two retrieval paths distinguishable.
    """

    def _manifest(self):
        import os, tempfile
        td = tempfile.TemporaryDirectory()
        p = os.path.join(td.name, "m.csv")
        rows = [
            "source_id,title,author,publisher,publication_year,religious_scope,religious_scope_confidence,knowledge_layer,teacher_or_author,lineage,text_name,text_category,sect,parent_source_id,source_quality",
            'SVK-0007,Ardha Magadhi Dictionary,Muni Ratnachandraji,unknown,1927,CORE_STHANAKAVASI,MEDIUM,LEXICON,Muni Ratnachandra,Conference,Ardha Magadhi Dictionary,DICTIONARY_PRAKRIT,STHANAKAVASI,,MEDIUM',
            'SVK-2002,Illustrated Dict Gujarati,A. C. Woolner,unknown,1932,CORE_STHANAKAVASI,MEDIUM,LEXICON,A. C. Woolner,Conference,Ardha Magadhi Dictionary,DICTIONARY_PRAKRIT,STHANAKAVASI,SVK-2004,MEDIUM',
            'SVK-2004,Quadrilingual Dictionary,A. C. Woolner,unknown,1927,CORE_STHANAKAVASI,MEDIUM,LEXICON,A. C. Woolner,Conference,Ardha Magadhi Dictionary,DICTIONARY_PRAKRIT,STHANAKAVASI,SVK-0007,MEDIUM',
            'SVK-0099,Unrelated Poems,Some Poet,unknown,1901,UNKNOWN,LOW,POETRY,Some Poet,,Unrelated Poems,POETRY,,,LOW',
        ]
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(rows) + "\n")
        self.addCleanup(td.cleanup)
        return Path(p)

    def test_index_and_author_title_match(self):
        from svk_corpus.retrieval.source_channel import build_source_index
        idx = build_source_index(self._manifest())
        hits = idx.search("Ratnachandra", top_k=5)
        self.assertTrue(hits)
        self.assertEqual(hits[0].source_id, "SVK-0007")
        self.assertIn(hits[0].matched_field, ("author", "teacher_or_author"))
        # The alias pipeline folds the variant to the corpus form.
        self.assertEqual(hits[0].matched_token, "ratnachandraji")
        self.assertFalse(hits[0].identifier_only)

    def test_title_match_surfaces_family_members(self):
        from svk_corpus.retrieval.source_channel import build_source_index
        idx = build_source_index(self._manifest())
        # All three cluster members match 'Ardha Magadhi Dictionary' directly
        # via text_name/title.
        got = [h.source_id for h in idx.search("Ardha Magadhi Dictionary", top_k=10)]
        for sid in ("SVK-0007", "SVK-2002", "SVK-2004"):
            self.assertIn(sid, got)
        # The FAMILY mechanism: 'Ratnachandra' matches only SVK-0007 directly;
        # the other cluster members must surface via_family with evidence.
        hits = idx.search("Ratnachandra", top_k=10)
        family = [h for h in hits if h.via_family]
        self.assertEqual({h.source_id for h in family}, {"SVK-2002", "SVK-2004"})
        self.assertTrue(all(h.family_root == "SVK-0007" for h in family))
        self.assertIn("family of SVK-0007", family[0].matched_value)

    def test_identifier_lookup_is_not_semantic(self):
        from svk_corpus.retrieval.source_channel import build_source_index
        idx = build_source_index(self._manifest())
        hits = idx.search_identifier("SVK-2002")
        self.assertEqual(hits[0].source_id, "SVK-2002")
        self.assertTrue(hits[0].identifier_only)
        # An id query must NOT produce semantic source matches.
        self.assertEqual([h.source_id for h in idx.search("SVK-2002")], [])

    def test_no_authority_from_source_id_ordering(self):
        from svk_corpus.retrieval.source_channel import build_source_index
        idx = build_source_index(self._manifest())
        # Both SVK-0007 and SVK-2004 match 'dictionary' with identical fields;
        # family/direct ordering is deterministic but the unrelated source
        # (SVK-0099, no match) must never appear.
        got = [h.source_id for h in idx.search("dictionary", top_k=10)]
        self.assertNotIn("SVK-0099", got)
        # And between equal-weight dictionary matches, the direct-match
        # ordering is deterministic (more matched tokens/fields first, then
        # source_id purely as a deterministic last resort) — verify stability.
        again = [h.source_id for h in idx.search("dictionary", top_k=10)]
        self.assertEqual(got, again)

    def test_unrelated_query_matches_nothing(self):
        from svk_corpus.retrieval.source_channel import build_source_index
        idx = build_source_index(self._manifest())
        # No token of this query occurs in any indexed metadata field.
        self.assertEqual(idx.search("kavya mudra grantha", top_k=10), [])

    def test_expansion_labels_channel_and_preserves_provenance(self):
        from svk_corpus.retrieval.source_channel import (build_source_index,
                                                         SourceUnitExpander)
        idx = build_source_index(self._manifest())
        docs = [_doc("e1", "entry one body", source_id="SVK-0007",
                     locator={"page": 5}),
                _doc("e2", "x", source_id="SVK-0007", locator={}),
                _doc("w1", "woolner unit", source_id="SVK-2002")]
        hits = idx.search("Ratnachandra", top_k=5)
        out = SourceUnitExpander(docs).expand(hits, top_k=5)
        self.assertTrue(out)
        first = out[0]
        self.assertEqual(first.doc.source_id, "SVK-0007")
        extra = first.extra
        self.assertEqual(extra["retrieval_channel"], "source_metadata")
        self.assertEqual(extra["source_metadata_match"]["matched_token"], "ratnachandraji")
        self.assertIsNone(extra["unit_bm25_rank"])  # honestly NOT a lexical match
        # Representative picks the paged, longer unit deterministically.
        self.assertEqual(first.doc.text_id, "e1")

    def test_combined_dedups_by_unit_identity(self):
        from svk_corpus.retrieval.fusion import RetrievalResult
        from svk_corpus.retrieval.source_channel import (SourceMatch,
                                                         SourceUnitExpander)
        docs = [_doc("e1", "matched body", source_id="SVK-0007")]
        unit_tier = [RetrievalResult(doc=docs[0], score=4.0, rank=1,
                                     methods={"bm25": 1})]
        m = SourceMatch(source_id="SVK-0007", matched_field="author",
                        matched_value="Muni Ratnachandraji", matched_token="ratnachandra",
                        weight=3.0)
        expanded = SourceUnitExpander(docs).expand([m], top_k=5)
        combined_ids = [r.doc.text_id for r in unit_tier + expanded
                        if r.doc.text_id not in {x.doc.text_id for x in unit_tier}]
        self.assertEqual(combined_ids, [])   # duplicate suppressed

    def test_missing_metadata_is_tolerated(self):
        import os, tempfile
        from svk_corpus.retrieval.source_channel import build_source_index
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        p = os.path.join(td.name, "m.csv")
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write("source_id,title,author,parent_source_id\n")
            f.write("SVK-X,Some Title,,\n")            # author missing/empty
        idx = build_source_index(Path(p))
        self.assertEqual([h.source_id for h in idx.search("Some Title")], ["SVK-X"])
        self.assertEqual(idx.search("Muni"), [])       # empty author not indexed


class TestSentenceTransformerDenseFromPrebuilt(unittest.TestCase):
    """Task 17: from_prebuilt() loads a pre-saved FAISS index."""

    def test_from_prebuilt_loads_index(self):
        import faiss
        import numpy as np
        import tempfile, os
        from svk_corpus.retrieval.dense import SentenceTransformerDense

        docs = [_doc("a", "kalpa sutra text"), _doc("b", "other content")]
        dim = 8
        rng = np.random.RandomState(42)
        vecs = rng.randn(2, dim).astype(np.float32)
        faiss.normalize_L2(vecs)
        idx = faiss.IndexFlatIP(dim)
        idx.add(vecs)

        with tempfile.NamedTemporaryFile(suffix=".index", delete=False) as f:
            faiss.write_index(idx, f.name)
            index_path = f.name
        try:
            dense = SentenceTransformerDense.from_prebuilt(
                docs=docs,
                index_path=index_path,
                model_name="paraphrase-multilingual-MiniLM-L12-v2",
                query_prefix="",
            )
            self.assertEqual(dense._index.ntotal, 2)
            self.assertEqual(dense._dim, dim)
            self.assertEqual(len(dense.docs), 2)
            self.assertEqual(dense.query_prefix, "")
            self.assertEqual(dense.normalize, True)
        finally:
            os.unlink(index_path)

    def test_from_prebuilt_rejects_missing_file(self):
        from svk_corpus.retrieval.dense import SentenceTransformerDense
        docs = [_doc("a", "text")]
        with self.assertRaises(FileNotFoundError):
            SentenceTransformerDense.from_prebuilt(
                docs=docs,
                index_path="/nonexistent/path.index",
            )

    def test_from_prebuilt_stores_query_prefix(self):
        import faiss
        import numpy as np
        import tempfile, os
        from svk_corpus.retrieval.dense import SentenceTransformerDense

        docs = [_doc("a", "text")]
        dim = 8
        idx = faiss.IndexFlatIP(dim)
        vecs = np.zeros((1, dim), dtype=np.float32)
        idx.add(vecs)

        with tempfile.NamedTemporaryFile(suffix=".index", delete=False) as f:
            faiss.write_index(idx, f.name)
            index_path = f.name
        try:
            d1 = SentenceTransformerDense.from_prebuilt(
                docs=docs, index_path=index_path,
                model_name="paraphrase-multilingual-MiniLM-L12-v2",
                query_prefix="Query: ",
            )
            d2 = SentenceTransformerDense.from_prebuilt(
                docs=docs, index_path=index_path,
                model_name="paraphrase-multilingual-MiniLM-L12-v2",
                query_prefix="",
            )
            self.assertEqual(d1.query_prefix, "Query: ")
            self.assertEqual(d2.query_prefix, "")
        finally:
            os.unlink(index_path)


if __name__ == "__main__":
    unittest.main()
