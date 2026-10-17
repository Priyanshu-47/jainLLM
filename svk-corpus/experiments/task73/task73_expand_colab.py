"""TASK 73 Colab kernel — zero-shot lexical query expansion (Phase 2).

Generates exactly 3 lexical search-query variants for each of the 47 frozen
queries. The model must NOT answer the question; it only reformulates the
search query. No retrieved evidence is shown to the model.

Protocol (deterministic):
  - model: Qwen/Qwen3-8B-Base (4-bit nf4 double, fp16 compute — same load
    path as Task-69/71 generation, no adapter)
  - decoding: greedy (do_sample=False), seed 42, max_new_tokens 160 fixed
  - chat_template prompt style with plain fallback
  - input: /content/task73/task73_queries_input.jsonl (47 rows, sha-verified
    via TASK73_INPUT_SHA env)

Outputs (under /content/task73/out):
  task73_query_expansions_raw.jsonl  — one row per case: original_query,
      variant_1..3, raw_output, parse_ok, prompt/decoding metadata
  task73_expansion_run_metadata.json — timings + versions
Also echoes RESULT_JSON:: lines to stdout for provenance.
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
    """Pin the Task-60/69/71 evaluation stack (transformers 5.0.0 / bnb 0.50.2)."""
    wanted = {"transformers": "5.0.0", "bitsandbytes": "0.50.2"}
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
        # Fresh VMs carry a newer preinstalled transformers; a plain `pip
        # install X==V` over it leaves a broken mixed tree (task71 lesson).
        # Uninstall first, then install the pin with --no-deps.
        pkgs = [n.split("==")[0] for n in need]
        print(f"[deps] pip uninstall {' '.join(pkgs)} (attempt {attempt})", flush=True)
        subprocess.run(
            f"{sys.executable} -m pip uninstall -y -q {' '.join(pkgs)}",
            shell=True, capture_output=True, text=True, timeout=600,
        )
        print(f"[deps] pip install --no-deps {' '.join(need)} (attempt {attempt})", flush=True)
        r = subprocess.run(
            f"{sys.executable} -m pip install -q --no-deps --retries 10 --timeout 60 {' '.join(need)}",
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

# Same T4-safe SDPA configuration as Task-71 (flash/cudnn invalid on sm75,
# math OOMs, transformers 5.0 enable_gqa unsupported by mem-efficient here).
torch.backends.cuda.enable_flash_sdp(False)
torch.backends.cuda.enable_mem_efficient_sdp(True)
torch.backends.cuda.enable_math_sdp(False)
torch.backends.cuda.enable_cudnn_sdp(False)

import transformers.integrations.sdpa_attention as _sda  # noqa: E402


def _use_gqa_false(attention_mask, key):  # noqa: ANN001
    return False


_sda.use_gqa_in_sdpa = _use_gqa_false

from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig  # noqa: E402

MODEL_ID = "Qwen/Qwen3-8B-Base"
ROOT = Path("/content/task73")
INPUT_PATH = ROOT / "task73_queries_input.jsonl"
WORK = ROOT / "out"
EXPECTED_INPUT_SHA = os.environ.get("TASK73_INPUT_SHA", "").strip()

SYSTEM_PROMPT = (
    "You are a search-query rewriter for a digital library of Jain religious "
    "texts. Your only job is to rewrite the given search query in alternative "
    "ways so that a keyword search over the library can find relevant "
    "passages. You must NOT answer the query, and you must NOT add "
    "explanations or commentary."
)
MAX_NEW_TOKENS = 160
SEED = 42


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_input() -> list[dict]:
    rows = [
        json.loads(ln)
        for ln in INPUT_PATH.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    if len(rows) != 47:
        raise SystemExit(f"expected 47 input rows, got {len(rows)}")
    for r in rows:
        if not r.get("question", "").strip():
            raise SystemExit(f"empty question for {r['example_id']}")
    return rows


def build_prompt(tokenizer, question: str) -> tuple[str, str]:
    user_content = (
        f"Search query:\n{question}\n\n"
        "Write exactly 3 alternative search queries for the same information "
        "need, one per line, numbered 1. 2. 3.\n"
        "Rules:\n"
        "- Do not answer the query.\n"
        "- Preserve named entities, teacher names, canonical text names, "
        "religious terms, and sect or tradition distinctions exactly.\n"
        "- Keep the same language as the original query.\n"
        "- Keep each variant self-contained and keyword-friendly.\n"
        "- Output only the three numbered lines."
    )
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


def parse_variants(raw: str) -> tuple[list[str], bool]:
    """Extract exactly 3 numbered variants; returns (variants, parse_ok)."""
    variants: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # strip leading enumeration like "1. ", "2) ", "-", "1:"
        stripped = line
        for prefix_len in (3, 2):
            head = stripped[:prefix_len]
            if head[:1].isdigit() and head[1:2] in ".):":
                rest = stripped[prefix_len:].strip()
                if rest:
                    stripped = rest
                break
            if stripped.startswith(("-", "*")):
                stripped = stripped[1:].strip()
                break
        if not stripped:
            continue
        if stripped.lower().startswith("search query"):
            continue
        variants.append(stripped)
        if len(variants) == 3:
            break
    ok = len(variants) == 3 and all(len(v) >= 3 for v in variants)
    if not ok:
        # keep whatever was parsed; pad with empty strings for structure
        variants = (variants + ["", "", ""])[:3]
    return variants, ok


def _oom_cleanup() -> None:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def main() -> None:
    torch.manual_seed(SEED)
    WORK.mkdir(parents=True, exist_ok=True)

    if not INPUT_PATH.exists():
        raise FileNotFoundError(INPUT_PATH)
    input_sha = sha256_file(INPUT_PATH)
    if EXPECTED_INPUT_SHA and input_sha != EXPECTED_INPUT_SHA:
        raise SystemExit(
            f"STOP: input sha {input_sha} != expected {EXPECTED_INPUT_SHA}"
        )
    log(f"input sha verified {input_sha[:16]}…")

    rows = load_input()
    log(f"{len(rows)} input rows")

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
    load_s = round(time.time() - t_load, 1)
    _oom_cleanup()
    log(f"model loaded in {load_s}s")

    out_rows: list[dict] = []
    t_gen0 = time.time()
    for i, r in enumerate(rows, 1):
        question = r["question"]
        prompt, style = build_prompt(tok, question)
        inputs = tok(prompt, return_tensors="pt")
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        t0 = time.time()
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,
                pad_token_id=tok.pad_token_id,
                eos_token_id=tok.eos_token_id,
            )
        new_ids = out[0][inputs["input_ids"].shape[1]:]
        raw = tok.decode(new_ids, skip_special_tokens=True).strip()
        decode_s = round(time.time() - t0, 3)
        variants, parse_ok = parse_variants(raw)
        row = {
            "example_id": r["example_id"],
            "original_query": question,
            "variant_1": variants[0],
            "variant_2": variants[1],
            "variant_3": variants[2],
            "parse_ok": parse_ok,
            "raw_output": raw,
            "model": MODEL_ID,
            "prompt_style": style,
            "system_prompt": SYSTEM_PROMPT,
            "decoding": "greedy",
            "seed": SEED,
            "max_new_tokens": MAX_NEW_TOKENS,
            "new_tokens": int(new_ids.shape[0]),
            "decode_seconds": decode_s,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        }
        out_rows.append(row)
        log(
            f"  [{i}/{len(rows)}] {r['example_id']} parse_ok={parse_ok} "
            f"({row['new_tokens']} tok) v1={variants[0][:60]!r}"
        )
        print("RESULT_JSON::" + json.dumps(row, ensure_ascii=False), flush=True)
        _oom_cleanup()

    gen_s = round(time.time() - t_gen0, 1)
    out_path = WORK / "task73_query_expansions_raw.jsonl"
    out_path.write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out_rows),
        encoding="utf-8",
    )
    log(f"wrote {out_path} ({len(out_rows)} rows)")

    n_parse_ok = sum(1 for x in out_rows if x["parse_ok"])
    metadata = {
        "task": "TASK 73 — zero-shot lexical query expansion (generation)",
        "model": MODEL_ID,
        "adapter": None,
        "quantization": "4bit-nf4-double, compute dtype fp16",
        "system_prompt": SYSTEM_PROMPT,
        "decoding": "greedy (do_sample=False)",
        "max_new_tokens": MAX_NEW_TOKENS,
        "seed": SEED,
        "n_cases": len(rows),
        "n_variants_requested": len(rows) * 3,
        "n_parse_ok_cases": n_parse_ok,
        "input_file": INPUT_PATH.name,
        "input_sha256": input_sha,
        "model_load_seconds": load_s,
        "generation_seconds": gen_s,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "torch": torch.__version__,
        "python": platform.python_version(),
        "transformers": __import__("transformers").__version__,
        "run_host": "Google Colab T4 (google-colab-cli)",
        "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    meta_path = WORK / "task73_expansion_run_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    log(f"metadata: {json.dumps(metadata)}")
    log("TASK 73 EXPANSION KERNEL DONE")


if __name__ == "__main__":
    main()
