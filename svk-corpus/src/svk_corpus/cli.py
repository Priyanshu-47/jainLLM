"""Command line entry point.

    python -m svk_corpus <command>
    python -m svk_corpus all
"""

from __future__ import annotations

import sys

from svk_corpus.pipeline import ALL_ORDER, COMMANDS, run

USAGE = f"""svk-corpus -- licence-gated, provenance-complete corpus pipeline

usage: python -m svk_corpus <command>

commands:
  check       verify the environment and configuration
  manifest    build the extended source manifest
  gate        run the deterministic licence gate
  acquire     download eligible sources (others are quarantined)
  extract     text extraction from acquired artifacts
  normalize   Unicode normalisation + script/language evidence
  segment     hierarchical segmentation into citation-addressable units
  dedupe      exact + near duplicate detection
  quality     per-unit quality metrics + OCR calibration report
  tokens      measure the release against real candidate tokenizers
  release     write the RAG and training corpora
  stats       corpus statistics + INGEST_REPORT.md + CPT verdict
  validate    schema and gate-compliance validation of the release
  all         {", ".join(ALL_ORDER)}
"""


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    command = argv[0]
    if command not in COMMANDS and command != "all":
        print(f"unknown command: {command}\n")
        print(USAGE)
        return 2
    return run(command)


if __name__ == "__main__":
    raise SystemExit(main())
