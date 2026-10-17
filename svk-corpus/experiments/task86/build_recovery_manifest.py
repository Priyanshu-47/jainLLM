#!/usr/bin/env python3
"""TASK 86 — build recovery manifest + artifact inventory.

Computes size + SHA-256 for every critical artifact and emits:

  docs/recovery/RECOVERY_MANIFEST.json   (machine-readable)
  docs/recovery/ARTIFACT_INVENTORY.md    (human-readable table)

Run from repo root:  python3 experiments/task86/build_recovery_manifest.py

Never reads or emits secret values (~/.kaggle/* is listed by name only).
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]          # .../svk-corpus
WORKSPACE = REPO.parent                              # .../jainLLM (git root)
OUT_JSON = REPO / "docs" / "recovery" / "RECOVERY_MANIFEST.json"
OUT_MD = REPO / "docs" / "recovery" / "ARTIFACT_INVENTORY.md"
ADAPTER_DIR = Path("/tmp/opencode/task75")

# classification vocabulary (Task 86)
SAFE_IN_GIT = "SAFE_IN_GIT"
LOCAL_ONLY = "LOCAL_ONLY"
REPRODUCIBLE = "REPRODUCIBLE"
EXTERNAL = "EXTERNAL_DEPENDENCY"
MISSING = "MISSING"
UNKNOWN = "UNKNOWN"


def sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def git(*args: str) -> str:
    p = subprocess.run(["git", *args], cwd=WORKSPACE, capture_output=True,
                       text=True, timeout=60)
    return p.stdout.strip()


def entry(rel: str, base: Path, classification: str, purpose: str,
          sensitivity: str, recovery: str, compute_hash: bool = True) -> dict:
    p = base / rel if not Path(rel).is_absolute() else Path(rel)
    if not p.exists():
        return {"path": rel, "exists": False, "classification": MISSING,
                "purpose": purpose, "sensitivity": sensitivity,
                "recovery_method": recovery}
    size = p.stat().st_size if p.is_file() else None
    if p.is_dir() and compute_hash:
        size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    sha = sha256_file(p) if (p.is_file() and compute_hash) else None
    return {"path": rel, "exists": True, "size_bytes": size,
            "sha256": sha, "classification": classification,
            "purpose": purpose, "sensitivity": sensitivity,
            "recovery_method": recovery}


def tracked(rel: str) -> bool:
    out = git("ls-files", "--error-unmatch", rel)
    return bool(out)


def main() -> int:
    t0 = time.time()
    R = REPO

    # ---- git snapshot -----------------------------------------------------
    status_lines = git("status", "--short").splitlines()
    tracked_mods = [ln for ln in status_lines if not ln.startswith("??")]
    untracked = [ln for ln in status_lines if ln.startswith("??")]
    commit = git("rev-parse", "HEAD")
    branch = git("branch", "--show-current")
    remote = git("remote", "get-url", "origin")
    # sanitise: hostname + path only, never credentials
    remote_sanitised = remote.split("@")[-1] if "@" in remote else remote

    entries: list[dict] = []

    # 1. Git-tracked tree (whole workspace)
    entries.append({
        "path": "(git-tracked tree, 428 files)",
        "exists": True,
        "size_bytes": None,
        "sha256": None,
        "classification": SAFE_IN_GIT,
        "purpose": "source pipeline, frozen benchmark, manifests, 115 historical reports, core docs",
        "sensitivity": "none",
        "recovery_method": "git clone github.com/Priyanshu-47/jainLLM (push status: LOCAL ONLY until pushed)",
    })

    # 2. Uncommitted tracked modification
    entries.append({
        "path": "configs/policy.toml",
        "exists": True,
        "size_bytes": (R / "configs" / "policy.toml").stat().st_size,
        "sha256": sha256_file(R / "configs" / "policy.toml"),
        "classification": LOCAL_ONLY,
        "purpose": "[retrieval] section added by Task 76 (+27 lines); production default mode=bm25",
        "sensitivity": "none",
        "recovery_method": "recovery archive; content also reproduced in Task-76/84 docs and git diff",
    })

    # 3. Untracked retrieval-critical source (Task 76/85 deliverables)
    for rel, purpose in [
        ("src/svk_corpus/retrieval/service.py", "production RetrievalService (Task 76; untracked!)"),
        ("src/svk_corpus/retrieval/api.py", "retrieval-only FastAPI app (Task 85)"),
        ("src/svk_corpus/retrieval/schemas.py", "pydantic request/response schemas (Task 85)"),
        ("tests/test_retrieval_service.py", "41 retrieval-service regression tests (Task 76)"),
        ("tests/test_retrieval_api.py", "39 API tests (Task 85)"),
        ("docs/retrieval_api.md", "API usage documentation (Task 85)"),
    ]:
        entries.append(entry(rel, R, LOCAL_ONLY, purpose, "none",
                             "recovery archive (untracked — NOT in git clone)"))

    # 4. Frozen evaluation artifacts (tracked, verified)
    for rel, purpose in [
        ("data/evaluation/dapt01_eval_cases.jsonl", "FROZEN 47-case benchmark (sha 06625f72...)"),
        ("data/evaluation/dapt01_base_results.jsonl", "frozen Task-60 base arm results"),
        ("data/evaluation/dapt01_dapt_results.jsonl", "frozen Task-60 DAPT arm results"),
    ]:
        entries.append(entry(rel, R, SAFE_IN_GIT, purpose, "none",
                             "git clone + hash verification"))

    # 5. Corpus + manifest
    entries.append(entry("data/release/rag_corpus.jsonl", R, REPRODUCIBLE,
                         "164,238-unit RAG corpus served by the API (gitignored, 472M)",
                         "none", "recovery archive; or rebuild via make all (network+compute)"))
    entries.append(entry("data/release/training_corpus.jsonl", R, REPRODUCIBLE,
                         "training-release corpus (gitignored, 304M)",
                         "none", "recovery archive; or rebuild via make all"))
    entries.append(entry("manifests/source_manifest.csv", R, SAFE_IN_GIT,
                         "source registry / provenance + rights metadata",
                         "none", "git clone"))
    entries.append(entry("data/raw", R, LOCAL_ONLY,
                         "acquired raw sources needed for offline rebuild (untracked, 32M)",
                         "none", "recovery archive"))

    # 6. Dense index + experiments (untracked)
    entries.append(entry("experiments/task74/dense_index/corpus_emb.f16.npy", R, LOCAL_ONLY,
                         "BGE-M3 dense index (rev 5617a9f..., untracked, 321M)",
                         "none", "recovery archive; or re-embed with BGE-M3 (HF download + CPU compute)"))
    entries.append(entry("experiments/task74/dense_index/index_meta.json", R, LOCAL_ONLY,
                         "dense index metadata + alignment hashes",
                         "none", "recovery archive"))
    entries.append({
        "path": "experiments/task69-85/ + experiments/sft_01/ + sft_02/ + sft_curation/ + dapt_01/",
        "exists": True,
        "size_bytes": None,
        "sha256": None,
        "classification": LOCAL_ONLY,
        "purpose": "experiment scripts, scorers, evidence builders, SFT checkpoints (91 files, ~680M total)",
        "sensitivity": "none",
        "recovery_method": "recovery archive (entirely untracked)",
    })

    # 7. Evaluation results + reports (untracked, Tasks 62-85)
    entries.append({
        "path": "data/evaluation/ (98 untracked files: task62-83 results)",
        "exists": True,
        "size_bytes": None, "sha256": None,
        "classification": LOCAL_ONLY,
        "purpose": "recorded generation/retrieval results incl. Task 82/83 gates",
        "sensitivity": "none",
        "recovery_method": "recovery archive",
    })
    entries.append({
        "path": "data/reports/ (65 untracked of 180 total: task62-85 reports)",
        "exists": True,
        "size_bytes": None, "sha256": None,
        "classification": LOCAL_ONLY,
        "purpose": "task reports + machine-readable summaries (Tasks 62-85)",
        "sensitivity": "none",
        "recovery_method": "recovery archive",
    })

    # 8. DAPT-01 adapter — volatile /tmp location
    adapter_main = ADAPTER_DIR / "adapter_model.safetensors"
    entries.append({
        "path": "/tmp/opencode/task75/adapter_model.safetensors (+ config/tokenizer, 678M dir)",
        "exists": ADAPTER_DIR.is_dir(),
        "size_bytes": sum(f.stat().st_size for f in ADAPTER_DIR.rglob("*") if f.is_file()) if ADAPTER_DIR.is_dir() else None,
        "sha256": sha256_file(adapter_main) if adapter_main.is_file() else None,
        "classification": LOCAL_ONLY,
        "purpose": "DAPT-01 QLoRA checkpoint (sha 9b4d2bdc...); referenced by Task 82/83 integrity checks",
        "sensitivity": "none",
        "recovery_method": "recovery archive (copied in); EXTERNAL copy: Kaggle dataset priyanshu471/dapt01-checkpoint-15248",
        "notes": "AT RISK: lives in /tmp — may vanish on VM restart even before credit expiry",
    })

    # 9. Model weights — external
    entries.append({
        "path": "svk-corpus/.hf_cache/ (Qwen3-8B-Base, 16G, gitignored)",
        "exists": (R / ".hf_cache").is_dir(),
        "size_bytes": None, "sha256": None,
        "classification": EXTERNAL,
        "purpose": "Qwen3-8B-Base fp16 weights (rev 49e3418f...) — used only by historical Kaggle generation runs",
        "sensitivity": "none",
        "recovery_method": "huggingface-cli download Qwen/Qwen3-8B-Base (NOT included in archive)",
    })
    entries.append({
        "path": "~/.cache/huggingface/ (BGE-M3 4.3G, PaddleOCR, faster-whisper, 20G total)",
        "exists": Path.home().joinpath(".cache/huggingface").is_dir(),
        "size_bytes": None, "sha256": None,
        "classification": EXTERNAL,
        "purpose": "BGE-M3 encoder weights (rev 5617a9f...) + OCR/ASR models",
        "sensitivity": "none",
        "recovery_method": "huggingface-cli download BAAI/bge-m3 --revision 5617a9f61b028005a4858fdac845db406aefb181",
    })

    # 10. Virtualenvs — reproducible
    for v in (".venv", ".venv-cpu-bench"):
        entries.append({
            "path": f"svk-corpus/{v}/",
            "exists": (R / v).is_dir(),
            "size_bytes": None, "sha256": None,
            "classification": REPRODUCIBLE,
            "purpose": "isolated Python envs (fastapi/pydantic/uvicorn/httpx/numpy/faiss-cpu; cpu-bench torch)",
            "sensitivity": "none",
            "recovery_method": "python3 -m venv + pip install (see runbook §4); NOT archived",
        })

    # 11. Bench artifacts — excluded from archive, noted
    for rel, purpose in [
        (".bench_ckpt/", "CPU QLoRA micro-bench checkpoint (511M) — experimental, not the released DAPT-01 adapter"),
        ("data/domain_train/train.jsonl", "DAPT domain-training mix (723M, gitignored)"),
        ("data/release/low_quality_units.jsonl", "quality-stage byproduct (474M, gitignored, regenerable)"),
        ("data/quality/units_quality.jsonl", "quality scores (183M, gitignored, regenerable via make quality)"),
    ]:
        p = R / rel
        entries.append({
            "path": rel, "exists": p.exists(),
            "size_bytes": sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else (p.stat().st_size if p.is_file() else None),
            "sha256": None,
            "classification": REPRODUCIBLE if "regenerable" in purpose or "quality" in purpose else LOCAL_ONLY,
            "purpose": purpose,
            "sensitivity": "none",
            "recovery_method": "included in recovery archive except .bench_ckpt; can be regenerated by pipeline stages",
        })

    # 12. Secrets — name/size only, NEVER contents
    kaggle = Path.home() / ".kaggle" / "kaggle.json"
    entries.append({
        "path": "~/.kaggle/kaggle.json",
        "exists": kaggle.is_file(),
        "size_bytes": kaggle.stat().st_size if kaggle.is_file() else None,
        "sha256": None,   # deliberately not hashed into the manifest
        "classification": LOCAL_ONLY,
        "purpose": "Kaggle API credentials (name/size recorded only)",
        "sensitivity": "SECRET — contents never read, never archived, never committed",
        "recovery_method": "recreate from Kaggle account settings on the new machine",
    })

    # 13. Environment — names only
    project_env = [k for k in os.environ if k.startswith("SVK_") or k.startswith("KAGGLE")
                   or k.startswith("HF_") or k.startswith("OPENAI")]
    entries.append({
        "path": "(environment variables)",
        "exists": True, "size_bytes": None, "sha256": None,
        "classification": SAFE_IN_GIT,
        "purpose": "project-relevant env vars (names only): "
                   + (", ".join(project_env) if project_env else "NONE SET (API requires none)"),
        "sensitivity": "names only; no values recorded",
        "recovery_method": "SVK_RETRIEVAL_* are optional runtime flags; see runbook §9",
    })

    # 14. Documentation drift note
    repro = (R / "docs" / "REPRODUCIBILITY.md").read_text(encoding="utf-8")
    entries.append({
        "path": "docs/REPRODUCIBILITY.md",
        "exists": True,
        "size_bytes": (R / "docs" / "REPRODUCIBILITY.md").stat().st_size,
        "sha256": sha256_file(R / "docs" / "REPRODUCIBILITY.md"),
        "classification": SAFE_IN_GIT,
        "purpose": "pipeline reproducibility doc",
        "sensitivity": "none",
        "recovery_method": "git clone",
        "notes": ("states 'Python 3.14' but the VM runs 3.12.3; doc drift — "
                  "runbook §2 records the tested version"
                  if "Python 3.14" in repro else "no drift detected"),
    })

    manifest = {
        "task": 86,
        "title": "Azure expiry recovery manifest",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "generated_epoch": int(t0),
        "elapsed_s": round(time.time() - t0, 1),
        "source_environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "git_branch": branch,
            "git_head": commit,
            "git_remote_host_path": remote_sanitised,  # sanitised: no credentials
            "tracked_modifications": tracked_mods,
            "untracked_count": len(untracked),
        },
        "classification_vocabulary": [SAFE_IN_GIT, LOCAL_ONLY, REPRODUCIBLE,
                                      EXTERNAL, MISSING, UNKNOWN],
        "artifacts": entries,
        "summary": {
            "safe_in_git": sum(1 for e in entries if e["classification"] == SAFE_IN_GIT),
            "local_only": sum(1 for e in entries if e["classification"] == LOCAL_ONLY),
            "reproducible": sum(1 for e in entries if e["classification"] == REPRODUCIBLE),
            "external_dependency": sum(1 for e in entries if e["classification"] == EXTERNAL),
            "missing": sum(1 for e in entries if e["classification"] == MISSING),
        },
        "backup_status": {
            "local_archive_command": (
                "tar -czf ~/svk-recovery-$(date +%Y%m%d).tar.gz "
                "--exclude='svk-corpus/.venv' --exclude='svk-corpus/.venv-cpu-bench' "
                "--exclude='svk-corpus/.hf_cache' --exclude='svk-corpus/.bench_ckpt' "
                "--exclude='__pycache__' --exclude='.pytest_cache' --exclude='*.pyc' "
                "-C ~ jainLLM/svk-corpus -C /tmp opencode/task75"
            ),
            "external_backup_verified": False,
            "external_backup_note": (
                "GitHub remote exists (github.com/Priyanshu-47/jainLLM) but pushing "
                "requires explicit user authorization — NOT pushed by Task 86. "
                "A local archive on this VM is NOT an external backup."
            ),
        },
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    # ---- ARTIFACT_INVENTORY.md -------------------------------------------
    def fmt_size(n):
        if n is None:
            return "—"
        for unit in ("B", "K", "M", "G"):
            if n < 1024:
                return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
            n /= 1024
        return f"{n:.1f}T"

    lines = [
        "# Artifact Inventory — Task 86",
        "",
        f"Generated: {manifest['generated_utc']} · Git HEAD `{commit[:12]}` · branch `{branch}`",
        "",
        "Classifications: `SAFE_IN_GIT` · `LOCAL_ONLY` · `REPRODUCIBLE` · "
        "`EXTERNAL_DEPENDENCY` · `MISSING` · `UNKNOWN`.",
        "",
        "| Path | Size | SHA-256 (first 16) | Class | Purpose | Sensitivity | Recovery |",
        "|---|---|---|---|---|---|---|",
    ]
    for e in entries:
        sha = (e.get("sha256") or "—")
        sha_s = (sha[:16] + "…") if isinstance(sha, str) and sha != "—" else "—"
        size = fmt_size(e.get("size_bytes"))
        path = e["path"].replace("|", "\\|")
        lines.append(
            f"| `{path}` | {size} | `{sha_s}` | **{e['classification']}** | "
            f"{e['purpose']} | {e['sensitivity']} | {e['recovery_method']} |"
        )
    lines += [
        "",
        "## Explicit exclusions",
        "",
        "- `.venv/`, `.venv-cpu-bench/` — reproducible via pip; not archived.",
        "- `.hf_cache/` (16G) — Hugging Face re-download; not archived.",
        "- `~/.cache/huggingface/` (20G) — Hugging Face re-download; not archived.",
        "- `.bench_ckpt/` (511M) — experimental CPU bench checkpoint; not archived.",
        "- `~/.kaggle/kaggle.json` — SECRET; never read, never archived, never committed.",
        "",
        "## At-risk items (action required before expiry)",
        "",
        "1. `/tmp/opencode/task75/` — DAPT-01 adapter lives in `/tmp` (volatile).",
        "   Kaggle dataset `priyanshu471/dapt01-checkpoint-15248` is an external copy.",
        "2. 202 untracked files (all Tasks 62–85 work) exist ONLY on this VM.",
        "3. `configs/policy.toml` +27-line retrieval section is uncommitted.",
        "",
        "See `RESTORE_VERIFICATION.md` for the checks to run after restore.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT_JSON.relative_to(REPO)} ({len(entries)} artifacts)")
    print(f"wrote {OUT_MD.relative_to(REPO)}")
    print(f"summary: {manifest['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
