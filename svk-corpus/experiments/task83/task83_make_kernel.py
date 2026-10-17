"""TASK 83 Phase-2 — build the self-contained Kaggle kernel for the targeted
mini-gate generation (P500 / P1000 on differing cases + P250/PFULL 037 controls).

Generation protocol byte-identical to experiments/task75/task75_rag_infer.py
and the Task-82 kernel (transformers 5.0.0 / peft 0.19.1 / bnb 0.50.2, 4-bit
NF4 double, fp16 compute, greedy, max_new_tokens=192, seed=42, chat_template
w/ plain fallback, SDPA memory-efficient only, purge_preimported after pin).

Configs (RAG arms only; no-RAG arms are unaffected by the pool and reuse the
recorded Task-75 rows):
  p500      BASE / DAPT-01 + H3_RRF20 pool=500   (target cases)
  p1000     BASE / DAPT-01 + H3_RRF20 pool=1000  (target cases)
  p250ctrl  BASE / DAPT-01 + recorded Task-82 pool-250 context, case 037
            (same-host determinism control)
  pfullctrl BASE / DAPT-01 + recorded Task-75 full-list context, case 037
            (same-host determinism control for the reference outcome)

Outputs
  experiments/task83/kaggle/task83_infer_kaggle.py
  experiments/task83/kaggle/kernel-metadata.json

Push: kaggle kernels push -p experiments/task83/kaggle
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PAYLOAD = REPO / "data" / "evaluation" / "task83_kernel_payload.json"
OUT_DIR = REPO / "experiments" / "task83" / "kaggle"

ADAPTER_SHA = "9b4d2bdcfe089118d0634815596b628506a83c434d3863cff7a731cba75a58e9"

KERNEL_TEMPLATE = r'''"""TASK 83 Kaggle kernel — targeted mini-gate generation (P500/P1000 + ctrls).

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
ADAPTER_SHA_EXPECTED = "@@ADAPTER_SHA@@"
PAYLOAD_SHA_EXPECTED = "@@PAYLOAD_SHA@@"
PAYLOAD_B64 = "@@PAYLOAD_B64@@"

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
'''

METADATA = {
    "id": "priyanshu471/task83-mini-gate-p500-p1000-targeted",
    "title": "TASK83 Mini Gate P500 P1000 Targeted Generation",
    "code_file": "task83_infer_kaggle.py",
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
    raw = PAYLOAD.read_bytes()
    payload_sha = hashlib.sha256(raw).hexdigest()
    b64 = base64.b64encode(gzip.compress(raw, compresslevel=9)).decode("ascii")
    payload = json.loads(raw)
    n_gens = sum(len(v) for v in payload["configs"].values()) * 2
    print(f"payload {len(raw)}B -> gzip+b64 {len(b64)}B, sha {payload_sha[:16]}…")
    print(f"configs: { {k: len(v) for k, v in payload['configs'].items()} } "
          f"-> {n_gens} generations")

    kernel = (
        KERNEL_TEMPLATE
        .replace("@@ADAPTER_SHA@@", ADAPTER_SHA)
        .replace("@@PAYLOAD_SHA@@", payload_sha)
        .replace("@@PAYLOAD_B64@@", b64)
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "task83_infer_kaggle.py").write_text(kernel, encoding="utf-8")
    (OUT_DIR / "kernel-metadata.json").write_text(
        json.dumps(METADATA, indent=2), encoding="utf-8")
    print(f"wrote {OUT_DIR / 'task83_infer_kaggle.py'} "
          f"({(OUT_DIR / 'task83_infer_kaggle.py').stat().st_size} B)")
    print(f"wrote {OUT_DIR / 'kernel-metadata.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
