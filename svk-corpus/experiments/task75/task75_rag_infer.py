"""TASK 75 Colab kernel — four-arm generation gate over H3_RRF20 evidence.

Byte-for-byte the same generation protocol as experiments/task69/task69_rag_infer.py
(transformers 5.0.0 / peft 0.19.1 / bnb 0.50.2, 4-bit NF4 double, fp16 compute,
greedy, max_new_tokens=192, seed=42, chat_template w/ plain fallback).

Four arms (single model load; adapter attached once for DAPT arms):
  A base_norag   BASE, question only            (user_content = frozen question)
  C base_rrf20   BASE, H3_RRF20 evidence+question
  B dapt_norag   DAPT-01, question only
  D dapt_rrf20   DAPT-01, H3_RRF20 evidence+question (identical bytes to C)

SDPA: memory-efficient only (math OOMs at R7 lengths on 14.5GiB T4; flash/cudnn
invalid on sm75; transformers enable_gqa forced to repeat_kv). fp16 numerics;
greedy/seed/cap/prompts/model unchanged. Safe at Task-69/R0 lengths too.

Inputs (uploaded to /content/task75):
  adapter/adapter_model.safetensors, adapter/adapter_config.json,
  task75_rag_prompts.jsonl

Outputs (downloaded back):
  task75_base_norag_results.jsonl, task75_base_rrf20_results.jsonl,
  task75_dapt_norag_results.jsonl, task75_dapt_rrf20_results.jsonl,
  task75_rag_run_metadata.json
"""

from __future__ import annotations

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

# Task-69 mixed-version guard: Colab kernels pre-import transformers into
# sys.modules; a pip-only pin leaves a mixed 5.17/5.0.0 stack that crashes
# create_causal_mask at first forward. After the pin+restart flow the import
# must report exactly 5.0.0 — hard-stop otherwise.
_tv = __import__("transformers").__version__
if _tv != "5.0.0":
    raise SystemExit(f"transformers {_tv} != 5.0.0 — mixed stack; restart-kernel after pin")

MODEL_ID = "Qwen/Qwen3-8B-Base"
ROOT = Path("/content/task75")
ADAPTER_DIR = ROOT / "adapter"
PROMPTS_PATH = ROOT / "task75_rag_prompts.jsonl"
WORK = ROOT / "out"

ADAPTER_SHA_EXPECTED = "9b4d2bdcfe089118d0634815596b628506a83c434d3863cff7a731cba75a58e9"

# Byte-identical to Task-60/69/71.
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

    adapter_weights = ADAPTER_DIR / "adapter_model.safetensors"
    adapter_cfg = ADAPTER_DIR / "adapter_config.json"
    for p in (adapter_weights, adapter_cfg, PROMPTS_PATH):
        if not p.exists():
            raise FileNotFoundError(p)

    adapter_sha = sha256_file(adapter_weights)
    prompts_sha = sha256_file(PROMPTS_PATH)
    if adapter_sha != ADAPTER_SHA_EXPECTED:
        raise SystemExit(f"adapter sha mismatch: {adapter_sha}")
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

    timings: dict[str, float] = {}

    log("=== ARM A: BASE, no RAG ===")
    t0 = time.time()
    a_rows = run_rows(model, tok, rows, arm="base_norag", rag=False)
    timings["base_norag_infer_seconds"] = round(time.time() - t0, 1)
    write_jsonl(WORK / "task75_base_norag_results.jsonl", a_rows)

    log("=== ARM C: BASE + H3_RRF20 ===")
    t0 = time.time()
    c_rows = run_rows(model, tok, rows, arm="base_rrf20", rag=True)
    timings["base_rrf20_infer_seconds"] = round(time.time() - t0, 1)
    write_jsonl(WORK / "task75_base_rrf20_results.jsonl", c_rows)

    log("attaching DAPT-01 adapter (no merge)")
    t0 = time.time()
    model = PeftModel.from_pretrained(model, str(ADAPTER_DIR), is_trainable=False)
    model.eval()
    timings["adapter_attach_seconds"] = round(time.time() - t0, 1)

    log("=== ARM B: DAPT-01, no RAG ===")
    t0 = time.time()
    b_rows = run_rows(model, tok, rows, arm="dapt_norag", rag=False)
    timings["dapt_norag_infer_seconds"] = round(time.time() - t0, 1)
    write_jsonl(WORK / "task75_dapt_norag_results.jsonl", b_rows)

    log("=== ARM D: DAPT-01 + H3_RRF20 ===")
    t0 = time.time()
    d_rows = run_rows(model, tok, rows, arm="dapt_rrf20", rag=True)
    timings["dapt_rrf20_infer_seconds"] = round(time.time() - t0, 1)
    write_jsonl(WORK / "task75_dapt_rrf20_results.jsonl", d_rows)

    # identical-context integrity: C and D must carry identical context shas
    ctx_ok = all(
        c["evidence_context_sha256"] == d["evidence_context_sha256"]
        for c, d in zip(c_rows, d_rows)
    )
    if not ctx_ok:
        raise SystemExit("STOP: C/D context shas differ")
    log("C/D identical contexts verified")

    gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    metadata = {
        "task": "TASK 75 — FOUR-ARM RRF@20 RAG GENERATION GATE (generation)",
        "model": MODEL_ID,
        "adapter": "DAPT-01 checkpoint-15248 (priyanshu471/dapt01-checkpoint-15248)",
        "adapter_sha256": adapter_sha,
        "adapter_merged": False,
        "quantization": "4bit-nf4-double, compute dtype fp16 (identical all arms)",
        "attention_backend": (
            "torch SDPA memory-efficient only (math disabled; flash/cudnn invalid "
            "on sm75 T4; transformers enable_gqa forced to repeat_kv). fp16 numerics; "
            "greedy/seed/cap/prompts/model unchanged"
        ),
        "system_prompt": SYSTEM_PROMPT,
        "system_prompt_identical_to_task60_69_71": True,
        "user_content": {
            "norag_arms": "frozen question only (Task-60 protocol)",
            "rag_arms": "H3_RRF20 governed evidence context + frozen question",
        },
        "prompts_file": "task75_rag_prompts.jsonl",
        "prompts_sha256": prompts_sha,
        "evidence_window": "H3_RRF20 (EVIDENCE_K=5, TEXT_TRUNC=500, RRF k=20)",
        "n_evidence_items_per_case": 5,
        "prompt_style": "chat_template if available else plain_fallback",
        "decoding": "greedy (do_sample=False)",
        "max_new_tokens": MAX_NEW_TOKENS,
        "seed": SEED,
        "n_cases": len(rows),
        "arms": ["base_norag", "base_rrf20", "dapt_norag", "dapt_rrf20"],
        "gpu": gpu,
        "torch": torch.__version__,
        "python": platform.python_version(),
        "transformers": __import__("transformers").__version__,
        "peft": __import__("peft").__version__,
        "bitsandbytes": __import__("bitsandbytes").__version__,
        "model_load_seconds": round(load_s, 1),
        **timings,
        "identical_contexts_both_rag_arms": True,
        "run_host": "Google Colab T4 (google-colab-cli; NOT Kaggle)",
        "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (WORK / "task75_rag_run_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    log(f"metadata: {json.dumps(metadata)}")
    log("TASK 75 COLAB KERNEL DONE")


if __name__ == "__main__":
    main()
