"""TASK 71 Colab kernel — R7 governed-RAG generation (+ Phase-3 baseline reproduction).

Byte-for-byte the same generation protocol as experiments/task69/task69_rag_infer.py:
  - model: Qwen/Qwen3-8B-Base (4-bit NF4 double, fp16 compute, same load path)
  - adapter: DAPT-01 checkpoint-15248 (attached, never merged) for the DAPT arms
  - system prompt: byte-identical to Task-60/69
  - greedy, max_new_tokens=192, seed=42
  - chat_template prompt style with plain fallback

Variant selected by env TASK71_VARIANT (set via `colab exec --env TASK71_VARIANT=...`):

  baseline (Phase 3 reproduction gate)
    prompts  : /content/task71/task69_rag_prompts.jsonl  (uploaded copy of the
               frozen Task-69 prompts file; sha must equal
               00096f61a4a2aea525b2f1bfe71449b626bc17a60073e4b4e9dac05f6edd5b8e)
    arms     : base_rag only
    outputs  : out/task71_baseline_base_rag_results.jsonl
               out/task71_baseline_run_metadata.json
    gate     : prompts sha mismatch -> STOP (SystemExit)

  r7 (Phase 4 controlled evaluation)
    prompts  : /content/task71/task71_r7_prompts.jsonl  (sha recorded;
               every row must carry n_evidence_items == 10)
    arms     : base_rag, dapt_rag
    outputs  : out/task71_base_rag_results.jsonl
               out/task71_dapt_rag_results.jsonl
               out/task71_r7_run_metadata.json

Inputs (uploaded to /content/task71):
  adapter/adapter_model.safetensors (reassembled from p00..p03, sha-verified),
  adapter/adapter_config.json, one of the two prompts files above.
"""

from __future__ import annotations

import gc
import hashlib
import json
import os
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


def ensure_deps() -> None:
    """Pin the Task-60 evaluation stack (transformers 5.0.0 / peft 0.19.1 / bnb 0.50.2)."""
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
            return
        print(f"[deps] pip install {' '.join(need)} (attempt {attempt})", flush=True)
        r = subprocess.run(
            f"{sys.executable} -m pip install -q --retries 10 --timeout 60 {' '.join(need)}",
            shell=True, capture_output=True, text=True, timeout=1800,
        )
        last = ((r.stdout or "") + (r.stderr or ""))[-500:]
        if r.returncode == 0:
            print("[deps] pip ok", flush=True)
            return
        print(f"[deps] attempt {attempt} failed: {last}", flush=True)
        time.sleep(15 * attempt)
    print(f"[deps] WARNING continuing with preinstalled stack after: {last}", flush=True)


ensure_deps()

import torch  # noqa: E402

# R7 sequences (up to ~15k context chars) make the math SDPA backend allocate
# SxSxHx4B tensors (~6.5-9.5 GiB) and OOM on the 14.5 GiB T4. flash/cudnn are
# invalid on sm75 (T4) and raise "Invalid backend" if left enabled. Config:
# memory-efficient only (verified OK at S=9000, peak 0.87 GiB). fp16 numerics;
# greedy decoding, seed, cap, prompts and model are untouched.
torch.backends.cuda.enable_flash_sdp(False)
torch.backends.cuda.enable_mem_efficient_sdp(True)
torch.backends.cuda.enable_math_sdp(False)
torch.backends.cuda.enable_cudnn_sdp(False)

# transformers 5.0 passes enable_gqa=True to F.sdpa (32 Q / 8 KV heads). On this
# torch 2.11/T4 build only math SDPA accepts enable_gqa, and math OOMs at R7
# lengths; mem-efficient rejects it ("Invalid backend"). Forcing repeat_kv makes
# the wrapper expand KV heads explicitly — same computation, mem-compatible.
import transformers.integrations.sdpa_attention as _sda  # noqa: E402


def _use_gqa_false(attention_mask, key):  # noqa: ANN001
    return False


_sda.use_gqa_in_sdpa = _use_gqa_false

from peft import PeftModel  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig  # noqa: E402

MODEL_ID = "Qwen/Qwen3-8B-Base"
ROOT = Path("/content/task71")
ADAPTER_DIR = ROOT / "adapter"
WORK = ROOT / "out"

ADAPTER_SHA_EXPECTED = "9b4d2bdcfe089118d0634815596b628506a83c434d3863cff7a731cba75a58e9"
TASK69_PROMPTS_SHA = "00096f61a4a2aea525b2f1bfe71449b626bc17a60073e4b4e9dac05f6edd5b8e"

VARIANT = os.environ.get("TASK71_VARIANT", "r7").strip().lower()
if VARIANT == "baseline":
    PROMPTS_PATH = ROOT / "task69_rag_prompts.jsonl"
    EXPECTED_PROMPTS_SHA = TASK69_PROMPTS_SHA
    ARMS = ("base_rag",)
    OUT_RESULTS = {"base_rag": WORK / "task71_baseline_base_rag_results.jsonl"}
    OUT_META = WORK / "task71_baseline_run_metadata.json"
elif VARIANT == "r7":
    PROMPTS_PATH = ROOT / "task71_r7_prompts.jsonl"
    EXPECTED_PROMPTS_SHA = None  # recorded, not pre-known
    ARMS = ("base_rag", "dapt_rag")
    OUT_RESULTS = {
        "base_rag": WORK / "task71_base_rag_results.jsonl",
        "dapt_rag": WORK / "task71_dapt_rag_results.jsonl",
    }
    OUT_META = WORK / "task71_r7_run_metadata.json"
else:
    raise SystemExit(f"TASK71_VARIANT must be baseline|r7, got {VARIANT!r}")

# Byte-identical to Task-60 (task60_infer_kaggle.py) and Task-69.
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


def load_prompts() -> list[dict]:
    rows = [
        json.loads(ln)
        for ln in PROMPTS_PATH.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    if len(rows) != 47:
        raise SystemExit(f"expected 47 prompt rows, got {len(rows)}")
    for r in rows:
        if not r.get("user_content"):
            raise SystemExit(f"empty user_content for {r['example_id']}")
        if VARIANT == "r7" and r.get("n_evidence_items") != 10:
            raise SystemExit(
                f"STOP: {r['example_id']} n_evidence_items="
                f"{r.get('n_evidence_items')} != 10 (R7 window not applied)"
            )
        if VARIANT == "baseline" and r.get("n_evidence_items") != 5:
            raise SystemExit(
                f"STOP: {r['example_id']} n_evidence_items="
                f"{r.get('n_evidence_items')} != 5 (baseline must stay Task-69)"
            )
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


def _oom_cleanup() -> None:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _generate_once(model, tokenizer, prompt: str) -> dict:
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


def generate(model, tokenizer, prompt: str) -> dict:
    try:
        return _generate_once(model, tokenizer, prompt)
    except torch.cuda.OutOfMemoryError:
        print("[oom] CUDA OOM during generate — cleaning cache, retrying once", flush=True)
        _oom_cleanup()
        return _generate_once(model, tokenizer, prompt)


def run_rows(model, tokenizer, rows: list[dict], arm: str) -> list[dict]:
    out = []
    for i, r in enumerate(rows, 1):
        prompt, style = build_prompt(tokenizer, r["user_content"])
        gen = generate(model, tokenizer, prompt)
        out.append(
            {
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
                "rag": True,
                "evidence_context_sha256": r["context_sha256"],
                "n_evidence_items": r["n_evidence_items"],
                "input_prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            }
        )
        log(
            f"  [{i}/{len(rows)}] {r['example_id']} ({gen['new_tokens']} tok) "
            f"{gen['answer'][:100]!r}"
        )
        print("RESULT_JSON::" + json.dumps(out[-1], ensure_ascii=False), flush=True)
        _oom_cleanup()
        if torch.cuda.is_available():
            alloc = torch.cuda.memory_allocated() / 2**30
            reserv = torch.cuda.memory_reserved() / 2**30
            log(f"  cuda mem alloc={alloc:.2f}GiB reserved={reserv:.2f}GiB")
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
    log(f"TASK71_VARIANT={VARIANT}")

    adapter_weights = ADAPTER_DIR / "adapter_model.safetensors"
    adapter_cfg = ADAPTER_DIR / "adapter_config.json"
    for p in (adapter_weights, adapter_cfg, PROMPTS_PATH):
        if not p.exists():
            raise FileNotFoundError(p)

    adapter_sha = sha256_file(adapter_weights)
    prompts_sha = sha256_file(PROMPTS_PATH)
    if adapter_sha != ADAPTER_SHA_EXPECTED:
        raise SystemExit(f"adapter sha mismatch: {adapter_sha}")
    if EXPECTED_PROMPTS_SHA and prompts_sha != EXPECTED_PROMPTS_SHA:
        raise SystemExit(
            f"STOP: baseline prompts sha {prompts_sha} != Task-69 {EXPECTED_PROMPTS_SHA}"
        )
    log(f"adapter sha verified {adapter_sha[:16]}…")

    rows = load_prompts()
    log(f"{len(rows)} prompt rows; prompts sha {prompts_sha[:16]}…")

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
    _oom_cleanup()
    log(
        "sdp backends: mem_efficient="
        f"{torch.backends.cuda.mem_efficient_sdp_enabled()} "
        f"math={torch.backends.cuda.math_sdp_enabled()} "
        f"flash={torch.backends.cuda.flash_sdp_enabled()}"
    )

    timings: dict[str, float | None] = {"model_load_seconds": round(load_s, 1)}
    adapter_s = None

    log("=== ARM A: BASE + RAG ===")
    t0 = time.time()
    base_rows = run_rows(model, tok, rows, arm="base_rag")
    base_s = time.time() - t0
    write_jsonl(OUT_RESULTS["base_rag"], base_rows)
    timings["base_rag_infer_seconds"] = round(base_s, 1)

    if "dapt_rag" in ARMS:
        log("attaching DAPT-01 adapter (no merge)")
        t0 = time.time()
        model = PeftModel.from_pretrained(model, str(ADAPTER_DIR), is_trainable=False)
        model.eval()
        adapter_s = time.time() - t0

        log("=== ARM B: DAPT-01 + RAG ===")
        t0 = time.time()
        dapt_rows = run_rows(model, tok, rows, arm="dapt_rag")
        dapt_s = time.time() - t0
        write_jsonl(OUT_RESULTS["dapt_rag"], dapt_rows)
        timings["adapter_attach_seconds"] = round(adapter_s, 1)
        timings["dapt_rag_infer_seconds"] = round(dapt_s, 1)

    gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    metadata = {
        "task": "TASK 71 — R7 GOVERNED RAG CONTROLLED EVALUATION (generation)",
        "variant": VARIANT,
        "model": MODEL_ID,
        "adapter": "DAPT-01 checkpoint-15248 (priyanshu471/dapt01-checkpoint-15248)",
        "adapter_sha256": adapter_sha,
        "adapter_merged": False,
        "quantization": "4bit-nf4-double, compute dtype fp16 (identical for both arms)",
        "attention_backend": (
            "torch SDPA memory-efficient only (math disabled — math materializes "
            "SxSxH fp32 buffers and OOMs at R7 sequence lengths on the 14.5GiB T4; "
            "flash/cudnn disabled — invalid on sm75 T4; transformers enable_gqa "
            "forced to repeat_kv path — mem-efficient has no GQA kernel here. "
            "fp16 numerics; greedy/seed/cap/prompts/model unchanged)"
        ),
        "system_prompt": SYSTEM_PROMPT,
        "system_prompt_identical_to_task60_task69": True,
        "user_content": "governed evidence context + frozen question (identical bytes both arms)",
        "prompts_file": PROMPTS_PATH.name,
        "prompts_sha256": prompts_sha,
        "evidence_window": (
            "Task-69 (EVIDENCE_K=5, TEXT_TRUNC=500)" if VARIANT == "baseline"
            else "R7 (EVIDENCE_K=10, TEXT_TRUNC=1000)"
        ),
        "n_evidence_items_per_case": 5 if VARIANT == "baseline" else 10,
        "prompt_style": "chat_template if available else plain_fallback",
        "decoding": "greedy (do_sample=False)",
        "max_new_tokens": MAX_NEW_TOKENS,
        "seed": SEED,
        "n_cases": len(rows),
        "arms": list(ARMS),
        "gpu": gpu,
        "torch": torch.__version__,
        "python": platform.python_version(),
        "transformers": __import__("transformers").__version__,
        "peft": __import__("peft").__version__,
        "bitsandbytes": __import__("bitsandbytes").__version__,
        **timings,
        "identical_contexts_both_rag_arms": True,
        "run_host": "Google Colab T4 (google-colab-cli; NOT Kaggle)",
        "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    OUT_META.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    log(f"metadata: {json.dumps(metadata)}")
    log(f"TASK 71 COLAB KERNEL DONE variant={VARIANT}")


if __name__ == "__main__":
    main()
