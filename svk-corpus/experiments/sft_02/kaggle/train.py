#!/usr/bin/env python3
"""SFT-02: QLoRA supervised fine-tuning on the DAPT-01 adapter lineage (Task 68).

Locked config (configs/sft_qwen3_8b_sft02_v1.yaml; only LR and epochs differ
from SFT-01 per Task-66 failure analysis):
    Qwen/Qwen3-8B-Base, 4-bit NF4 (double quant, fp16 compute),
    adapter priyanshu471/dapt01-checkpoint-15248 continued as trainable,
    r=16/alpha=32/dropout=0.05, 7 projection targets (inherited from adapter),
    lr=3e-5 cosine warmup_ratio=0.03, batch 1x8 (effective 8), seq 2048,
    fp16, epochs=2, save/eval per epoch (save_total_limit=2), seed=42.

Data:   attach priyanshu471/jainllm-sft02-train (train.jsonl=61, eval.jsonl=13)
        and verify sha256 against the Task-67 records before training.
Output: /kaggle/working/sft-02-output + sft02_train_report.json; final adapter
        uploaded to priyanshu471/sft02-output.

This is a Kaggle session script, executed by Task 68 only.
No credentials are stored here: the Kaggle API authenticates from the
environment provisioned by Kaggle itself.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import traceback
from pathlib import Path

LOCKED = {
    "model": "Qwen/Qwen3-8B-Base",
    "quant": "4bit-nf4-double",
    "lora_r": 16, "lora_alpha": 32, "lora_dropout": 0.05,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj",
                       "gate_proj", "up_proj", "down_proj"],
    "lr": 3e-5, "scheduler": "cosine", "warmup_ratio": 0.03,
    "batch": 1, "grad_accum": 8, "effective_batch": 8,
    "max_seq_length": 2048, "precision": "fp16", "seed": 42,
    "epochs": 2, "save_eval": "epoch", "save_total_limit": 2,
    "weight_decay": 0.01, "max_grad_norm": 1.0,
}
EXPECTED_DATA = {
    "train_sha256": "3a45925f7f3e3c8d7beaecff4b1a6ac14592dc12b9849c8b70c32bb328b5b7e5",
    "eval_sha256": "ba59533699b28328e4dc9e5fa3df1c24a0b026824bafc852cfc703f38e6fcc35",
    "train_rows": 61,
    "eval_rows": 13,
}
ADAPTER_DATASETS = [
    "priyanshu471/dapt01-checkpoint-15248",
    "priyanshu47/dapt01-checkpoint-15248",
]
DATA_DATASET = "priyanshu471/jainllm-sft02-train"
OUT_DATASET = "priyanshu471/sft02-output"

WORK = Path("/kaggle/working")
LOG = WORK / "sft02_train_worker.log"
STATUS = WORK / "sft02_train_status.json"
OUT = WORK / "sft-02-output"
OWNER = os.environ.get("KAGGLE_USERNAME", "priyanshu471")

_T0 = time.time()
TOK = None


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def write_status(**kw):
    d = {"ts": time.time()}
    d.update(kw)
    STATUS.write_text(json.dumps(d, indent=2))


def _import_ok(mod):
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def ensure_deps():
    need = [p for p, m in {
        "transformers": "transformers", "peft": "peft",
        "datasets": "datasets", "accelerate": "accelerate",
        "bitsandbytes": "bitsandbytes",
    }.items() if not _import_ok(m)]
    if not need:
        log("deps preinstalled")
        return
    log(f"pip install missing: {need}")
    last = None
    for attempt in range(1, 7):
        subprocess.run("getent hosts pypi.org || sleep 5", shell=True, capture_output=True)
        r = subprocess.run(
            f"{sys.executable} -m pip install -q --retries 10 --timeout 60 {' '.join(need)}",
            shell=True, capture_output=True, text=True, timeout=1800,
        )
        if r.returncode == 0:
            log(f"pip ok attempt={attempt}")
            return
        last = ((r.stdout or "") + (r.stderr or ""))[-500:]
        log(f"pip attempt {attempt} failed: {last}")
        time.sleep(20 * attempt)
    raise SystemExit(f"pip failed: {last}")


def _find(name, root):
    if not root.exists():
        return None
    if (root / name).exists():
        return root / name
    hits = list(root.glob(f"**/{name}"))
    return hits[0] if hits else None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_rows(path):
    n = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                n += 1
    return n


def ensure_data():
    """Locate train.jsonl + eval.jsonl; verify Task-67 sha256 and row counts."""
    root = Path("/kaggle/input/jainllm-sft02-train")
    train, ev = _find("train.jsonl", root), _find("eval.jsonl", root)
    if train is None or ev is None:
        dl = WORK / "sft02_data"
        r = subprocess.run(
            f"kaggle datasets download -d {DATA_DATASET} -p {dl} --unzip",
            shell=True, capture_output=True, text=True, timeout=900,
        )
        if r.returncode != 0:
            raise SystemExit("sft02 data download failed: " +
                             ((r.stdout or "") + (r.stderr or ""))[-400:])
        train, ev = _find("train.jsonl", dl), _find("eval.jsonl", dl)
    if train is None:
        raise SystemExit("train.jsonl not found")
    if ev is None:
        raise SystemExit("eval.jsonl not found")
    t_sha, e_sha = sha256_file(str(train)), sha256_file(str(ev))
    if t_sha != EXPECTED_DATA["train_sha256"]:
        raise SystemExit(f"train.jsonl sha256 mismatch: {t_sha}")
    if e_sha != EXPECTED_DATA["eval_sha256"]:
        raise SystemExit(f"eval.jsonl sha256 mismatch: {e_sha}")
    n_train, n_eval = count_rows(train), count_rows(ev)
    if n_train != EXPECTED_DATA["train_rows"] or n_eval != EXPECTED_DATA["eval_rows"]:
        raise SystemExit(f"row count mismatch train={n_train} eval={n_eval}")
    log(f"attached train={train} ({n_train} rows sha ok) eval={ev} ({n_eval} rows sha ok)")
    return train, ev


def ensure_adapter():
    """Locate the DAPT-01 checkpoint-15248 adapter directory."""
    for slug in ADAPTER_DATASETS:
        step = slug.rsplit("-", 1)[-1]
        short = slug.split("/", 1)[1]
        for att in (Path(f"/kaggle/input/dapt01-checkpoint-{step}"),
                    Path(f"/kaggle/input/datasets/{slug}"),
                    Path(f"/kaggle/input/{short}")):
            if (att / "adapter_config.json").exists():
                return att
            hits = list(att.glob("**/adapter_config.json")) if att.exists() else []
            if hits:
                return hits[0].parent
    dl = WORK / "dapt_adapter"
    for slug in ADAPTER_DATASETS:
        r = subprocess.run(
            f"kaggle datasets download -d {slug} -p {dl} --unzip",
            shell=True, capture_output=True, text=True, timeout=1800,
        )
        if r.returncode == 0:
            hits = list(Path(dl).glob("**/adapter_config.json"))
            if hits:
                return hits[0].parent
    raise SystemExit("DAPT-01 adapter not found (attach dapt01-checkpoint-15248)")


def package_versions():
    ver = {"python": platform.python_version()}
    for mod in ("torch", "transformers", "peft", "bitsandbytes",
                "accelerate", "datasets"):
        try:
            ver[mod] = __import__(mod).__version__
        except Exception:
            ver[mod] = None
    return ver


def startup_checks(adapter):
    import torch
    if not torch.cuda.is_available():
        raise SystemExit("CUDA not available")
    name = torch.cuda.get_device_name(0)
    free, total = torch.cuda.mem_get_info(0)
    log(f"GPU={name} vram_free={free / 1e9:.1f}GB vram_total={total / 1e9:.1f}GB")
    if total and total < 12e9:
        raise SystemExit(f"VRAM too low: {total / 1e9:.1f}GB")
    for f in ("adapter_config.json", "adapter_model.safetensors"):
        if not (adapter / f).exists():
            raise SystemExit(f"adapter missing {f}")
    ad = json.loads((adapter / "adapter_config.json").read_text())
    if ad.get("r") != LOCKED["lora_r"] or ad.get("lora_alpha") != LOCKED["lora_alpha"]:
        raise SystemExit(f"adapter LoRA mismatch r={ad.get('r')} alpha={ad.get('lora_alpha')}")
    if float(ad.get("lora_dropout") or 0) != LOCKED["lora_dropout"]:
        raise SystemExit(f"adapter dropout mismatch {ad.get('lora_dropout')}")
    if set(ad.get("target_modules") or []) != set(LOCKED["target_modules"]):
        raise SystemExit(f"adapter target_modules mismatch {ad.get('target_modules')}")
    if LOCKED["model"] != "Qwen/Qwen3-8B-Base":
        raise SystemExit("LOCKED model corrupted")
    if LOCKED["lr"] != 3e-5 or LOCKED["epochs"] != 2:
        raise SystemExit("LOCKED hyperparameters corrupted (expected lr=3e-5 epochs=2)")
    return name


def render_chat(tokenizer, messages, add_generation_prompt=False):
    if getattr(tokenizer, "chat_template", None):
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=add_generation_prompt)
    parts = []
    for m in messages:
        parts.append("<|im_start|>" + m["role"] + "\n" + m["content"] + "<|im_end|>\n")
    text = "".join(parts)
    if add_generation_prompt:
        text += "<|im_start|>assistant\n"
    return text


def build_example(messages, tokenizer, max_len):
    prompt_text = render_chat(tokenizer, messages[:-1], add_generation_prompt=True)
    full_text = render_chat(tokenizer, messages, add_generation_prompt=False)
    prompt_ids = tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
    enc = tokenizer(full_text, add_special_tokens=False, truncation=True,
                    max_length=max_len)
    input_ids = enc["input_ids"]
    cut = min(len(prompt_ids), len(input_ids) - 1)
    labels = [-100] * cut + input_ids[cut:]
    return {"input_ids": input_ids, "labels": labels,
            "attention_mask": [1] * len(input_ids)}


def load_pair(path):
    import datasets
    ds = datasets.load_dataset("json", data_files=str(path))
    split = ds[list(ds.keys())[0]]

    def tok_fn(ex):
        msgs = ex["messages"]
        assert msgs[0]["role"] == "user" and msgs[-1]["role"] == "assistant"
        return build_example(msgs, TOK, LOCKED["max_seq_length"])

    cols = split.column_names
    return split.map(tok_fn, batched=False, remove_columns=cols, num_proc=1)


def load_model_and_adapter(adapter_dir):
    import torch
    from peft import PeftModel, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    global TOK
    TOK = AutoTokenizer.from_pretrained(LOCKED["model"], trust_remote_code=True)
    if TOK.pad_token is None:
        TOK.pad_token = TOK.eos_token
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    base = AutoModelForCausalLM.from_pretrained(
        LOCKED["model"], quantization_config=bnb, torch_dtype=torch.float16,
        device_map="auto", trust_remote_code=True)
    base = prepare_model_for_kbit_training(base, use_gradient_checkpointing=True)
    model = PeftModel.from_pretrained(base, str(adapter_dir), is_trainable=True)
    try:
        model.print_trainable_parameters()
    except Exception:
        pass
    return TOK, model


def train(model, tok, train_ds, eval_ds, adapter_dir):
    import inspect
    from transformers import DataCollatorForSeq2Seq, Trainer, TrainingArguments

    collator = DataCollatorForSeq2Seq(tok, padding=True, pad_to_multiple_of=8,
                                      label_pad_token_id=-100)
    candidate = {
        "output_dir": str(OUT),
        "num_train_epochs": LOCKED["epochs"],
        "per_device_train_batch_size": LOCKED["batch"],
        "per_device_eval_batch_size": LOCKED["batch"],
        "gradient_accumulation_steps": LOCKED["grad_accum"],
        "learning_rate": LOCKED["lr"],
        "lr_scheduler_type": LOCKED["scheduler"],
        "warmup_ratio": LOCKED["warmup_ratio"],
        "weight_decay": LOCKED["weight_decay"],
        "max_grad_norm": LOCKED["max_grad_norm"],
        "seed": LOCKED["seed"],
        "fp16": True,
        "bf16": False,
        "optim": "adamw_torch",
        "logging_steps": 1,
        "save_strategy": "epoch",
        "eval_strategy": "epoch",
        "save_total_limit": LOCKED["save_total_limit"],
        "load_best_model_at_end": False,
        "report_to": [],
        "remove_unused_columns": True,
        "dataloader_num_workers": 0,
        "gradient_checkpointing": True,
    }
    params = set(inspect.signature(TrainingArguments.__init__).parameters)
    kwargs = {k: v for k, v in candidate.items() if k in params}
    dropped = sorted(set(candidate) - set(kwargs))
    if dropped:
        log(f"TrainingArguments dropped: {dropped}")
    args = TrainingArguments(**kwargs)
    log(f"TrainingArguments ok epochs={args.num_train_epochs} lr={args.learning_rate} "
        f"save={args.save_strategy} eval={args.eval_strategy} fp16={args.fp16}")

    resume = os.environ.get("SFT02_RESUME") or None
    if resume is None and OUT.exists():
        cks = sorted(OUT.glob("checkpoint-*"),
                     key=lambda p: int(p.name.split("-")[-1]))
        if cks and (cks[-1] / "trainer_state.json").exists():
            resume = str(cks[-1])
    if resume:
        log(f"resume from {resume}")

    tparams = set(inspect.signature(Trainer.__init__).parameters)
    tkw = ({"processing_class": tok} if "processing_class" in tparams
           else {"tokenizer": tok})
    trainer = Trainer(model=model, args=args, train_dataset=train_ds,
                      eval_dataset=eval_ds, data_collator=collator, **tkw)
    result = None
    try:
        result = trainer.train(resume_from_checkpoint=resume)
    except Exception:
        log("TRAIN_EXCEPTION\n" + traceback.format_exc())
        write_status(state="error", error=traceback.format_exc()[-2000:])
        raise
    return trainer, result


def save_outputs(trainer, tok, model, adapter_dir, train_path, eval_path, result):
    OUT.mkdir(parents=True, exist_ok=True)
    final_dir = OUT / "sft-02-final"
    final_dir.mkdir(exist_ok=True)
    model.save_pretrained(str(final_dir))
    tok.save_pretrained(str(final_dir))
    report = {
        "experiment": "SFT-02",
        "task": "TASK 68",
        "locked": LOCKED,
        "base_model": LOCKED["model"],
        "continues_adapter": "priyanshu471/dapt01-checkpoint-15248",
        "adapter_dir": str(adapter_dir),
        "train_file": str(train_path),
        "train_sha256": sha256_file(str(train_path)),
        "eval_file": str(eval_path),
        "eval_sha256": sha256_file(str(eval_path)),
        "train_rows": EXPECTED_DATA["train_rows"],
        "eval_rows": EXPECTED_DATA["eval_rows"],
        "global_step": int(getattr(trainer.state, "global_step", 0)),
        "epochs": LOCKED["epochs"],
        "elapsed_sec": round(time.time() - _T0, 1),
        "training_started": True,
        "final_adapter_dir": str(final_dir),
        "versions": package_versions(),
        "gpu": __import__("torch").cuda.get_device_name(0),
    }
    if result is not None:
        try:
            if isinstance(result, dict):
                metrics = result
            elif hasattr(result, "_asdict"):
                metrics = result._asdict()
            elif hasattr(result, "metrics"):
                metrics = dict(result.metrics or {})
            else:
                metrics = dict(getattr(result, "__dict__", {}) or {})
            report.update({k: float(v) for k, v in metrics.items()
                           if isinstance(v, (int, float)) and not isinstance(v, bool)})
        except Exception as exc:  # noqa: BLE001
            log(f"metrics embed skipped: {exc}")
    lh = trainer.state.log_history or []
    ev = [x for x in lh if "eval_loss" in x]
    losses = [x for x in lh if "loss" in x and "eval_loss" not in x]
    if ev:
        report["eval_losses"] = [x.get("eval_loss") for x in ev]
        report["first_eval_loss"] = ev[0].get("eval_loss")
        report["last_eval_loss"] = ev[-1].get("eval_loss")
    if losses:
        report["train_loss_series"] = [x.get("loss") for x in losses]
        report["starting_train_loss"] = losses[0].get("loss")
        report["ending_train_loss"] = losses[-1].get("loss")
    (final_dir / "sft02_train_report.json").write_text(json.dumps(report, indent=2))
    (OUT / "sft02_train_report.json").write_text(json.dumps(report, indent=2))
    log("REPORT " + json.dumps(report))
    return final_dir, report


def upload_output(final_dir, report):
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except Exception as e:
        log(f"kaggle api unavailable ({e}); skipping upload")
        return None
    import shutil
    folder = Path("/tmp/kaggle_up_sft02")
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    for p in final_dir.iterdir():
        if p.is_file():
            shutil.copy2(p, folder / p.name)
    (folder / "dataset-metadata.json").write_text(json.dumps({
        "title": "SFT-02 final adapter (DAPT-01 lineage)",
        "id": f"{OWNER}/sft02-output",
        "licenses": [{"name": "CC0-1.0"}],
        "description": "SFT-02 QLoRA adapter on DAPT-01 checkpoint-15248 lineage (Task 68).",
    }, indent=2))
    api = KaggleApi()
    api.authenticate()
    try:
        resp = api.dataset_create_new(folder=str(folder), public=True, quiet=True,
                                      convert_to_csv=False, dir_mode="skip")
        status = getattr(resp, "status", "Ok")
        if status not in ("Ok", "ok", "SUCCESS"):
            raise RuntimeError(f"create status={status} "
                               f"error={getattr(resp, 'error', None)}")
        log("upload create ok")
    except Exception as exc:  # noqa: BLE001
        log(f"upload create failed ({exc}); trying version")
        resp = api.dataset_create_version(str(folder), version_notes="sft-02 final",
                                          quiet=True, convert_to_csv=False,
                                          dir_mode="skip")
        status = getattr(resp, "status", "Ok")
        if status not in ("Ok", "ok", "SUCCESS"):
            raise RuntimeError(f"version status={status} "
                               f"error={getattr(resp, 'error', None)}")
        log("upload version ok")
    return f"{OWNER}/sft02-output"


def main():
    import torch
    WORK.mkdir(parents=True, exist_ok=True)
    write_status(state="starting")
    ensure_deps()
    adapter_dir = ensure_adapter()
    gpu = startup_checks(adapter_dir)
    log(f"SFT02 START gpu={gpu} adapter={adapter_dir} "
        f"lr={LOCKED['lr']} epochs={LOCKED['epochs']} seed={LOCKED['seed']}")
    write_status(state="loading_model", adapter=str(adapter_dir), gpu=gpu)
    tok, model = load_model_and_adapter(adapter_dir)
    train_path, eval_path = ensure_data()
    train_ds, eval_ds = load_pair(train_path), load_pair(eval_path)
    log(f"dataset train={len(train_ds)} eval={len(eval_ds)}")
    write_status(state="training", train_rows=len(train_ds), eval_rows=len(eval_ds))
    trainer, result = train(model, tok, train_ds, eval_ds, adapter_dir)
    final_dir, report = save_outputs(trainer, tok, model, adapter_dir,
                                     train_path, eval_path, result)
    slug = upload_output(final_dir, report)
    write_status(state="done", report=report, uploaded=slug,
                 elapsed_sec=round(time.time() - _T0, 1))
    log(f"SFT02 COMPLETE uploaded={slug}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        try:
            STATUS.write_text(json.dumps({
                "ts": time.time(), "state": "fatal",
                "error": traceback.format_exc()[-2000:]}, indent=2))
            with LOG.open("a") as f:
                f.write("FATAL\n" + traceback.format_exc() + "\n")
        except Exception:
            pass
        raise
