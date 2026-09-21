# Task 51: Current Model Landscape (September 2026)

**Date:** 2026-09-21

---

## 1. Research Summary

Fresh web research conducted September 2026 using authoritative sources.

---

## 2. Model Candidates

### 2.1 Qwen Series (Current)

| Model | Parameters | Active | Context | License | Release |
|-------|-----------|--------|---------|---------|---------|
| Qwen3.5-0.8B | 0.8B | 0.8B | 262K | Apache 2.0 | 2026-03-02 |
| Qwen3.5-2B | 2B | 2B | 262K | Apache 2.0 | 2026-03-02 |
| Qwen3.5-4B | 4B | 4B | 262K | Apache 2.0 | 2026-03-02 |
| Qwen3.5-9B | 9B | 9B | 262K | Apache 2.0 | 2026-03-02 |
| Qwen3.5-27B | 27B | 27B | 262K | Apache 2.0 | 2026-02-24 |
| Qwen3.5-35B-A3B | 35B | 3B | 262K | Apache 2.0 | 2026-02-24 |
| Qwen3.5-122B-A10B | 122B | 10B | 262K | Apache 2.0 | 2026-02-24 |
| Qwen3.5-397B-A17B | 397B | 17B | 262K | Apache 2.0 | 2026-02-16 |
| Qwen3.6-35B-A3B | 35B | 3B | 262K | Apache 2.0 | 2026-04-16 |
| Qwen3.6-27B | 27B | 27B | 262K | Apache 2.0 | 2026-04-22 |
| Qwen3.8-27B | 27B | 27B | 262K | Apache 2.0 | 2026-08-14 |
| Qwen3.8-2.4T-A95B | 2.4T | 95B | 262K | Custom | 2026-08-12 |

**Key features:**
- Native multimodal (text, image, video)
- Gated DeltaNet hybrid attention
- Multi-token prediction
- 201 language vocabulary
- Strong Indian language support

### 2.2 Gemma Series (Current)

| Model | Parameters | Active | Context | License | Release |
|-------|-----------|--------|---------|---------|---------|
| Gemma 4 E2B | 2.3B eff | 2.3B | 128K | Apache 2.0 | 2026-04-02 |
| Gemma 4 E4B | 4.5B eff | 4.5B | 128K | Apache 2.0 | 2026-04-02 |
| Gemma 4 12B | 11.95B | 11.95B | 256K | Apache 2.0 | 2026-04-02 |
| Gemma 4 26B-A4B | 26B | 3.8B | 256K | Apache 2.0 | 2026-04-02 |
| Gemma 4 31B | 31B | 31B | 256K | Apache 2.0 | 2026-04-02 |

**Key features:**
- Native multimodal (text, image, audio on E2B/E4B/12B)
- 140+ language support
- Thinking mode
- QAT quantized variants available

### 2.3 Sarvam Series (Current)

| Model | Parameters | Active | Context | License | Release |
|-------|-----------|--------|---------|---------|---------|
| Sarvam-30B | 30B | 2.4B | 64K | Apache 2.0 | 2026-03-06 |
| Sarvam-105B | 105B | - | 128K | Apache 2.0 | 2026-03-06 |

**Key features:**
- Trained from scratch on Indian data
- 22 Indian language support
- Custom tokenizer for Indic scripts
- Trained on 16T tokens (30B)
- IndiaAI Mission compute

### 2.4 Llama Series (Current)

| Model | Parameters | Active | Context | License | Release |
|-------|-----------|--------|---------|---------|---------|
| Llama 4 Scout | 109B | 17B | 10M | Custom | 2025-04-05 |
| Llama 4 Maverick | 400B | 17B | 1M | Custom | 2025-04-05 |

**Key features:**
- MoE architecture
- Native multimodal
- Hindi supported
- Custom commercial license

### 2.5 Mistral Series (Current)

| Model | Parameters | Active | Context | License | Release |
|-------|-----------|--------|---------|---------|---------|
| Mistral Small 4 | 119B | 6.5B | 256K | Apache 2.0 | 2026-03-16 |

**Key features:**
- Unified instruct/reasoning/coding
- Configurable reasoning effort
- Vision support
- Apache 2.0

---

## 3. Shortlist

| Model | Parameters | Indian Lang | Domain Adapt | QLoRA | License |
|-------|-----------|-------------|--------------|-------|---------|
| Qwen3.5-4B | 4B | STRONG | STRONG | STRONG | Apache 2.0 |
| Qwen3.5-9B | 9B | STRONG | STRONG | STRONG | Apache 2.0 |
| Qwen3.8-27B | 27B | STRONG | STRONG | ADEQUATE | Apache 2.0 |
| Sarvam-30B | 30B | STRONG | ADEQUATE | ADEQUATE | Apache 2.0 |
| Gemma 4 12B | 12B | ADEQUATE | STRONG | ADEQUATE | Apache 2.0 |
| Gemma 4 E4B | 4.5B | ADEQUATE | ADEQUATE | STRONG | Apache 2.0 |

---

## 4. Base vs Instruct

| Model | Base Available | Instruct Available | Domain Adapt | SFT |
|-------|---------------|-------------------|--------------|-----|
| Qwen3.5-4B | YES | YES | BASE | INSTRUCT |
| Qwen3.5-9B | YES | YES | BASE | INSTRUCT |
| Qwen3.8-27B | YES | YES | BASE | INSTRUCT |
| Sarvam-30B | YES | YES | BASE | INSTRUCT |
| Gemma 4 12B | YES | YES | BASE | INSTRUCT |
| Gemma 4 E4B | YES | YES | BASE | INSTRUCT |

**Recommendation:**
- Domain adaptation: Use BASE checkpoint
- SFT: Use INSTRUCT checkpoint

---

## 5. Training Strategy

| Option | Description | Feasibility |
|--------|-------------|-------------|
| OPTION A | Base → SFT → RAG | FEASIBLE |
| OPTION B | Base → DA → SFT → RAG | FEASIBLE |
| OPTION C | Base → LoRA DA → SFT → RAG | FEASIBLE |
| OPTION D | Base → CPT → SFT → RAG | COMPLEX |

**First experiment:** OPTION A or OPTION C

---

## 6. GPU Requirements

| Model | VRAM (QLoRA) | VRAM (Full) | Recommended |
|-------|--------------|-------------|-------------|
| Qwen3.5-4B | ~3GB | ~8GB | 16GB+ |
| Qwen3.5-9B | ~6GB | ~18GB | 24GB+ |
| Qwen3.8-27B | ~14GB | ~54GB | 48GB+ |
| Sarvam-30B | ~6GB | ~60GB | 48GB+ |
| Gemma 4 12B | ~6GB | ~24GB | 24GB+ |

**GPU_REQUIRED = YES**
