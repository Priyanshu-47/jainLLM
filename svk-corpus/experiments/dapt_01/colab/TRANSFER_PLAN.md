# DAPT-01 ↔ Colab transfer plan (Phase 7) — DECIDED

## Chosen path: public Kaggle datasets

| Asset | Kaggle slug | Visibility | Size |
|-------|-------------|------------|------|
| domain_train | `priyanshu47/jainllm-domain-train` | **public** | 777 MB |
| checkpoint-3893 | `priyanshu47/dapt01-checkpoint-3893` | **public** | ~511 MB |
| Qwen3-8B base | HF `Qwen/Qwen3-8B-Base` | public HF | ~16 GB (Colab downloads) |

### Why not colab upload for bulk?
- 461MB single tarball → SSL EOF failure
- 40MB parts work (~6–15s each) but awkward for 777MB dataset
- Kaggle create of domain_train: **24.9s**; Colab download at ~50–160MB/s

### Colab pull (token via `--env` only; never commit)
```bash
kaggle datasets download -d priyanshu47/jainllm-domain-train -p /content/domain_train --unzip
kaggle datasets download -d priyanshu47/dapt01-checkpoint-3893 -p /content/ck_dl --unzip
```

### Not used
- Git/LFS for corpus/checkpoint blobs
- Google Drive (optional fallback if Kaggle unavailable)
- Blind `colab upload` of 723MB train.jsonl
