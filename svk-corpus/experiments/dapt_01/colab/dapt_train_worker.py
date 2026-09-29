#!/usr/bin/env python3
"""DAPT-01 worker: resume 3893 -> TARGET_STEP. Saves every 500. Uploads result to Kaggle."""
from __future__ import annotations
import json, os, shutil, sys, time, traceback
from pathlib import Path

FROM_STEP = 3893
TARGET_STEP = int(os.environ.get("DAPT_TARGET_STEP", "5500"))
SAVE_STEPS = 500
TOTAL = 15248
LOCKED = {
    "model": "Qwen/Qwen3-8B-Base",
    "lora_r": 16, "lora_alpha": 32, "lora_dropout": 0.05,
    "lr": 2e-4, "max_seq_length": 2048, "batch": 1, "grad_accum": 16,
    "seed": 42,
    "target_modules": ["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
}
LOG = Path("/content/dapt_train_worker.log")
STATUS = Path("/content/dapt_train_status.json")

def log(msg: str):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a") as f:
        f.write(line + "\n")

def write_status(**kw):
    d = {"ts": time.time(), "from": FROM_STEP, "target": TARGET_STEP}
    d.update(kw)
    STATUS.write_text(json.dumps(d, indent=2))

def detect_step(ckpt: Path) -> int:
    return int(json.loads((ckpt / "trainer_state.json").read_text())["global_step"])

def verify(ckpt: Path):
    ac = json.loads((ckpt / "adapter_config.json").read_text())
    assert ac["base_model_name_or_path"] == LOCKED["model"]
    assert ac["r"] == LOCKED["lora_r"]
    assert set(ac["target_modules"]) == set(LOCKED["target_modules"])

def snapshot(ckpt: Path, step: int):
    dest = Path(f"/content/dapt_known_good/known_good_step_{step}")
    dest.mkdir(parents=True, exist_ok=True)
    for name in ["adapter_model.safetensors","adapter_config.json","trainer_state.json",
                 "optimizer.pt","scheduler.pt","training_args.bin","tokenizer.json","tokenizer_config.json"]:
        src = ckpt / name
        if src.exists() and not (dest / name).exists():
            shutil.copy2(src, dest / name)
    return dest

from transformers import TrainerCallback

class TimeSafety(TrainerCallback):
    def __init__(self, timeout_sec):
        self.t0 = time.time()
        self.timeout_sec = timeout_sec
    def on_train_begin(self, args, state, control, **kwargs):
        self.t0 = time.time()
        return control
    def on_step_end(self, args, state, control, **kwargs):
        if time.time() - self.t0 > self.timeout_sec:
            control.should_training_stop = True
            log(f"TIME_SAFETY stop at {state.global_step}")
        return control

class SaveUploadCallback(TrainerCallback):
    """Upload every completed save_steps checkpoint to Kaggle so a Colab recycle cannot wipe it."""
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self._uploaded = set()
    def on_save(self, args, state, control, **kwargs):
        step = state.global_step
        ck = self.output_dir / f"checkpoint-{step}"
        if not (ck / "trainer_state.json").exists():
            log(f"on_save: missing {ck}")
            return control
        if step in self._uploaded:
            return control
        try:
            slug = upload_to_kaggle(ck, step)
            self._uploaded.add(step)
            log(f"UPLOAD_OK step={step} slug={slug}")
        except Exception:
            log(f"UPLOAD_FAIL step={step}\n" + traceback.format_exc())
        return control

def upload_to_kaggle(ckpt_dir: Path, step: int) -> str:
    """Upload public dataset for this checkpoint. Returns slug."""
    from kaggle.api.kaggle_api_extended import KaggleApi
    slug_name = f"dapt01-checkpoint-{step}"
    folder = Path(f"/tmp/kaggle_up_{step}")
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    for p in ckpt_dir.iterdir():
        if p.is_file():
            shutil.copy2(p, folder / p.name)
    # do not upload huge logs
    (folder / "dataset-metadata.json").write_text(json.dumps({
        "title": f"DAPT-01 checkpoint {step}",
        "id": f"Priyanshu47/{slug_name}",
        "licenses": [{"name": "CC0-1.0"}],
        "description": f"DAPT-01 QLoRA resume checkpoint global_step={step}/15248 (from 3893).",
    }, indent=2))
    api = KaggleApi(); api.authenticate()
    # try create new; if exists, create new version
    try:
        resp = api.dataset_create_new(folder=str(folder), public=True, quiet=True,
                                      convert_to_csv=False, dir_mode="skip")
        log(f"kaggle create ok ref={getattr(resp,'ref',None)}")
        return f"priyanshu47/{slug_name}"
    except Exception as e:
        log(f"kaggle create failed ({e}); trying version...")
        try:
            resp = api.dataset_create_version(str(folder), version_notes=f"step {step}",
                                              quiet=True, convert_to_csv=False, dir_mode="skip")
            log(f"kaggle version ok {resp}")
            return f"priyanshu47/{slug_name}"
        except Exception as e2:
            log(f"kaggle version failed: {e2}")
            raise

def main():
    log(f"WORKER START target={TARGET_STEP} from={FROM_STEP}")
    write_status(state="starting")
    ck = Path("/content/checkpoint-3893")
    data = Path("/content/domain_train")
    out = Path("/content/dapt-01-output")
    out.mkdir(exist_ok=True)

    assert (ck / "trainer_state.json").exists(), "missing resume ckpt"
    assert (data / "train.jsonl").exists(), "missing dataset"
    step = detect_step(ck)
    verify(ck)
    if step != FROM_STEP:
        raise SystemExit(f"unexpected step {step}")
    if TARGET_STEP <= step:
        raise SystemExit("target <= current")
    log(f"resume step={step} target={TARGET_STEP} delta={TARGET_STEP-step}")

    snapshot(ck, step)
    resume_dst = out / f"checkpoint-{step}"
    if not (resume_dst / "trainer_state.json").exists():
        if resume_dst.exists():
            shutil.rmtree(resume_dst)
        shutil.copytree(ck, resume_dst)

    # ---- ML stack ----
    import torch
    from transformers import (
        AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig,
        TrainingArguments, Trainer, DataCollatorForLanguageModeling,
    )
    from peft import PeftModel, prepare_model_for_kbit_training
    from datasets import load_dataset

    log(f"torch={torch.__version__} cuda={torch.cuda.is_available()} gpu={torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}")
    write_status(state="loading_model")

    tok = AutoTokenizer.from_pretrained(ck, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )
    try:
        base = AutoModelForCausalLM.from_pretrained(
            LOCKED["model"], dtype=torch.float16, device_map="auto",
            quantization_config=bnb, trust_remote_code=True,
        )
    except TypeError:
        base = AutoModelForCausalLM.from_pretrained(
            LOCKED["model"], torch_dtype=torch.float16, device_map="auto",
            quantization_config=bnb, trust_remote_code=True,
        )
    base = prepare_model_for_kbit_training(base, use_gradient_checkpointing=True)
    model = PeftModel.from_pretrained(base, ck, is_trainable=True)
    log("model+adapter loaded")

    write_status(state="loading_data")
    # train only — eval disabled; joint train+val schema cast fails (string vs null)
    try:
        ds = load_dataset("json", data_files={"train": str(data / "train.jsonl")})
        cols = ds["train"].column_names
        if "text" not in cols:
            raise ValueError(f"no text col: {cols}")
    except Exception as e:
        log(f"load_dataset failed ({e}); building text-only cache")
        text_only = Path("/content/domain_train_textonly.jsonl")
        if not text_only.exists() or text_only.stat().st_size == 0:
            with (data / "train.jsonl").open() as fin, text_only.open("w") as fout:
                import json as _json
                for line in fin:
                    try:
                        o = _json.loads(line)
                    except Exception:
                        continue
                    tx = o.get("text") or ""
                    if tx:
                        fout.write(_json.dumps({"text": tx}) + "\n")
        ds = load_dataset("json", data_files={"train": str(text_only)})
        cols = ds["train"].column_names

    def tok_fn(ex):
        return tok(ex["text"], truncation=True, max_length=LOCKED["max_seq_length"], padding=False)
    ds = ds.map(tok_fn, batched=True, remove_columns=cols, num_proc=1)
    log(f"dataset train={len(ds['train'])}")

    import inspect as _inspect
    _ta_params = set(_inspect.signature(TrainingArguments.__init__).parameters)
    # locked DAPT-01 kwargs; filter to what this transformers version accepts
    _candidate = {
        "output_dir": str(out),
        "max_steps": TARGET_STEP,
        "per_device_train_batch_size": LOCKED["batch"],
        "gradient_accumulation_steps": LOCKED["grad_accum"],
        "learning_rate": LOCKED["lr"],
        "lr_scheduler_type": "cosine",
        "warmup_steps": 0,  # resume past warmup; 5.17 has no warmup_ratio
        "weight_decay": 0.01,
        "max_grad_norm": 1.0,
        "seed": LOCKED["seed"],
        "fp16": True,
        "bf16": False,
        "optim": "adamw_torch",
        "logging_steps": 10,
        "save_steps": SAVE_STEPS,
        "save_strategy": "steps",
        "save_total_limit": 3,
        "report_to": [],
        "eval_strategy": "no",
        "remove_unused_columns": True,
        "dataloader_num_workers": 0,
        "gradient_checkpointing": True,
    }
    _kwargs = {k: v for k, v in _candidate.items() if k in _ta_params}
    _dropped = sorted(set(_candidate) - set(_kwargs))
    if _dropped:
        log(f"TrainingArguments dropped unsupported: {_dropped}")
    args = TrainingArguments(**_kwargs)
    if hasattr(args, "warmup_steps"):
        args.warmup_steps = 0
    log(f"TrainingArguments ok max_steps={args.max_steps} save_steps={args.save_steps}")

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=ds["train"],
        eval_dataset=None,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tok, mlm=False),
        processing_class=tok,
    )
    # ~10h hard stop; save_steps will have written 4000/4500/... along the way
    trainer.add_callback(TimeSafety(10 * 3600))
    trainer.add_callback(SaveUploadCallback(str(out)))

    write_status(state="training", global_step=step)
    log(f"TRAIN start resume={resume_dst} max_steps={TARGET_STEP}")
    t0 = time.time()
    try:
        result = trainer.train(resume_from_checkpoint=str(resume_dst))
    except Exception:
        log("TRAIN_EXCEPTION\n" + traceback.format_exc())
        write_status(state="error", error=traceback.format_exc()[-2000:])
        # still try to package whatever checkpoints exist
        result = None

    elapsed = time.time() - t0
    final_step = int(getattr(trainer.state, "global_step", step))
    log(f"TRAIN done final_step={final_step} elapsed={elapsed:.1f}s")
    train_failed = final_step <= FROM_STEP
    if train_failed and result is None:
        write_status(state="error", global_step=final_step, error="train_exception_no_progress")
        log("NO_PROGRESS exiting without upload")
        return 1

    # ensure final resumable ckpt
    final_ck = out / f"checkpoint-{final_step}"
    if not (final_ck / "trainer_state.json").exists():
        final_ck.mkdir(parents=True, exist_ok=True)
        trainer.save_model(str(final_ck))
        for name in ["tokenizer.json","tokenizer_config.json","chat_template.jinja","README.md"]:
            src = ck / name
            if src.exists():
                shutil.copy2(src, final_ck / name)
        if trainer.optimizer is not None:
            torch.save(trainer.optimizer.state_dict(), final_ck / "optimizer.pt")
        if trainer.lr_scheduler is not None:
            torch.save(trainer.lr_scheduler.state_dict(), final_ck / "scheduler.pt")
        trainer.state.save_to_json(final_ck / "trainer_state.json")
        torch.save(trainer.args, final_ck / "training_args.bin")

    (out / "LAST_RUN.json").write_text(json.dumps({
        "started_from": FROM_STEP,
        "final_step": final_step,
        "target": TARGET_STEP,
        "elapsed_sec": elapsed,
        "metrics": (result.metrics if result else {}),
        "timestamp": time.time(),
    }, indent=2))
    log(f"checkpoints={sorted(p.name for p in out.glob('checkpoint-*'))}")

    # package newest complete ckpt
    package_ck = final_ck
    if not (package_ck / "trainer_state.json").exists():
        # fall back to highest numbered
        cks = sorted(out.glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[1]))
        package_ck = cks[-1]
    fts = json.loads((package_ck / "trainer_state.json").read_text())
    pstep = int(fts["global_step"])
    log(f"packaging {package_ck} step={pstep}")

    tar_path = Path(f"/content/checkpoint-{pstep}.tgz")
    import tarfile
    with tarfile.open(tar_path, "w:gz") as tf:
        tf.add(package_ck, arcname=package_ck.name)
    log(f"tarball {tar_path} size={tar_path.stat().st_size}")

    write_status(state="uploading", final_step=pstep)
    try:
        # configure kaggle if env present
        token = os.environ.get("KAGGLE_API_TOKEN") or os.environ.get("KAGGLE_KEY")
        if token:
            cfg = Path.home() / ".kaggle"
            cfg.mkdir(exist_ok=True)
            (cfg / "kaggle.json").write_text(json.dumps({
                "username": os.environ.get("KAGGLE_USERNAME", "Priyanshu47"),
                "key": token,
            }))
            os.chmod(cfg / "kaggle.json", 0o600)
        slug = upload_to_kaggle(package_ck, pstep)
        write_status(state="done", final_step=pstep, kaggle=slug, elapsed_sec=elapsed)
        log(f"KAGGLE_OK {slug}")
    except Exception:
        log("UPLOAD_FAIL\n" + traceback.format_exc())
        write_status(state="done_local_only", final_step=pstep, elapsed_sec=elapsed,
                     error=traceback.format_exc()[-1500:])

    log("WORKER COMPLETE")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        try:
            STATUS.write_text(json.dumps({
                "ts": time.time(), "from": FROM_STEP, "target": TARGET_STEP,
                "state": "error", "error": traceback.format_exc()[-2000:],
            }, indent=2))
            with LOG.open("a") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S") + " FATAL\n" + traceback.format_exc() + "\n")
        except Exception:
            pass
        raise
