# svk-corpus v0.1 — corpus statistics

Generated: 2026-09-17T14:14:48+00:00  
Pipeline: v0.1.0  
Corpus version: `svk-corpus-v0.1`

All figures below are read from the pipeline's own output files. Nothing is estimated. Where a figure is unavailable it is marked.

## 1. Volume

| Measure | Value |
| --- | --- |
| Sources in manifest | 48 |
| Sources passing the licence gate and released | 13 |
| Sources acquired (text extracted) | 13 |
| Sources excluded from release | 35 |
| Documents (one per extracted source) | 13 |
| Pages | 13 |
| RAG records (text units) | 50,325 |
| Training records (text units) | 30,361 |
| RAG characters | 4,402,832 |
| Training characters | 4,150,595 |
| RAG words | 777,117 |
| Training words | 725,085 |
| RAG tokens (sarvam-30b) | 1,604,385 |
| Training tokens (sarvam-30b) | 1,455,295 |
| On-disk size of the release directory | not recorded |

### Token counts by tokenizer

| Tokenizer | Tokens |
| --- | --- |
| gemma-3-4b-it-unsloth | rag 1,604,358 / train 1,455,273 (0.3644 tok/char on rag) |
| gemma-4-E4B-it | rag 1,604,366 / train 1,455,281 (0.3644 tok/char on rag) |
| qwen3-0.6b | rag 1,906,474 / train 1,722,572 (0.433 tok/char on rag) |
| qwen3-embed-0.6b | rag 1,906,474 / train 1,722,572 (0.433 tok/char on rag) |
| qwen3.5-4b | rag 1,808,634 / train 1,632,643 (0.4108 tok/char on rag) |
| sarvam-30b | rag 1,604,385 / train 1,455,295 (0.3644 tok/char on rag) |

Tokenizers that could not be downloaded are recorded in `tokenizer_measurements.json` under `tokenizer_fetch`, with their HTTP status. They are not silently omitted.

## 2. Language (RAG corpus)

| Language | Records |
| --- | --- |
| en | 36164 |
| unknown | 12177 |
| hi | 1984 |

## 3. Script (RAG corpus)

| Script | Records |
| --- | --- |
| Latin | 36164 |
| Devanagari | 14161 |

## 4. Text role (RAG corpus)

| Text role | Records |
| --- | --- |
| ORIGINAL | 50325 |

## 5. Sect (RAG corpus)

| Sect | Records |
| --- | --- |
| unknown | 22188 |
| STHANAKAVASI | 12177 |
| MULTI_TRADITION | 7422 |
| SVETAMBARA | 6916 |
| MULTI_TRADITION (describes Sthanakavasi) | 1622 |

## 6. Unit type (RAG corpus)

| Unit type | Records |
| --- | --- |
| paragraph | 37199 |
| section | 12292 |
| verse | 708 |
| chunk | 126 |

## 7. Source (RAG corpus)

| Source id | Records |
| --- | --- |
| SVK-1007 | 13894 |
| SVK-0007 | 8067 |
| SVK-1005 | 7023 |
| SVK-1010 | 4963 |
| SVK-1001 | 4868 |
| SVK-0037 | 4110 |
| SVK-0016 | 1984 |
| SVK-0038 | 1622 |
| SVK-1002 | 1116 |
| SVK-1009 | 1074 |
| SVK-1003 | 932 |
| SVK-1008 | 399 |
| SVK-1006 | 273 |

## 8. Licensing

| Gate decision | Sources |
| --- | --- |
| NEEDS_PERMISSION | 2 |
| NOT_ALLOWED | 1 |
| RAG_ALLOWED | 1 |
| TRAINING_ALLOWED | 15 |
| UNKNOWN | 10 |
| WITH_CONDITIONS | 19 |

Excluded sources, with the rule and reason for each: `data/release/excluded_sources.jsonl`.

## 9. Quality

| Metric | Value |
| --- | --- |
| Units assessed | 73828 |
| Units carrying quality flags | 44462 |
| Mean Unicode quality | 0.995787 |
| Mean OCR noise estimate | 0.152417 |
| Mean structural quality | 0.6 |
| Units evaluated for duplication | 73828 |
| Exact duplicates | 4821 |
| Near duplicates | 31 |
| Duplicate rate (exact+near) | 0.06572 |
| OCR: sources needing manual review | 3 |
| OCR engines available | no OCR engine is installed in this environment, so OCR was NOT performed and no OCR quality claim is made. The pipeline's OCR stage is exercised only on text the Internet Archive already OCR'd, whose quality is measured below against independent script evidence. |

### Quality flags

| Flag | Units |
| --- | --- |
| VERY_SHORT | 25091 |
| SCRIPT_CONFUSION | 18305 |
| HIGH_DIGIT_RATIO | 10319 |
| SCRIPT_MISMATCH | 4386 |
| HIGH_SYMBOL_RATIO | 2539 |
| ORPHAN_COMBINING_MARKS | 809 |
| OCR_NOISE_HIGH | 490 |
| REPEATED_CHARACTER_RUN | 68 |
| REPEATED_LINES | 30 |

## 10. CPT verdict

| Question | Answer |
| --- | --- |
| Clean training tokens | 1,455,295 |
| Measuring tokenizer | sarvam-30b |
| Project threshold | 50,000,000 |
| Ratio of threshold | 0.0291 |
| **CPT_ELIGIBLE** | **NO** |

- the 50M figure is this project's adopted heuristic, not a scientific constant; it is a floor for a domain-adaptation pass to have any chance of moving the model, not a guarantee that it will
- token count alone cannot justify CPT: duplication rate, provenance quality, language balance and script coverage all have to hold too
- a corpus dominated by one language cannot teach the others, however large it is
- below the threshold the correct move is RAG plus a small, verified SFT set, which is also cheaper and easier to audit
