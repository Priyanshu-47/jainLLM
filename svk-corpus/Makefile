# svk-corpus — reproducible pipeline entry points
#
# This project is stdlib-only, so it runs straight from src/ with no install:
#     make.py check
#
# On systems where `python`/`python3` is not on PATH (common on Windows), pass
# the interpreter explicitly, e.g.:
#     make PYTHON="/c/Users/you/AppData/Local/Python/pythoncore-3.14-64/python.exe" all
# or simply export PYTHON once in your shell.

PYTHON ?= python3
PY     := PYTHONPATH=src $(PYTHON) -m svk_corpus
STAMP  := data/reports/.pipeline_stamp

.PHONY: help check manifest gate acquire extract normalize segment dedupe quality tokens release stats all test validate clean stamp

help:
	@echo "svk-corpus targets:"
	@echo "  make check      verify interpreter + stdlib requirements"
	@echo "  make manifest   build extended source manifest from parent manifest + curation"
	@echo "  make gate       run the deterministic licence gate -> license_manifest.csv"
	@echo "  make acquire    download eligible sources -> data/raw/<source_id>/ + artifact_manifest.csv"
	@echo "  make extract    text extraction (plain/HTML/EPUB/PDF) -> data/extracted/"
	@echo "  make normalize  Unicode normalisation + script/language detection"
	@echo "  make segment    hierarchical segmentation into citation-addressable units"
	@echo "  make dedupe     exact + near-duplicate detection"
	@echo "  make quality    quality metrics + OCR report"
	@echo "  make tokens     tokenizer measurements (per language/script/role/sect)"
	@echo "  make release    write RAG + training corpora to data/release/"
	@echo "  make stats      write data/reports/corpus_statistics.md"
	@echo "  make all        manifest gate acquire extract normalize segment dedupe quality tokens release stats"
	@echo "  make test       run the test suite"
	@echo "  make validate   schema + provenance validation of the release"
	@echo "  make clean      remove regenerable intermediate layers"

check:
	@$(PY) check

manifest:
	@$(PY) manifest

gate:
	@$(PY) gate

acquire:
	@$(PY) acquire

extract:
	@$(PY) extract

normalize:
	@$(PY) normalize

segment:
	@$(PY) segment

dedupe:
	@$(PY) dedupe

quality:
	@$(PY) quality

tokens:
	@$(PY) tokens

release:
	@$(PY) release

stats:
	@$(PY) stats

all:
	@$(PY) manifest
	@$(PY) gate
	@$(PY) acquire
	@$(PY) extract
	@$(PY) normalize
	@$(PY) segment
	@$(PY) dedupe
	@$(PY) quality
	@$(PY) tokens
	@$(PY) release
	@$(PY) stats
	@$(PY) validate

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

validate:
	@$(PY) validate

clean:
	@rm -rf data/extracted data/normalized data/deduplicated data/cache
	@echo "cleaned regenerable layers (data/raw and data/release kept)"
