"""Tests for the retrieval-only FastAPI API (Task 85).

Two layers:
  * Unit tests with a mocked/injected RetrievalService (no corpus I/O).
  * Integration tests against the real release corpus + BM25 index
    (skipped when the release artifacts are absent).

The FastAPI/pydantic dependency is optional for the stdlib pipeline: every
test class is skipped when fastapi is not importable, so the established
system-python regression baseline is unchanged.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

try:
    import fastapi  # noqa: F401
    import httpx    # noqa: F401
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from svk_corpus.retrieval.service import (RetrievalMode, RetrievalPolicy,
                                          RetrievalService, SearchResponse,
                                          ServiceResult)

# ---------------------------------------------------------------------------
# Shared fixtures (mirror tests/test_retrieval_service.py conventions)
# ---------------------------------------------------------------------------

def _doc(text_id: str, text: str, **over):
    from svk_corpus.retrieval.documents import RetrievalDocument
    base = dict(
        text_id=text_id, source_id=f"SRC-{text_id}", title=f"Title {text_id}",
        text=text, language="en", script="Latin", sect="unknown",
        religious_scope="CONTEXTUAL_JAIN", religious_scope_confidence="MEDIUM",
        knowledge_layer="SECONDARY SCHOLARSHIP", teacher_or_author="unknown",
        lineage="none", unit_type="paragraph", section="",
        locator={"citation": f"Title {text_id} [SRC-{text_id}]", "page": 3},
        publication_year="1900", author="Someone",
        parent_source_id=f"PARENT-{text_id}",
    )
    base.update(over)
    return RetrievalDocument(**base)


def _corpus():
    return [
        _doc("a", "The Kalpa Sutra translation of the Kalpa Sutra text."),
        _doc("b", "A study of monastic conduct and ordination rituals."),
        _doc("c", "Kalpa references in unrelated poetry and verse."),
        _doc("d", "Samayika meditation practice among the Sthanakavasi."),
        _doc("e", "Ahimsa non-violence principle in Jain ethics."),
        _doc("f", "Terapanth sect founded by Bhagwanaji in modern era."),
    ]


def _bm25_service(docs=None, policy=None, **kw) -> RetrievalService:
    return RetrievalService(policy=policy or RetrievalPolicy(),
                            docs=docs or _corpus(), **kw)


def _client(app):
    from fastapi.testclient import TestClient
    return TestClient(app)


def _app_with_service(service, policy=None, init_errors=None):
    from svk_corpus.retrieval.api import create_app
    pol = policy if policy is not None else (
        service.policy if service is not None else RetrievalPolicy())
    return create_app(policy=pol, service=service, init_errors=init_errors)


def _release_available() -> bool:
    return ((REPO / "data" / "release" / "rag_corpus.jsonl").is_file()
            and (REPO / "manifests" / "source_manifest.csv").is_file())


# ---------------------------------------------------------------------------
# 1. Health endpoint
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_FASTAPI, "fastapi/httpx not installed (run in .venv)")
class TestHealthEndpoint(unittest.TestCase):
    def test_health_healthy_bm25(self):
        svc = _bm25_service()
        with _client(_app_with_service(svc)) as c:
            r = c.get("/health")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["mode_configured"], "bm25")
        self.assertEqual(body["mode_default"], "bm25")
        self.assertTrue(body["corpus_loaded"])
        self.assertEqual(body["n_documents"], 6)
        self.assertFalse(body["dense_available"])
        self.assertFalse(body["query_encoder_available"])
        self.assertFalse(body["bm25_fallback_active"])
        self.assertFalse(body["strict_dense"])
        self.assertEqual(body["initialization_errors"], [])

    def test_health_hybrid_without_dense_is_degraded_not_ok(self):
        """Hybrid configured but dense/encoder absent -> degraded + fallback flag,
        NEVER a false 'hybrid is available'."""
        pol = RetrievalPolicy(mode=RetrievalMode.HYBRID_RRF20,
                              fallback_on_dense_failure=True,
                              strict_dense=False)
        svc = _bm25_service(policy=pol)  # no dense, no encoder
        with _client(_app_with_service(svc, policy=pol)) as c:
            body = c.get("/health").json()
        self.assertEqual(body["status"], "degraded")
        self.assertEqual(body["mode_configured"], "hybrid_rrf20")
        self.assertFalse(body["dense_available"])
        self.assertFalse(body["query_encoder_available"])
        self.assertTrue(body["bm25_fallback_active"])

    def test_health_strict_dense_without_dense_is_error(self):
        pol = RetrievalPolicy(mode=RetrievalMode.HYBRID_RRF20, strict_dense=True)
        svc = _bm25_service(policy=pol)
        with _client(_app_with_service(svc, policy=pol)) as c:
            body = c.get("/health").json()
        self.assertEqual(body["status"], "error")
        self.assertTrue(body["strict_dense"])
        self.assertFalse(body["bm25_fallback_active"])

    def test_health_init_failure_reports_error(self):
        with _client(_app_with_service(None, init_errors=["service init failed: boom"])) as c:
            r = c.get("/health")
        body = r.json()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(body["status"], "error")
        self.assertFalse(body["corpus_loaded"])
        self.assertIn("boom", body["initialization_errors"][0])

    def test_health_exposes_no_secrets(self):
        svc = _bm25_service()
        with _client(_app_with_service(svc)) as c:
            raw = c.get("/health").text
        for forbidden in ("password", "secret", "token", "api_key",
                          "Authorization", os.path.expanduser("~")):
            self.assertNotIn(forbidden.lower(), raw.lower())


# ---------------------------------------------------------------------------
# 2. Search endpoint — valid + schema
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_FASTAPI, "fastapi/httpx not installed (run in .venv)")
class TestSearchValid(unittest.TestCase):
    def setUp(self):
        self.svc = _bm25_service()
        self.app = _app_with_service(self.svc)
        self.c = _client(self.app)
        self.c.__enter__()

    def tearDown(self):
        self.c.__exit__(None, None, None)

    def test_valid_search_schema(self):
        r = self.c.post("/search", json={"query": "Kalpa Sutra", "top_k": 3})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        for key in ("request_id", "mode_requested", "mode_used", "fallback_reason",
                    "latency_s", "top_k", "n_results", "results"):
            self.assertIn(key, body)
        self.assertEqual(body["mode_requested"], "bm25")
        self.assertEqual(body["mode_used"], "bm25")
        self.assertIsNone(body["fallback_reason"])
        self.assertEqual(body["top_k"], 3)
        self.assertEqual(body["n_results"], len(body["results"]))
        self.assertTrue(body["request_id"])

        first = body["results"][0]
        for key in ("rank", "channel", "score", "text_id", "source_id", "title",
                    "text", "parent_source_id", "locator", "religious_scope",
                    "religious_scope_confidence", "knowledge_layer",
                    "teacher_or_author", "lineage", "source_quality", "methods",
                    "unit_bm25_rank", "unit_bm25_score", "dense_rank",
                    "dense_score", "metadata_match"):
            self.assertIn(key, first)

    def test_result_provenance_fields_match_underlying_document(self):
        r = self.c.post("/search", json={"query": "Kalpa Sutra", "top_k": 1})
        first = r.json()["results"][0]
        doc = next(d for d in self.svc.docs if d.text_id == first["text_id"])
        self.assertEqual(first["source_id"], doc.source_id)
        self.assertEqual(first["title"], doc.title)
        self.assertEqual(first["text"], doc.text)
        self.assertEqual(first["parent_source_id"], doc.parent_source_id)
        self.assertEqual(first["locator"], doc.locator)
        self.assertEqual(first["religious_scope"], doc.religious_scope)
        self.assertEqual(first["knowledge_layer"], doc.knowledge_layer)
        self.assertEqual(first["teacher_or_author"], doc.teacher_or_author)
        self.assertEqual(first["lineage"], doc.lineage)
        self.assertEqual(first["source_quality"], doc.source_quality)

    def test_unit_bm25_channel_and_ranks(self):
        r = self.c.post("/search", json={"query": "Kalpa Sutra", "top_k": 3})
        for res in r.json()["results"]:
            self.assertEqual(res["channel"], "unit_bm25")
            self.assertIsNotNone(res["unit_bm25_rank"])
            self.assertIsNotNone(res["unit_bm25_score"])
            self.assertIsNone(res["metadata_match"])

    def test_default_top_k_is_policy_default(self):
        r = self.c.post("/search", json={"query": "Samayika"})
        self.assertEqual(r.json()["top_k"], 10)

    def test_x_request_id_header_echoed(self):
        r = self.c.post("/search", json={"query": "Ahimsa"},
                        headers={"X-Request-ID": "test-req-42"})
        self.assertEqual(r.json()["request_id"], "test-req-42")

    def test_no_answer_generation_fields(self):
        r = self.c.post("/search", json={"query": "Kalpa"})
        body = r.json()
        for forbidden in ("answer", "generated_text", "completion", "llm",
                          "model_output", "response_text"):
            self.assertNotIn(forbidden, body)
            for res in body["results"]:
                self.assertNotIn(forbidden, res)


# ---------------------------------------------------------------------------
# 3. Validation / error handling
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_FASTAPI, "fastapi/httpx not installed (run in .venv)")
class TestSearchValidation(unittest.TestCase):
    def setUp(self):
        self.c = _client(_app_with_service(_bm25_service()))
        self.c.__enter__()

    def tearDown(self):
        self.c.__exit__(None, None, None)

    def test_empty_query_rejected(self):
        r = self.c.post("/search", json={"query": ""})
        self.assertEqual(r.status_code, 422)

    def test_whitespace_only_query_rejected(self):
        r = self.c.post("/search", json={"query": "   \t\n  "})
        self.assertEqual(r.status_code, 422)

    def test_oversized_query_rejected(self):
        r = self.c.post("/search", json={"query": "x" * 2001})
        self.assertEqual(r.status_code, 422)

    def test_query_at_max_length_accepted(self):
        r = self.c.post("/search", json={"query": "x" * 2000, "top_k": 1})
        self.assertEqual(r.status_code, 200)

    def test_malformed_json_rejected(self):
        r = self.c.post("/search", content=b"{not json",
                        headers={"content-type": "application/json"})
        self.assertEqual(r.status_code, 422)

    def test_missing_query_rejected(self):
        r = self.c.post("/search", json={"top_k": 5})
        self.assertEqual(r.status_code, 422)

    def test_extra_field_rejected(self):
        r = self.c.post("/search", json={"query": "x", "foo": 1})
        self.assertEqual(r.status_code, 422)

    def test_top_k_zero_rejected(self):
        r = self.c.post("/search", json={"query": "Kalpa", "top_k": 0})
        self.assertEqual(r.status_code, 422)

    def test_top_k_negative_rejected(self):
        r = self.c.post("/search", json={"query": "Kalpa", "top_k": -1})
        self.assertEqual(r.status_code, 422)

    def test_top_k_too_large_rejected(self):
        r = self.c.post("/search", json={"query": "Kalpa", "top_k": 51})
        self.assertEqual(r.status_code, 422)

    def test_top_k_non_integer_rejected(self):
        r = self.c.post("/search", json={"query": "Kalpa", "top_k": "all"})
        self.assertEqual(r.status_code, 422)

    def test_no_result_query_returns_empty_list_not_error(self):
        r = self.c.post("/search", json={"query": "zzzzqqqxyzzy-no-match-9x"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["n_results"], 0)
        self.assertEqual(body["results"], [])

    def test_oversized_body_rejected_413(self):
        big = "x" * (65 * 1024)
        r = self.c.post("/search", content=json.dumps({"query": big}).encode(),
                        headers={"content-type": "application/json"})
        self.assertEqual(r.status_code, 413)


# ---------------------------------------------------------------------------
# 4. Initialization failure + fallback + strict-dense behaviour
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_FASTAPI, "fastapi/httpx not installed (run in .venv)")
class TestInitFailureAndFallback(unittest.TestCase):
    def test_search_503_when_init_failed(self):
        app = _app_with_service(None, init_errors=["service init failed: boom"])
        with _client(app) as c:
            r = c.post("/search", json={"query": "Kalpa"})
        self.assertEqual(r.status_code, 503)
        body = r.json()
        self.assertIn("initialization_errors", body)
        self.assertIn("boom", body["initialization_errors"][0])

    def test_hybrid_without_encoder_falls_back_and_reports_mode_used(self):
        pol = RetrievalPolicy(mode=RetrievalMode.HYBRID_RRF20,
                              fallback_on_dense_failure=True, strict_dense=False)
        svc = _bm25_service(policy=pol)  # no dense, no encoder
        with _client(_app_with_service(svc, policy=pol)) as c:
            r = c.post("/search", json={"query": "Kalpa Sutra", "top_k": 3})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["mode_requested"], "hybrid_rrf20")
        self.assertEqual(body["mode_used"], "bm25")
        self.assertIsNotNone(body["fallback_reason"])
        # With both dense and encoder absent, the dense-index reason is
        # reported first (service checks dense before encoder).
        self.assertTrue(
            "dense" in body["fallback_reason"].lower()
            or "encoder" in body["fallback_reason"].lower(),
            body["fallback_reason"],
        )
        # results still served via BM25
        self.assertGreater(body["n_results"], 0)
        for res in body["results"]:
            self.assertEqual(res["channel"], "unit_bm25")

    def test_hybrid_strict_dense_raises_503(self):
        pol = RetrievalPolicy(mode=RetrievalMode.HYBRID_RRF20, strict_dense=True)
        svc = _bm25_service(policy=pol)
        with _client(_app_with_service(svc, policy=pol)) as c:
            r = c.post("/search", json={"query": "Kalpa Sutra", "top_k": 3})
        # strict_dense raises DenseIndexUnavailable -> explicit 503, fail-closed
        self.assertEqual(r.status_code, 503)
        body = r.json()
        self.assertIn("strict_dense", body["detail"])
        self.assertIn("dense", body["reason"].lower())

    def test_mode_used_never_misreported(self):
        """mode_used must reflect what actually served, not what was asked."""
        pol = RetrievalPolicy(mode=RetrievalMode.HYBRID_RRF20,
                              fallback_on_dense_failure=True)
        svc = _bm25_service(policy=pol)
        with _client(_app_with_service(svc, policy=pol)) as c:
            body = c.post("/search", json={"query": "Kalpa"}).json()
        self.assertEqual(body["mode_requested"], "hybrid_rrf20")
        self.assertEqual(body["mode_used"], "bm25")
        self.assertNotEqual(body["mode_used"], body["mode_requested"])


# ---------------------------------------------------------------------------
# 5. Determinism + contract preservation
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_FASTAPI, "fastapi/httpx not installed (run in .venv)")
class TestDeterminismAndContract(unittest.TestCase):
    def test_repeated_queries_deterministic(self):
        c = _client(_app_with_service(_bm25_service()))
        with c:
            a = c.post("/search", json={"query": "Kalpa Sutra", "top_k": 5}).json()
            b = c.post("/search", json={"query": "Kalpa Sutra", "top_k": 5}).json()
        keys = ("text_id", "source_id", "rank", "channel", "score",
                "unit_bm25_rank", "unit_bm25_score")
        for ka, kb in zip(a["results"], b["results"]):
            for k in keys:
                self.assertEqual(ka[k], kb[k])

    def test_evidence_contract_validate_result_passes(self):
        from svk_corpus.retrieval.contract import (CanonicalResult,
                                                   RetrievalChannel,
                                                   validate_result)
        c = _client(_app_with_service(_bm25_service()))
        with c:
            body = c.post("/search", json={"query": "Kalpa Sutra", "top_k": 3}).json()
        for res in body["results"]:
            cr = CanonicalResult(
                result_id=res["text_id"], source_id=res["source_id"],
                text=res["text"], title=res["title"],
                parent_source_id=res["parent_source_id"],
                locator=res["locator"],
                religious_scope=res["religious_scope"],
                religious_scope_confidence=res["religious_scope_confidence"],
                knowledge_layer=res["knowledge_layer"],
                teacher_or_author=res["teacher_or_author"],
                lineage=res["lineage"], source_quality=res["source_quality"],
                retrieval_channel=RetrievalChannel(res["channel"]),
                retrieval_rank=res["rank"], retrieval_score=res["score"],
                methods=res["methods"],
                unit_bm25_rank=res["unit_bm25_rank"],
                unit_bm25_score=res["unit_bm25_score"],
            )
            self.assertEqual(validate_result(cr), [])


# ---------------------------------------------------------------------------
# 6. No generation / no model inference in the API
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_FASTAPI, "fastapi/httpx not installed (run in .venv)")
class TestRetrievalOnly(unittest.TestCase):
    def test_api_module_has_no_generation_imports(self):
        src = (REPO / "src" / "svk_corpus" / "retrieval" / "api.py").read_text()
        for forbidden in ("transformers", "torch", "peft", "ollama",
                          "openai", "AutoModel", "generate(",
                          "chat.completions", "TextStreamer"):
            self.assertNotIn(forbidden, src)

    def test_schemas_have_no_answer_field(self):
        from svk_corpus.retrieval.schemas import SearchResponseModel
        fields = set(SearchResponseModel.model_fields)
        for forbidden in ("answer", "generated_text", "completion", "llm_output"):
            self.assertNotIn(forbidden, fields)

    def test_openapi_paths_are_retrieval_only(self):
        c = _client(_app_with_service(_bm25_service()))
        with c:
            spec = c.get("/openapi.json").json()
        self.assertEqual(set(spec["paths"]), {"/health", "/search"})


# ---------------------------------------------------------------------------
# 7. Policy loading (unit, no network, no app)
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_FASTAPI, "fastapi/httpx not installed (run in .venv)")
class TestPolicyLoading(unittest.TestCase):
    def test_load_retrieval_policy_reads_bm25_default(self):
        from svk_corpus.retrieval.api import load_retrieval_policy
        pol = load_retrieval_policy(REPO)
        self.assertIs(pol.mode, RetrievalMode.BM25)
        self.assertEqual(pol.top_k, 10)
        self.assertEqual(pol.rrf_k, 20)
        self.assertFalse(pol.strict_dense)
        self.assertTrue(pol.fallback_on_dense_failure)

    def test_env_override_hybrid_is_respected(self):
        from svk_corpus.retrieval.api import load_retrieval_policy
        old = os.environ.get("SVK_RETRIEVAL_MODE")
        os.environ["SVK_RETRIEVAL_MODE"] = "hybrid_rrf20"
        try:
            pol = load_retrieval_policy(REPO)
            self.assertIs(pol.mode, RetrievalMode.HYBRID_RRF20)
        finally:
            if old is None:
                os.environ.pop("SVK_RETRIEVAL_MODE", None)
            else:
                os.environ["SVK_RETRIEVAL_MODE"] = old

    def test_env_override_typo_is_ignored(self):
        from svk_corpus.retrieval.api import load_retrieval_policy
        old = os.environ.get("SVK_RETRIEVAL_MODE")
        os.environ["SVK_RETRIEVAL_MODE"] = "hybrid_typo"
        try:
            pol = load_retrieval_policy(REPO)
            self.assertIs(pol.mode, RetrievalMode.BM25)
        finally:
            if old is None:
                os.environ.pop("SVK_RETRIEVAL_MODE", None)
            else:
                os.environ["SVK_RETRIEVAL_MODE"] = old


# ---------------------------------------------------------------------------
# 8. Integration against the real release corpus (opt-in)
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_FASTAPI, "fastapi/httpx not installed (run in .venv)")
@unittest.skipUnless(_release_available(), "release corpus/manifest absent")
class TestIntegrationReleaseCorpus(unittest.TestCase):
    """Real corpus + BM25 via RetrievalService.from_repo (no dense, no models)."""

    @classmethod
    def setUpClass(cls):
        from svk_corpus.retrieval.api import create_app, load_retrieval_policy
        cls.policy = load_retrieval_policy(REPO)
        cls.app = create_app(root=REPO, policy=cls.policy)

    def test_health_on_real_corpus(self):
        with _client(self.app) as c:
            body = c.get("/health").json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["mode_configured"], "bm25")
        self.assertGreater(body["n_documents"], 1000)
        self.assertFalse(body["dense_available"])  # not loaded for bm25 mode

    def test_search_returns_evidence_with_stable_ids(self):
        with _client(self.app) as c:
            body = c.post("/search",
                          json={"query": "Kalpa Sutra", "top_k": 5}).json()
        self.assertGreater(body["n_results"], 0)
        for res in body["results"]:
            self.assertTrue(res["text_id"])
            self.assertTrue(res["source_id"])
            self.assertTrue(res["text"])

    def test_deterministic_on_real_corpus(self):
        with _client(self.app) as c:
            a = c.post("/search", json={"query": "Samayika", "top_k": 5}).json()
            b = c.post("/search", json={"query": "Samayika", "top_k": 5}).json()
        for ra, rb in zip(a["results"], b["results"]):
            self.assertEqual(ra["text_id"], rb["text_id"])
            self.assertEqual(ra["rank"], rb["rank"])


if __name__ == "__main__":
    unittest.main()
