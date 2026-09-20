# INGEST_REPORT.md — svk-corpus v0.1

Generated: 2026-09-17T14:14:48+00:00  
Corpus version: `svk-corpus-v0.1`  
Pipeline: v0.1.0

## Sources

| Measure | Value |
| --- | --- |
| Sources in manifest | 48 |
| Sources with acquisition configured | 13 |
| Sources successfully acquired and extracted | 13 |
| Sources with download/extraction failures | 0 |
| Sources rejected by the licence gate (never downloaded as text) | 1 |
| Sources requiring permission | 2 |
| Sources with unresolved (UNKNOWN) status | 10 |
| Sources admitted to a release product | 13 |
| Sources excluded from the release, with reasons | 35 |

### Extraction outcome per source

| Source | Status | Method | Characters | Pages | Error |
| --- | --- | --- | --- | --- | --- |
| SVK-0007 | OK | PLAIN_TEXT | 2337506 | 1 |  |
| SVK-0016 | OK | PLAIN_TEXT | 191859 | 1 |  |
| SVK-0037 | OK | PLAIN_TEXT | 1389139 | 1 |  |
| SVK-0038 | OK | PLAIN_TEXT | 215971 | 1 |  |
| SVK-1001 | OK | PLAIN_TEXT | 809932 | 1 |  |
| SVK-1002 | OK | PLAIN_TEXT | 248360 | 1 |  |
| SVK-1003 | OK | PLAIN_TEXT | 227212 | 1 |  |
| SVK-1005 | OK | PLAIN_TEXT | 1048689 | 1 |  |
| SVK-1006 | OK | PLAIN_TEXT | 90592 | 1 |  |
| SVK-1007 | OK | PLAIN_TEXT | 1012373 | 1 |  |
| SVK-1008 | OK | PLAIN_TEXT | 49272 | 1 |  |
| SVK-1009 | OK | PLAIN_TEXT | 258838 | 1 |  |
| SVK-1010 | OK | PLAIN_TEXT | 404003 | 1 |  |

## OCR

Engines: no OCR engine is installed in this environment, so OCR was NOT performed and no OCR quality claim is made. The pipeline's OCR stage is exercised only on text the Internet Archive already OCR'd, whose quality is measured below against independent script evidence.

| Measure | Value |
| --- | --- |
| Sources with an OCR report | 13 |
| Sources needing manual review | 3 |

Full per-source calibration: `data/quality/ocr_quality_report.json` and `.csv`.

## Totals

| Measure | Value |
| --- | --- |
| Documents | 13 |
| Pages | 13 |
| RAG records | 50,325 |
| Training records | 30,361 |
| Characters (RAG) | 4,402,832 |
| Characters (training) | 4,150,595 |
| Words (RAG) | 777,117 |
| Tokens (RAG, sarvam-30b) | 1,604,385 |
| Tokens (training, sarvam-30b) | 1,455,295 |

### Tokens by language

| language | Records | Characters | Words | Tokens (sarvam-30b) | tok/char |
| --- | --- | --- | --- | --- | --- |
| en | 0 | 22,986,804 | 3,963,696 | 1,325,532 | 0.0577 |
| unknown | 0 | 2,523,060 | 517,950 | 228,717 | 0.0907 |
| hi | 0 | 907,128 | 181,056 | 50,136 | 0.0553 |

### Tokens by script

| script | Records | Characters | Words | Tokens (sarvam-30b) | tok/char |
| --- | --- | --- | --- | --- | --- |
| Latin | 0 | 22,986,804 | 3,963,696 | 1,325,532 | 0.0577 |
| Devanagari | 0 | 3,430,188 | 699,006 | 278,853 | 0.0813 |

### Tokens by text role

| text_role | Records | Characters | Words | Tokens (sarvam-30b) | tok/char |
| --- | --- | --- | --- | --- | --- |
| ORIGINAL | 0 | 26,416,992 | 4,662,702 | 1,604,385 | 0.0607 |

### Tokens by sect

| sect | Records | Characters | Words | Tokens (sarvam-30b) | tok/char |
| --- | --- | --- | --- | --- | --- |
| unknown | 0 | 10,068,114 | 1,730,400 | 675,861 | 0.0671 |
| SVETAMBARA | 0 | 6,444,042 | 1,142,202 | 302,938 | 0.047 |
| MULTI_TRADITION | 0 | 6,312,936 | 1,080,270 | 344,001 | 0.0545 |
| STHANAKAVASI | 0 | 2,523,060 | 517,950 | 228,717 | 0.0907 |
| MULTI_TRADITION (describes Sthanakavasi) | 0 | 1,068,840 | 191,880 | 52,868 | 0.0495 |

## Duplication

| Measure | Value |
| --- | --- |
| Units evaluated | 73828 |
| Exact duplicates | 4821 |
| Short exact repeats kept (low signal) | 52686 |
| Near duplicates | 31 |
| Duplicate rate | 0.06572 |

Semantic dedup: **disabled**. semantic dedup is disabled for v0.1: no embedding model in the research set has credible Prakrit/Ardhamagadhi coverage, and a wrongly merged sutra is undetectable downstream. Safe only for ['English', 'Gujarati', 'Hindi'].

## Quality

| Measure | Value |
| --- | --- |
| Units assessed | 73828 |
| Units carrying flags | 44462 |
| Mean Unicode quality | 0.995787 |
| Mean OCR noise estimate | 0.152417 |

## Tokens by tokenizer (all measured, none assumed)

| Tokenizer | Tokens |
| --- | --- |
| gemma-3-4b-it-unsloth | 1,604,358 rag / 1,455,273 training |
| gemma-4-E4B-it | 1,604,366 rag / 1,455,281 training |
| qwen3-0.6b | 1,906,474 rag / 1,722,572 training |
| qwen3-embed-0.6b | 1,906,474 rag / 1,722,572 training |
| qwen3.5-4b | 1,808,634 rag / 1,632,643 training |
| sarvam-30b | 1,604,385 rag / 1,455,295 training |

## CPT conclusion

| Question | Answer |
| --- | --- |
| Clean training tokens | 1,455,295 |
| Threshold | 50,000,000 |
| Ratio | 0.0291 |
| **CPT_ELIGIBLE** | **NO** |


## Major problems

- 2 acquisition failure(s) recorded in acquisition_failures.json
- 10 source(s) have UNKNOWN licensing status, usually a missing publication year, and are therefore neither usable nor provably unusable
- 2 source(s) require permission. These are the project's largest legal blocker.
- 3 source(s) require manual OCR review before their text may be treated as even provisional scripture
- Sectarian coverage: 12,177 records are Sthanakavasi-attributed, but attribution rests on publisher imprint metadata (A.B. Sthanakvasi Jain Conference / Shastroddhar Samiti imprints), not on content-level sect marking; treat sect as provenance-based, not verified per-verse.
- Language coverage is dominated by whatever the acquired scans happen to contain; there is no bilingual alignment and no translation layer.

## Excluded sources

| Source | Gate | Rule | Reason |
| --- | --- | --- | --- |
| SVK-0001 | WITH_CONDITIONS | R20_PERMISSIVE_LICENCE_UNVERIFIED | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |
| SVK-0002 | WITH_CONDITIONS | R30_CC0_ASSERTED_PRE_1966 | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |
| SVK-0003 | WITH_CONDITIONS | R30_CC0_ASSERTED_PRE_1966 | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |
| SVK-0004 | WITH_CONDITIONS | R30_CC0_ASSERTED_PRE_1966 | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |
| SVK-0005 | WITH_CONDITIONS | R30_CC0_ASSERTED_PRE_1966 | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |
| SVK-0006 | WITH_CONDITIONS | R30_CC0_ASSERTED_PRE_1966 | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |
| SVK-0008 | WITH_CONDITIONS | R95_CHRONOLOGY_UNRESOLVED | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |
| SVK-0009 | WITH_CONDITIONS | R95_CHRONOLOGY_UNRESOLVED | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |
| SVK-0010 | WITH_CONDITIONS | R95_CHRONOLOGY_UNRESOLVED | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |
| SVK-0011 | NEEDS_PERMISSION | R90_MODERN_IN_COPYRIGHT | P10_GATE_STATE: gate state NEEDS_PERMISSION permits no release product |
| SVK-0012 | WITH_CONDITIONS | R95_CHRONOLOGY_UNRESOLVED | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |
| SVK-0013 | WITH_CONDITIONS | R95_CHRONOLOGY_UNRESOLVED | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |
| SVK-0014 | WITH_CONDITIONS | R95_CHRONOLOGY_UNRESOLVED | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |
| SVK-0015 | WITH_CONDITIONS | R95_CHRONOLOGY_UNRESOLVED | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |
| SVK-0017 | WITH_CONDITIONS | R95_CHRONOLOGY_UNRESOLVED | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |
| SVK-0018 | WITH_CONDITIONS | R95_CHRONOLOGY_UNRESOLVED | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |
| SVK-0019 | WITH_CONDITIONS | R95_CHRONOLOGY_UNRESOLVED | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |
| SVK-0020 | WITH_CONDITIONS | R95_CHRONOLOGY_UNRESOLVED | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |
| SVK-0021 | UNKNOWN | R99_INSUFFICIENT_EVIDENCE | P10_GATE_STATE: gate state UNKNOWN permits no release product |
| SVK-0022 | UNKNOWN | R99_INSUFFICIENT_EVIDENCE | P10_GATE_STATE: gate state UNKNOWN permits no release product |
| SVK-0023 | UNKNOWN | R99_INSUFFICIENT_EVIDENCE | P10_GATE_STATE: gate state UNKNOWN permits no release product |
| SVK-0024 | UNKNOWN | R99_INSUFFICIENT_EVIDENCE | P10_GATE_STATE: gate state UNKNOWN permits no release product |
| SVK-0025 | UNKNOWN | R99_INSUFFICIENT_EVIDENCE | P10_GATE_STATE: gate state UNKNOWN permits no release product |
| SVK-0026 | TRAINING_ALLOWED | R20_PERMISSIVE_LICENCE | P40_NOT_ACQUIRED: passed the gate but no artifact was acquired in this milestone (reported explicitly so that 'absent' is not read as 'rejected') |
| SVK-0027 | TRAINING_ALLOWED | R20_PERMISSIVE_LICENCE | P40_NOT_ACQUIRED: passed the gate but no artifact was acquired in this milestone (reported explicitly so that 'absent' is not read as 'rejected') |
| SVK-0028 | UNKNOWN | R99_INSUFFICIENT_EVIDENCE | P10_GATE_STATE: gate state UNKNOWN permits no release product |
| SVK-0029 | UNKNOWN | R99_INSUFFICIENT_EVIDENCE | P10_GATE_STATE: gate state UNKNOWN permits no release product |
| SVK-0030 | UNKNOWN | R99_INSUFFICIENT_EVIDENCE | P10_GATE_STATE: gate state UNKNOWN permits no release product |
| SVK-0031 | WITH_CONDITIONS | R20_PERMISSIVE_LICENCE_UNVERIFIED | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |
| SVK-0032 | RAG_ALLOWED | R40_SHAREALIKE | P30_ARTIFACT_PROVENANCE: only 3/6 artifact provenance components are present (grade 'low'), below the release minimum 'medium' |
| SVK-0033 | NOT_ALLOWED | R10_NODERIVATIVES | P10_GATE_STATE: gate state NOT_ALLOWED permits no release product |
| SVK-0034 | UNKNOWN | R99_INSUFFICIENT_EVIDENCE | P10_GATE_STATE: gate state UNKNOWN permits no release product |
| SVK-0035 | UNKNOWN | R99_INSUFFICIENT_EVIDENCE | P10_GATE_STATE: gate state UNKNOWN permits no release product |
| SVK-0036 | NEEDS_PERMISSION | R30_CC0_ASSERTED_TOO_RECENT | P10_GATE_STATE: gate state NEEDS_PERMISSION permits no release product |
| SVK-1004 | WITH_CONDITIONS | R95_CHRONOLOGY_UNRESOLVED | P10_GATE_STATE: gate state WITH_CONDITIONS permits no release product |

## Next recommended engineering action

**Do not attempt continued pretraining.** Instead, build the retrieval layer: index this release with a multilingual embedding model plus BM25 hybrid search, and measure retrieval recall on a hand-written question set. Justification: the training corpus is 1,455,295 tokens against a 50,000,000-token threshold (0.0291x), so SFT and RAG are the only technically defensible next steps, and RAG is the one that does not require scholar-verified instruction data first.
