"""TASK 82 Phase-2 — build the self-contained Kaggle kernel for four-arm generation.

Adapts experiments/task75/task75_rag_infer.py byte-for-byte in protocol
(transformers 5.0.0 / peft 0.19.1 / bnb 0.50.2, 4-bit NF4 double, fp16 compute,
greedy, max_new_tokens=192, seed=42, chat_template w/ plain fallback, SDPA
memory-efficient only) and changes ONLY:
  - evidence: optimized H3_RRF20 (BM25 pool=250) prompts (embedded, gzip+base64)
  - run host: Kaggle T4 (established safe execution method; Colab token expired)
  - adapter: attached Kaggle dataset priyanshu471/dapt01-checkpoint-15248
    (read-only; sha-verified in-kernel against 9b4d2bdc…)

Outputs
  experiments/task82/kaggle/task82_rag_infer_kaggle.py  (self-contained kernel)
  experiments/task82/kaggle/kernel-metadata.json

Push with:  kaggle kernels push -p experiments/task82/kaggle
Pull with:  kaggle kernels output priyanshu471/task82-four-arm-pool250 -p data/raw/task82
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROMPTS = REPO / "data" / "evaluation" / "task82_rag_prompts.jsonl"
OUT_DIR = REPO / "experiments" / "task82" / "kaggle"

ADAPTER_SHA = "9b4d2bdcfe089118d0634815596b628506a83c434d3863cff7a731cba75a58e9"

KERNEL_TEMPLATE = r'''"""TASK 82 Kaggle kernel — four-arm generation gate over optimized H3_RRF20
(BM25 pool=250) evidence.

Byte-for-byte the same generation protocol as experiments/task75/task75_rag_infer.py
(transformers 5.0.0 / peft 0.19.1 / bnb 0.50.2, 4-bit NF4 double, fp16 compute,
greedy, max_new_tokens=192, seed=42, chat_template w/ plain fallback).

Four arms (single model load; adapter attached once for DAPT arms):
  A base_norag    BASE, question only
  C base_rrf250   BASE, optimized H3_RRF20 evidence+question
  B dapt_norag    DAPT-01, question only
  D dapt_rrf250   DAPT-01, optimized H3_RRF20 evidence+question (identical bytes to C)

Inputs
  - attached dataset priyanshu471/dapt01-checkpoint-15248 (adapter, read-only)
  - prompts embedded in this file (gzip+base64 of task82_rag_prompts.jsonl)

Outputs (to /kaggle/working, pulled back with `kaggle kernels output`)
  task82_base_norag_results.jsonl, task82_base_rrf250_results.jsonl,
  task82_dapt_norag_results.jsonl, task82_dapt_rrf250_results.jsonl,
  task82_rag_run_metadata.json
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path


def _import_ok(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except Exception:
        return False


_PIN_PREFIXES = (
    "transformers", "peft", "bitsandbytes", "tokenizers",
    "accelerate", "huggingface_hub", "safetensors",
)


def purge_preimported() -> None:
    """Kaggle notebooks pre-import transformers (5.16.x) into sys.modules at
    startup; a pip pin alone leaves the cached 5.16 module in place. Drop the
    cached modules so the next import binds the freshly pinned versions."""
    dropped = [
        m for m in list(sys.modules)
        if m.split(".")[0] in _PIN_PREFIXES
    ]
    for m in dropped:
        del sys.modules[m]
    if dropped:
        print(f"[deps] purged {len(dropped)} pre-imported modules "
              f"(e.g. {dropped[:5]})", flush=True)


def ensure_deps() -> None:
    wanted = {
        "transformers": "5.0.0",
        "peft": "0.19.1",
        "bitsandbytes": "0.50.2",
    }
    last = ""
    for attempt in range(1, 7):
        need = []
        for pkg, ver in wanted.items():
            if not _import_ok(pkg):
                need.append(f"{pkg}=={ver}")
            else:
                from importlib.metadata import version as _v
                try:
                    if _v(pkg) != ver:
                        need.append(f"{pkg}=={ver}")
                except Exception:
                    need.append(f"{pkg}=={ver}")
        if not need:
            print("[deps] pinned stack present", flush=True)
            purge_preimported()
            return
        print(f"[deps] pip install {' '.join(need)} (attempt {attempt})", flush=True)
        r = subprocess.run(
            f"{sys.executable} -m pip install -q --retries 10 --timeout 60 {' '.join(need)}",
            shell=True, capture_output=True, text=True, timeout=1800,
        )
        last = ((r.stdout or "") + (r.stderr or ""))[-500:]
        if r.returncode == 0:
            print("[deps] pip ok", flush=True)
            purge_preimported()
            return
        print(f"[deps] attempt {attempt} failed: {last}", flush=True)
        time.sleep(15 * attempt)
    print(f"[deps] WARNING continuing with preinstalled stack after: {last}", flush=True)
    purge_preimported()


ensure_deps()

import torch  # noqa: E402

torch.backends.cuda.enable_flash_sdp(False)
torch.backends.cuda.enable_mem_efficient_sdp(True)
torch.backends.cuda.enable_math_sdp(False)
torch.backends.cuda.enable_cudnn_sdp(False)

import transformers.integrations.sdpa_attention as _sda  # noqa: E402


def _use_gqa_false(attention_mask, key):  # noqa: ANN001
    return False


_sda.use_gqa_in_sdpa = _use_gqa_false

from peft import PeftModel  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig  # noqa: E402

_tv = __import__("transformers").__version__
if _tv != "5.0.0":
    import transformers as _t
    from importlib.metadata import version as _ver
    raise SystemExit(
        f"transformers {_tv} ({getattr(_t, '__file__', '?')}) "
        f"dist={_ver('transformers')} != 5.0.0 — mixed stack"
    )

MODEL_ID = "Qwen/Qwen3-8B-Base"
WORK = Path("/kaggle/working")
PROMPTS_PATH = WORK / "task82_rag_prompts.jsonl"
ADAPTER_SHA_EXPECTED = "@@ADAPTER_SHA@@"
PROMPTS_SHA_EXPECTED = "@@PROMPTS_SHA@@"

PROMPTS_B64 = "@@PROMPTS_B64@@"

SYSTEM_PROMPT = (
    "You are a careful assistant for Jain studies. "
    "Answer the user's question concisely (in 1-3 sentences). "
    "If you are unsure or the information is not available, say so."
)
MAX_NEW_TOKENS = 192
SEED = 42


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_adapter_dir() -> Path:
    import glob as _glob
    cands = [
        Path("/kaggle/input/dapt01-checkpoint-15248"),
        *sorted(Path("/kaggle/input").glob("**/*dapt01-checkpoint-15248*")),
        *sorted(Path("/kaggle/input").glob("**/*checkpoint-15248*")),
        *sorted(Path("/kaggle/input").glob("**/adapter_model.safetensors")),
    ]
    for c in cands:
        if c.is_file() and c.name == "adapter_model.safetensors":
            return c.parent
        if c.is_dir() and (c / "adapter_model.safetensors").exists():
            return c
        if c.is_dir():
            hits = list(c.rglob("adapter_model.safetensors"))
            if hits:
                return hits[0].parent
    try:
        import kagglehub
        dl = Path(kagglehub.dataset_download("priyanshu471/dapt01-checkpoint-15248"))
        if (dl / "adapter_model.safetensors").exists():
            return dl
        for sub in dl.rglob("adapter_model.safetensors"):
            return sub.parent
    except Exception as exc:
        log(f"kagglehub fallback failed: {exc}")
    raise FileNotFoundError(
        f"adapter not found; inputs={list(Path('/kaggle/input').iterdir())}"
    )


def load_prompts() -> list[dict]:
    raw = gzip.decompress(base64.b64decode(PROMPTS_B64))
    PROMPTS_PATH.write_bytes(raw)
    sha = sha256_file(PROMPTS_PATH)
    if sha != PROMPTS_SHA_EXPECTED:
        raise SystemExit(f"prompts sha mismatch: {sha} != {PROMPTS_SHA_EXPECTED}")
    log(f"prompts sha verified {sha[:16]}...")
    rows = [
        json.loads(ln)
        for ln in raw.decode("utf-8").splitlines()
        if ln.strip()
    ]
    if len(rows) != 47:
        raise SystemExit(f"expected 47 prompt rows, got {len(rows)}")
    for r in rows:
        if not r.get("user_content") or not r.get("question"):
            raise SystemExit(f"empty user_content/question for {r['example_id']}")
    return rows


def build_prompt(tokenizer, user_content: str) -> tuple[str, str]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    if getattr(tokenizer, "chat_template", None):
        prompt = tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False
        )
        return prompt, "chat_template"
    prompt = f"{SYSTEM_PROMPT}\n\n{user_content}\n"
    return prompt, "plain_fallback"


def generate(model, tokenizer, prompt: str) -> dict:
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    t0 = time.time()
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    new_ids = out[0][inputs["input_ids"].shape[1]:]
    text = tokenizer.decode(new_ids, skip_special_tokens=True)
    return {
        "answer": text.strip(),
        "new_tokens": int(new_ids.shape[0]),
        "decode_seconds": round(time.time() - t0, 3),
    }


def run_rows(model, tokenizer, rows: list[dict], arm: str, rag: bool) -> list[dict]:
    out = []
    for i, r in enumerate(rows, 1):
        user_content = r["user_content"] if rag else r["question"]
        prompt, style = build_prompt(tokenizer, user_content)
        gen = generate(model, tokenizer, prompt)
        row = {
            "example_id": r["example_id"],
            "arm": arm,
            "question": r["question"],
            "answer": gen["answer"],
            "prompt_style": style,
            "system_prompt": SYSTEM_PROMPT,
            "decoding": "greedy",
            "max_new_tokens": MAX_NEW_TOKENS,
            "new_tokens": gen["new_tokens"],
            "decode_seconds": gen["decode_seconds"],
            "seed": SEED,
            "rag": rag,
            "input_prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        }
        if rag:
            row["evidence_context_sha256"] = r["context_sha256"]
            row["n_evidence_items"] = r["n_evidence_items"]
        out.append(row)
        log(
            f"  [{i}/{len(rows)}] {r['example_id']} ({gen['new_tokens']} tok) "
            f"{gen['answer'][:100]!r}"
        )
        print("RESULT_JSON::" + json.dumps(out[-1], ensure_ascii=False), flush=True)
    return out


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    log(f"wrote {path} ({len(rows)} rows)")


def main() -> None:
    torch.manual_seed(SEED)
    WORK.mkdir(parents=True, exist_ok=True)

    adapter_dir = resolve_adapter_dir()
    adapter_weights = adapter_dir / "adapter_model.safetensors"
    adapter_cfg = adapter_dir / "adapter_config.json"
    if not adapter_weights.exists() or not adapter_cfg.exists():
        raise FileNotFoundError(f"adapter files missing under {adapter_dir}")
    adapter_sha = sha256_file(adapter_weights)
    if adapter_sha != ADAPTER_SHA_EXPECTED:
        raise SystemExit(f"adapter sha mismatch: {adapter_sha}")
    log(f"adapter sha verified {adapter_sha[:16]}... dir={adapter_dir}")

    rows = load_prompts()

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    log(f"loading tokenizer {MODEL_ID}")
    tok = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    log(f"loading base model {MODEL_ID} (4-bit nf4)")
    t_load = time.time()
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16,
    )
    model.eval()
    load_s = time.time() - t_load

    timings: dict[str, float] = {}

    log("=== ARM A: BASE, no RAG ===")
    t0 = time.time()
    a_rows = run_rows(model, tok, rows, arm="base_norag", rag=False)
    timings["base_norag_infer_seconds"] = round(time.time() - t0, 1)
    write_jsonl(WORK / "task82_base_norag_results.jsonl", a_rows)

    log("=== ARM C: BASE + optimized H3_RRF20 (pool=250) ===")
    t0 = time.time()
    c_rows = run_rows(model, tok, rows, arm="base_rrf250", rag=True)
    timings["base_rrf250_infer_seconds"] = round(time.time() - t0, 1)
    write_jsonl(WORK / "task82_base_rrf250_results.jsonl", c_rows)

    log("attaching DAPT-01 adapter (no merge)")
    t0 = time.time()
    model = PeftModel.from_pretrained(model, str(adapter_dir), is_trainable=False)
    model.eval()
    timings["adapter_attach_seconds"] = round(time.time() - t0, 1)

    log("=== ARM B: DAPT-01, no RAG ===")
    t0 = time.time()
    b_rows = run_rows(model, tok, rows, arm="dapt_norag", rag=False)
    timings["dapt_norag_infer_seconds"] = round(time.time() - t0, 1)
    write_jsonl(WORK / "task82_dapt_norag_results.jsonl", b_rows)

    log("=== ARM D: DAPT-01 + optimized H3_RRF20 (pool=250) ===")
    t0 = time.time()
    d_rows = run_rows(model, tok, rows, arm="dapt_rrf250", rag=True)
    timings["dapt_rrf250_infer_seconds"] = round(time.time() - t0, 1)
    write_jsonl(WORK / "task82_dapt_rrf250_results.jsonl", d_rows)

    ctx_ok = all(
        c["evidence_context_sha256"] == d["evidence_context_sha256"]
        for c, d in zip(c_rows, d_rows)
    )
    if not ctx_ok:
        raise SystemExit("STOP: C/D context shas differ")
    log("C/D identical contexts verified")

    gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    metadata = {
        "task": "TASK 82 — FOUR-ARM OPTIMIZED H3_RRF20 (pool=250) GENERATION GATE",
        "model": MODEL_ID,
        "adapter": "DAPT-01 checkpoint-15248 (priyanshu471/dapt01-checkpoint-15248)",
        "adapter_sha256": adapter_sha,
        "adapter_merged": False,
        "quantization": "4bit-nf4-double, compute dtype fp16 (identical all arms)",
        "attention_backend": (
            "torch SDPA memory-efficient only (math disabled; flash/cudnn invalid "
            "on sm75 T4; transformers enable_gqa forced to repeat_kv). fp16 numerics; "
            "greedy/seed/cap/prompts/model unchanged from Task-75"
        ),
        "system_prompt": SYSTEM_PROMPT,
        "system_prompt_identical_to_task60_69_71_75": True,
        "user_content": {
            "norag_arms": "frozen question only (Task-60 protocol)",
            "rag_arms": (
                "optimized H3_RRF20 (BM25 pool=250) governed evidence + question"
            ),
        },
        "prompts_file": "task82_rag_prompts.jsonl",
        "prompts_sha256": PROMPTS_SHA_EXPECTED,
        "evidence_window": (
            "optimized H3_RRF20 (BM25 pool=250, EVIDENCE_K=5, TEXT_TRUNC=500, RRF k=20)"
        ),
        "n_evidence_items_per_case": 5,
        "prompt_style": "chat_template if available else plain_fallback",
        "decoding": "greedy (do_sample=False)",
        "max_new_tokens": MAX_NEW_TOKENS,
        "seed": SEED,
        "n_cases": len(rows),
        "arms": ["base_norag", "base_rrf250", "dapt_norag", "dapt_rrf250"],
        "gpu": gpu,
        "torch": torch.__version__,
        "python": platform.python_version(),
        "transformers": __import__("transformers").__version__,
        "peft": __import__("peft").__version__,
        "bitsandbytes": __import__("bitsandbytes").__version__,
        "model_load_seconds": round(load_s, 1),
        **timings,
        "identical_contexts_both_rag_arms": True,
        "run_host": "Kaggle T4 (established safe execution method; Colab token expired)",
        "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (WORK / "task82_rag_run_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    log(f"metadata: {json.dumps(metadata)}")
    log("TASK 82 KAGGLE KERNEL DONE")


if __name__ == "__main__":
    main()
'''

METADATA = {
    "id": "priyanshu471/task82-four-arm-optimized-h3-rrf20-pool250-gate",
    "title": "TASK82 Four-Arm Optimized H3 RRF20 Pool250 Gate",
    "code_file": "task82_rag_infer_kaggle.py",
    "language": "python",
    "kernel_type": "script",
    "is_private": "true",
    "enable_gpu": "true",
    "enable_tpu": "false",
    "enable_internet": "true",
    "machine_shape": "NvidiaTeslaT4",
    "dataset_sources": ["priyanshu471/dapt01-checkpoint-15248"],
    "competition_sources": [],
    "kernel_sources": [],
    "model_sources": [],
}


def main() -> int:
    raw = PROMPTS.read_bytes()
    prompts_sha = hashlib.sha256(raw).hexdigest()
    b64 = base64.b64encode(gzip.compress(raw, compresslevel=9)).decode("ascii")
    print(f"prompts {len(raw)}B -> gzip+b64 {len(b64)}B, sha {prompts_sha[:16]}…")

    kernel = (
        KERNEL_TEMPLATE
        .replace("@@ADAPTER_SHA@@", ADAPTER_SHA)
        .replace("@@PROMPTS_SHA@@", prompts_sha)
        .replace("@@PROMPTS_B64@@", b64)
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "task82_rag_infer_kaggle.py").write_text(kernel, encoding="utf-8")
    (OUT_DIR / "kernel-metadata.json").write_text(
        json.dumps(METADATA, indent=2), encoding="utf-8")
    print(f"wrote {OUT_DIR / 'task82_rag_infer_kaggle.py'} "
          f"({(OUT_DIR / 'task82_rag_infer_kaggle.py').stat().st_size} B)")
    print(f"wrote {OUT_DIR / 'kernel-metadata.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
