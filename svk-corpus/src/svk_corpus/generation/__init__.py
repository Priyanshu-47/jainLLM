"""Experimental evidence-generation MVP (Task 89).

Isolated from the production retrieval stack: it *consumes*
``svk_corpus.retrieval`` unchanged and serves only on ``127.0.0.1:8101``.
Local Ollama model only — no downloads, no training, no external APIs.
"""

from svk_corpus.generation.answer import (AnswerResult, AnswerService,
                                          EvidenceItem, SYSTEM_PROMPT,
                                          ValidationError, build_evidence,
                                          build_prompt, extract_citations)
from svk_corpus.generation.provider import (GenerationConfig, GenerationError,
                                            GenerationTimeout,
                                            GenerationUnavailable,
                                            OllamaProvider,
                                            MalformedGenerationResponse)

__all__ = [
    "AnswerResult", "AnswerService", "EvidenceItem", "SYSTEM_PROMPT",
    "ValidationError", "build_evidence", "build_prompt", "extract_citations",
    "GenerationConfig", "GenerationError", "GenerationTimeout",
    "GenerationUnavailable", "MalformedGenerationResponse", "OllamaProvider",
]
