"""TASK 83 Kaggle kernel — targeted mini-gate generation (P500/P1000 + ctrls).

Protocol identical to the Task-75/82 kernels (see imports/guards below).
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
PAYLOAD_PATH = WORK / "task83_kernel_payload.json"
ADAPTER_SHA_EXPECTED = "9b4d2bdcfe089118d0634815596b628506a83c434d3863cff7a731cba75a58e9"
PAYLOAD_SHA_EXPECTED = "5d2bf840a0d8f5d03899d58b63698111a9673b0330b0d9e7487e411598262641"
PAYLOAD_B64 = "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"

SYSTEM_PROMPT = (
    "You are a careful assistant for Jain studies. "
    "Answer the user's question concisely (in 1-3 sentences). "
    "If you are unsure or the information is not available, say so."
)
MAX_NEW_TOKENS = 192
SEED = 42
CONFIGS = ("p500", "p1000", "p250ctrl", "pfullctrl")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_adapter_dir() -> Path:
    cands = [
        Path("/kaggle/input/dapt01-checkpoint-15248"),
        *sorted(Path("/kaggle/input").glob("**/*dapt01-checkpoint-15248*")),
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
    raise FileNotFoundError("adapter not found")


def load_payload() -> dict:
    raw = gzip.decompress(base64.b64decode(PAYLOAD_B64))
    PAYLOAD_PATH.write_bytes(raw)
    sha = sha256_file(PAYLOAD_PATH)
    if sha != PAYLOAD_SHA_EXPECTED:
        raise SystemExit(f"payload sha mismatch: {sha} != {PAYLOAD_SHA_EXPECTED}")
    log(f"payload sha verified {sha[:16]}...")
    payload = json.loads(raw.decode("utf-8"))
    for cfg in CONFIGS:
        cases = payload["configs"].get(cfg)
        if not cases:
            raise SystemExit(f"payload missing config {cfg}")
        for eid, row in cases.items():
            if not row.get("user_content") or not row.get("question"):
                raise SystemExit(f"empty content {cfg}/{eid}")
    return payload


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


def run_config(model, tokenizer, cases: dict, config: str, arm: str) -> list[dict]:
    out = []
    items = list(cases.items())
    for i, (eid, r) in enumerate(items, 1):
        prompt, style = build_prompt(tokenizer, r["user_content"])
        gen = generate(model, tokenizer, prompt)
        row = {
            "example_id": eid,
            "config": config,
            "arm": f"{arm}_{config}",
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
            "input_prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "evidence_context_sha256": r["context_sha256"],
            "n_evidence_items": r["n_evidence_items"],
        }
        out.append(row)
        log(f"  [{config} {arm} {i}/{len(items)}] {eid} "
            f"({gen['new_tokens']} tok) {gen['answer'][:90]!r}")
        print("RESULT_JSON::" + json.dumps(row, ensure_ascii=False), flush=True)
    return out


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    log(f"wrote {path.name} ({len(rows)} rows)")


def main() -> None:
    torch.manual_seed(SEED)
    WORK.mkdir(parents=True, exist_ok=True)

    adapter_dir = resolve_adapter_dir()
    adapter_weights = adapter_dir / "adapter_model.safetensors"
    if not adapter_weights.exists() or not (adapter_dir / "adapter_config.json").exists():
        raise FileNotFoundError(f"adapter files missing under {adapter_dir}")
    adapter_sha = sha256_file(adapter_weights)
    if adapter_sha != ADAPTER_SHA_EXPECTED:
        raise SystemExit(f"adapter sha mismatch: {adapter_sha}")
    log(f"adapter sha verified {adapter_sha[:16]}... dir={adapter_dir}")

    payload = load_payload()

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
    all_rows: dict[str, dict[str, list[dict]]] = {c: {} for c in CONFIGS}

    log("=== BASE arms (all configs) ===")
    t0 = time.time()
    for cfg in CONFIGS:
        rows = run_config(model, tok, payload["configs"][cfg], cfg, "base")
        all_rows[cfg]["base"] = rows
        write_jsonl(WORK / f"task83_{cfg}_base_results.jsonl", rows)
    timings["base_infer_seconds"] = round(time.time() - t0, 1)

    log("attaching DAPT-01 adapter (no merge)")
    t0 = time.time()
    model = PeftModel.from_pretrained(model, str(adapter_dir), is_trainable=False)
    model.eval()
    timings["adapter_attach_seconds"] = round(time.time() - t0, 1)

    log("=== DAPT arms (all configs) ===")
    t0 = time.time()
    for cfg in CONFIGS:
        rows = run_config(model, tok, payload["configs"][cfg], cfg, "dapt")
        all_rows[cfg]["dapt"] = rows
        write_jsonl(WORK / f"task83_{cfg}_dapt_results.jsonl", rows)
    timings["dapt_infer_seconds"] = round(time.time() - t0, 1)

    for cfg in CONFIGS:
        ctx_ok = all(
            b["evidence_context_sha256"] == d["evidence_context_sha256"]
            for b, d in zip(all_rows[cfg]["base"], all_rows[cfg]["dapt"])
        )
        if not ctx_ok:
            raise SystemExit(f"STOP: {cfg} base/dapt context shas differ")
    log("all configs: base/dapt identical contexts verified")

    gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    metadata = {
        "task": (
            "TASK 83 — TARGETED MINI-GATE GENERATION "
            "(P500/P1000 differing cases + P250/PFULL 037 controls)"
        ),
        "model": MODEL_ID,
        "adapter": "DAPT-01 checkpoint-15248 (priyanshu471/dapt01-checkpoint-15248)",
        "adapter_sha256": adapter_sha,
        "adapter_merged": False,
        "quantization": "4bit-nf4-double, compute dtype fp16 (identical all arms)",
        "attention_backend": (
            "torch SDPA memory-efficient only (math disabled; flash/cudnn "
            "invalid on sm75 T4; enable_gqa forced to repeat_kv). fp16 numerics; "
            "greedy/seed/cap/prompts/model unchanged from Task-75"
        ),
        "system_prompt": SYSTEM_PROMPT,
        "configs": {
            cfg: {
                "n_cases": len(payload["configs"][cfg]),
                "example_ids": sorted(payload["configs"][cfg]),
                "context_shas": {
                    eid: row["context_sha256"]
                    for eid, row in payload["configs"][cfg].items()
                },
            }
            for cfg in CONFIGS
        },
        "controls": {
            "p250ctrl": "recorded Task-82 pool-250 context for 037 rerun same host",
            "pfullctrl": "recorded Task-75 full-list context for 037 rerun same host",
        },
        "prompt_style": "chat_template if available else plain_fallback",
        "decoding": "greedy (do_sample=False)",
        "max_new_tokens": MAX_NEW_TOKENS,
        "seed": SEED,
        "arms": ["base", "dapt"],
        "gpu": gpu,
        "torch": torch.__version__,
        "python": platform.python_version(),
        "transformers": __import__("transformers").__version__,
        "peft": __import__("peft").__version__,
        "bitsandbytes": __import__("bitsandbytes").__version__,
        "model_load_seconds": round(load_s, 1),
        **timings,
        "run_host": "Kaggle T4 (established; Colab token expired)",
        "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (WORK / "task83_run_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    log(f"metadata: {json.dumps(metadata)}")
    log("TASK 83 KAGGLE KERNEL DONE")


if __name__ == "__main__":
    main()
