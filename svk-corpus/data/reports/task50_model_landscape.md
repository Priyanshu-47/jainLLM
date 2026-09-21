# Task 50: Current Model Landscape Research (2026)

**Date:** 2026-09-21

---

## 1. Research Scope

Researched current open-weight models suitable for:
- Indian languages (Hindi, Gujarati)
- Sanskrit/Prakrit terminology
- Domain adaptation
- QLoRA/SFT
- Local/self-hosted inference
- Azure GPU deployment

---

## 2. Model Candidates

### 2.1 Qwen Series

| Model | Parameters | Context | Languages | License |
|-------|-----------|---------|-----------|---------|
| Qwen2.5-0.5B | 0.5B | 32K | Multilingual | Apache 2.0 |
| Qwen2.5-1.5B | 1.5B | 32K | Multilingual | Apache 2.0 |
| Qwen2.5-3B | 3B | 32K | Multilingual | Apache 2.0 |
| Qwen2.5-7B | 7B | 32K | Multilingual | Apache 2.0 |
| Qwen2.5-14B | 14B | 32K | Multilingual | Apache 2.0 |

**Strengths:**
- Excellent multilingual support
- Strong Hindi/Gujarati capability
- Good instruction following
- Both base and instruct checkpoints available
- Active development

### 2.2 Gemma Series

| Model | Parameters | Context | Languages | License |
|-------|-----------|---------|-----------|---------|
| Gemma2-2B | 2B | 8K | Multilingual | Gemma License |
| Gemma2-9B | 9B | 8K | Multilingual | Gemma License |

**Strengths:**
- Good performance at smaller sizes
- Efficient architecture
- Google-backed

**Limitations:**
- Smaller context window
- Less Hindi/Gujarati specific training

### 2.3 Llama Series

| Model | Parameters | Context | Languages | License |
|-------|-----------|---------|-----------|---------|
| Llama3.2-1B | 1B | 128K | Multilingual | Llama License |
| Llama3.2-3B | 3B | 128K | Multilingual | Llama License |
| Llama3.1-8B | 8B | 128K | Multilingual | Llama License |

**Strengths:**
- Large context window
- Strong ecosystem
- Good instruction following

**Limitations:**
- Indian language support less extensive than Qwen

### 2.4 Mistral Series

| Model | Parameters | Context | Languages | License |
|-------|-----------|---------|-----------|---------|
| Mistral-7B | 7B | 32K | Multilingual | Apache 2.0 |

**Strengths:**
- Strong general performance
- Good reasoning

**Limitations:**
- Indian language support limited

### 2.5 Sarvam Series

| Model | Parameters | Context | Languages | License |
|-------|-----------|---------|-----------|---------|
| Sarvam-2B | 2B | 4K | Indian languages | Open |

**Strengths:**
- Specifically trained for Indian languages
- Hindi/Gujarati focus

**Limitations:**
- Smaller context
- Less mature ecosystem

---

## 3. Shortlist

| Model | Parameters | Indian Lang | Domain Adapt | QLoRA | License |
|-------|-----------|-------------|--------------|-------|---------|
| Qwen2.5-3B | 3B | STRONG | STRONG | STRONG | Apache 2.0 |
| Qwen2.5-7B | 7B | STRONG | STRONG | STRONG | Apache 2.0 |
| Llama3.2-3B | 3B | ADEQUATE | STRONG | STRONG | Llama |
| Gemma2-2B | 2B | ADEQUATE | ADEQUATE | STRONG | Gemma |
| Sarvam-2B | 2B | STRONG | LIMITED | ADEQUATE | Open |

---

## 4. Recommendation

**Primary candidate:** Qwen2.5-3B or Qwen2.5-7B

**Rationale:**
- Best Indian language support
- Both base and instruct checkpoints available
- Strong domain adaptation capability
- Apache 2.0 license
- Good QLoRA/SFT ecosystem
- Active community

---

## 5. GPU Requirements

| Model | VRAM (QLoRA) | VRAM (Full) | Recommended |
|-------|--------------|-------------|-------------|
| Qwen2.5-3B | ~6GB | ~12GB | 16GB+ |
| Qwen2.5-7B | ~12GB | ~28GB | 24GB+ |
| Llama3.2-3B | ~6GB | ~12GB | 16GB+ |

**GPU_REQUIRED = YES**
