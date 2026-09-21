# Task 52: Existing Pipeline Audit

**Date:** 2026-09-21

---

## 1. Repository Structure Discovered

### Source Modules (src/svk_corpus/)

| Module | Purpose | Status |
|--------|---------|--------|
| acquisition/ | Internet Archive, HuggingFace acquisition | IMPLEMENTED |
| cli.py | Command-line interface | IMPLEMENTED |
| config.py | Configuration management | IMPLEMENTED |
| deduplication/ | Document deduplication | IMPLEMENTED |
| extraction/ | Text extraction from PDF/DjVu | IMPLEMENTED |
| knowledge/ | Knowledge layer metadata | IMPLEMENTED |
| licensing/ | Rights gate, license evaluation | IMPLEMENTED |
| manifests.py | Source/artifact manifest management | IMPLEMENTED |
| normalization/ | Text normalization, script detection | IMPLEMENTED |
| ocr/ | OCR pipeline | IMPLEMENTED |
| pipeline.py | Full pipeline orchestration | IMPLEMENTED |
| quality/ | Quality checks, assessment | IMPLEMENTED |
| release.py | Corpus release generation | IMPLEMENTED |
| reports.py | Report generation | IMPLEMENTED |
| retrieval/ | RAG retrieval system | IMPLEMENTED |
| schemas/ | Data schemas, validation | IMPLEMENTED |
| segmentation/ | Document segmentation | IMPLEMENTED |
| selection.py | Corpus selection (RAG/training) | IMPLEMENTED |
| tokenization/ | Token counting, measurements | IMPLEMENTED |
| training/ | SFT candidate extraction | IMPLEMENTED |

### Data Directories

| Directory | Purpose | Status |
|-----------|---------|--------|
| data/raw/ | Raw acquired sources | 8 sources (SVK-2030..2037) |
| data/segmented/ | Segmented units | EXISTS |
| data/release/ | Released corpora | EXISTS |
| data/training/ | SFT training data | EXISTS |
| data/reports/ | Reports | EXISTS |
| data/rights/ | Rights evidence | EXISTS |
| data/evaluation/ | Evaluation data | EXISTS |
| data/knowledge/ | Knowledge metadata | EXISTS |

### Manifests

| File | Purpose | Records |
|------|---------|---------|
| source_manifest.csv | All sources | 87 sources |
| license_manifest.csv | License gate states | 87 sources |
| artifact_manifest.csv | Acquired artifacts | EXISTS |
| corpus_manifest.json | Corpus statistics | EXISTS |

### Existing Tests

| Test File | Purpose |
|-----------|---------|
| test_contract.py | Contract validation |
| test_deduplication.py | Deduplication tests |
| test_knowledge_contract.py | Knowledge contract |
| test_licensing.py | Licensing tests |
| test_normalization.py | Normalization tests |
| test_retrieval.py | Retrieval tests |
| test_schema.py | Schema validation |
| test_segmentation.py | Segmentation tests |
| test_sft_candidates.py | SFT candidate tests |
| test_sft_candidates_v2.py | SFT candidate v2 tests |
| test_task26_contracts.py | Task 26 contracts |
| test_task30_audit.py | Task 30 audit |
| test_tokenization.py | Tokenization tests |
| test_training_contract.py | Training contract |

---

## 2. Current Corpus State

### Source Count
- Total sources in manifest: 87
- Released RAG corpus: 164,238 units
- Released training corpus: 97,763 units

### SFT Training Data
- SFT candidate pool: 127 candidates
- Task 51 filtered candidates: 17
- Task 51 human reviews: 18
- Task 51 APPROVED: 11
- Task 51 REVISE: 2
- Task 51 REJECT: 5

### Existing Pipeline Components
- Full ingestion pipeline: IMPLEMENTED
- Rights gate: IMPLEMENTED
- Deduplication: IMPLEMENTED
- Quality checks: IMPLEMENTED
- SFT candidate extraction: IMPLEMENTED
- RAG retrieval: IMPLEMENTED

---

## 3. Key Findings

### Already Implemented
1. **Full pipeline** from acquisition to release
2. **Rights gate** with license evaluation
3. **Deduplication** at document level
4. **Quality checks** for text assessment
5. **SFT candidate extraction** with deterministic categorization
6. **RAG retrieval** system

### What Task 52 Needs to Add
1. **Domain train/val/test split** (document-level)
2. **SFT seed dataset** from 11 APPROVED examples
3. **Qwen3-8B DAPT configuration**
4. **Training infrastructure** (QLoRA config)
5. **Evaluation framework** for Jain domain

### What NOT to Rewrite
- Existing pipeline stages
- Existing rights gate
- Existing deduplication
- Existing quality checks
- Existing manifest management

---

## 4. Recommendations

1. **Reuse existing pipeline** for new source ingestion
2. **Extend existing manifest** for domain train/val/test split
3. **Create new module** for DAPT configuration
4. **Create new module** for SFT seed dataset
5. **Preserve all existing tests**

---

## 5. Next Steps

1. Create domain train/val/test split
2. Build SFT seed dataset from 11 APPROVED
3. Create Qwen3-8B DAPT config
4. Run preflight test
5. Execute DAPT-01
